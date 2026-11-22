"""찜(product_like), 리뷰 쓰기(review_new)·완료(review_done) 라우트 확인

실행: (apps/be에서) python -m pytest test_review.py
pyrebase db를 흉내 내는 FakeDb를 review.db, product.db에 주입해서 찜/리뷰 저장을 확인한다.
"""

import io
import os
import tempfile
from contextlib import contextmanager
from urllib.parse import quote

from flask import template_rendered

from core import app
# 헤더의 url_for가 찾는 라우트를 모두 등록한다 (app.py와 같은 import)
from routes import auction, auth, chat, my, product, review, wanted  # noqa: F401

product.UPLOAD_DIR = tempfile.mkdtemp()
client = app.test_client()


def uploaded_files():
    return set(os.listdir(product.UPLOAD_DIR))


@contextmanager
def captured_templates():
    """render_template에 넘긴 템플릿 이름과 context를 잡는다 (Flask 표준 테스트 패턴)."""
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def detail_path(name):
    """product_detail로 가는 redirect Location (url_for가 만드는 percent-encoding과 맞춘다)"""
    return "/product/" + quote(name, safe="/")


class FakeSnapshot:
    def __init__(self, value):
        self._value = value

    def val(self):
        return self._value


class FakeDb:
    """pyrebase처럼 하나의 객체가 경로 상태를 들고 있다.

    child()는 self.path에 이어 붙이고 self를 반환한다(새 객체를 만들지 않는다).
    get()/set()/remove()는 실행 후 self.path를 비운다. 그래서 ref를 변수에 저장해 두고
    나중에 또 child()를 이어 부르면 경로가 섞인다 — set()을 변수로 저장한 ref에 바로 쓰지 말고
    매번 db.child(...).child(...).get()/set()/remove()처럼 한 줄 체인으로 실행해야 한다.
    """

    def __init__(self):
        self.store = {}
        self.path = []
        self.get_log = []  # get()이 실행될 때마다의 경로(tuple). 중복 읽기 확인용

    def child(self, key):
        self.path.append(str(key))
        return self

    def get(self):
        self.get_log.append(tuple(self.path))
        node = self.store
        for key in self.path:
            if not isinstance(node, dict) or key not in node:
                node = None
                break
            node = node[key]
        self.path = []
        return FakeSnapshot(node)

    def set(self, value):
        assert self.path, "루트 경로(path가 비어 있음)에 set()을 호출했어요 — DB 전체를 덮어쓸 수 있어요."
        node = self.store
        for key in self.path[:-1]:
            node = node.setdefault(key, {})
        node[self.path[-1]] = value
        self.path = []
        return value

    def remove(self):
        assert self.path, "루트 경로(path가 비어 있음)에 remove()를 호출했어요 — DB 전체를 지울 수 있어요."
        node = self.store
        for key in self.path[:-1]:
            node = node.get(key, {})
        node.pop(self.path[-1], None)
        self.path = []


def seed_product(fake_db, **fields):
    product_data = {
        "name": "아이패드 1/2",
        "seller": "owner",
        "price": 10000,
        "address": "ECC",
        "status": "상",
        "description": "설명",
        "kind": "fixed",
        "sale_status": "sale",
        "likes": 3,
        "created_at": "2026-11-20T10:00:00+09:00",
    }
    product_data.update(fields)
    fake_db.child("products").child(product.product_key(product_data["name"])).set(product_data)
    return product_data


def login(user_id):
    with client.session_transaction() as sess:
        sess["id"] = user_id


def logout():
    with client.session_transaction() as sess:
        sess.pop("id", None)


def like(name):
    return client.post("/product/like", data={"name": name})


def check_not_logged_in():
    logout()
    response = like("아이패드 1/2")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def check_missing_product():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    login("tester")
    assert like("없는 상품").status_code == 404


def check_own_product():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="tester")
    login("tester")

    response = like("아이패드 1/2")
    assert response.status_code == 302
    assert response.headers["Location"] == detail_path("아이패드 1/2")
    # 자기 상품은 좋아요 경로/개수가 그대로여야 한다
    assert fake_db.store.get("likes") is None
    assert fake_db.store["products"][product.product_key("아이패드 1/2")]["likes"] == 3


def check_like_add_and_cancel():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="owner", likes=3)
    login("tester")
    key = product.product_key("아이패드 1/2")

    # 추가
    response = like("아이패드 1/2")
    assert response.status_code == 302
    assert response.headers["Location"] == detail_path("아이패드 1/2")
    assert fake_db.store["likes"]["tester"][key]["created_at"]
    assert fake_db.store["products"][key]["likes"] == 4

    # 취소
    response = like("아이패드 1/2")
    assert response.status_code == 302
    assert key not in fake_db.store["likes"]["tester"]
    assert fake_db.store["products"][key]["likes"] == 3


def check_likes_not_below_zero():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="owner", likes=0)
    login("tester")
    key = product.product_key("아이패드 1/2")
    # 이미 찜한 상태로 만들어 취소했을 때 0 미만으로 내려가지 않는지 확인한다
    fake_db.child("likes").child("tester").child(key).set({"created_at": "x"})

    response = like("아이패드 1/2")
    assert response.status_code == 302
    assert fake_db.store["products"][key]["likes"] == 0


def check_route_priority():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    login("tester")

    # GET /product/like는 product_detail(name="like")로 매칭되어야 한다 (상품이 없으니 404, 405가 아니다)
    assert client.get("/product/like").status_code == 404

    # POST /product/like는 product_like로 매칭되어야 한다 (405 Method Not Allowed가 아니다)
    seed_product(fake_db, name="다른 상품", seller="owner")
    response = like("다른 상품")
    assert response.status_code == 302
    assert response.headers["Location"] == detail_path("다른 상품")


def check_db_none_does_not_crash():
    review.db = None
    product.db = None
    login("tester")
    response = like("컴퓨터구조 및 설계 5판")
    assert response.status_code == 302
    assert response.headers["Location"] == detail_path("컴퓨터구조 및 설계 5판")


def test_review():
    check_not_logged_in()
    check_missing_product()
    check_own_product()
    check_like_add_and_cancel()
    check_likes_not_below_zero()
    check_route_priority()
    check_db_none_does_not_crash()


def review_new_get(**args):
    return client.get("/review/new", query_string=args)


def review_new_post(**fields):
    form = {"product_name": "아이패드 1/2", "rating": "5", "title": "제목", "content": "내용"}
    form.update(fields)
    return client.post("/review/new", data=form, content_type="multipart/form-data")


def check_review_new_requires_login():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    logout()
    assert review_new_get().headers["Location"] == "/login"
    assert review_new_post().headers["Location"] == "/login"


def check_review_new_missing_fields():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="owner")
    login("tester")
    before = uploaded_files()

    response = review_new_post(title="", content="")
    assert response.status_code == 400
    text = response.get_data(as_text=True)
    assert "제목을 입력해 주세요." in text and "내용을 입력해 주세요." in text
    assert uploaded_files() == before


def check_review_new_missing_product():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    login("tester")
    before = uploaded_files()

    response = review_new_post(product_name="없는 상품")
    assert response.status_code == 400
    assert "없는 상품이에요." in response.get_data(as_text=True)
    assert uploaded_files() == before


def check_review_new_rating_out_of_range():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="owner")
    login("tester")
    before = uploaded_files()

    response = review_new_post(rating="9")
    assert response.status_code == 400
    assert "별점을 1~5점 중에서 골라 주세요." in response.get_data(as_text=True)
    assert uploaded_files() == before


def check_review_new_own_product():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="tester")
    login("tester")
    before = uploaded_files()

    response = review_new_post()
    assert response.status_code == 400
    assert "내가 올린 상품에는 리뷰를 쓸 수 없어요." in response.get_data(as_text=True)
    assert uploaded_files() == before


def check_review_new_duplicate():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="owner")
    key = product.product_key("아이패드 1/2")
    fake_db.child("reviews").child(key).set(
        {
            "product_name": "아이패드 1/2",
            "reviewer": "someone",
            "seller": "owner",
            "rating": 4,
            "title": "t",
            "content": "c",
            "photo": "",
            "created_at": "x",
        }
    )
    login("tester")
    before = uploaded_files()

    response = review_new_post()
    assert response.status_code == 400
    assert "이미 리뷰를 작성한 상품이에요." in response.get_data(as_text=True)
    assert uploaded_files() == before


def check_review_new_validation_failure_does_not_save_photo():
    """검증(title 누락)에 실패하면 사진은 유효해도 저장되면 안 된다."""
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="owner")
    login("tester")
    before = uploaded_files()

    response = review_new_post(title="", photo=(io.BytesIO(b"\x89PNG"), "사진.png"))
    assert response.status_code == 400
    assert uploaded_files() == before


def check_review_new_db_none_does_not_save_photo():
    """db가 없으면 검증을 통과해도 사진을 저장하지 않고 flash만 한다."""
    review.db = None
    product.db = None
    login("tester")
    before = uploaded_files()

    response = review_new_post(product_name="컴퓨터구조 및 설계 5판", photo=(io.BytesIO(b"\x89PNG"), "사진.png"))
    assert response.status_code == 200
    assert "지금은 리뷰를 저장할 수 없어요." in response.get_data(as_text=True)
    assert uploaded_files() == before


def check_review_new_success_and_done():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="owner")
    key = product.product_key("아이패드 1/2")
    login("tester")
    before = uploaded_files()

    response = review_new_post(reviewer="someone_else", title="좋아요", content="잘 받았어요.")
    assert response.status_code == 302
    assert response.headers["Location"] == "/review/done"

    saved = fake_db.store["reviews"][key]
    assert saved["reviewer"] == "tester"  # 폼의 reviewer 값은 무시하고 session['id']를 쓴다
    assert saved["seller"] == "owner"  # products.seller를 복사해 저장한다
    assert saved["photo"] == ""
    assert uploaded_files() == before  # 사진을 올리지 않았으니 새 파일이 없어야 한다

    done = client.get("/review/done")
    assert done.status_code == 200
    text = done.get_data(as_text=True)
    assert "좋아요" in text and "잘 받았어요." in text and "tester" in text


def check_review_done_without_last_review():
    logout()
    with client.session_transaction() as sess:
        sess.pop("last_review", None)
    response = client.get("/review/done")
    assert response.status_code == 200
    assert "방금 등록한 리뷰 정보가 없어요." in response.get_data(as_text=True)


def test_review_new():
    # 다른 테스트 파일이 같은 product.UPLOAD_DIR을 공유하므로(수집 순서에 따라 바뀔 수 있다)
    # 이 테스트만의 깨끗한 업로드 폴더로 다시 잡아 둔다.
    product.UPLOAD_DIR = tempfile.mkdtemp()
    check_review_new_requires_login()
    check_review_new_missing_fields()
    check_review_new_missing_product()
    check_review_new_rating_out_of_range()
    check_review_new_own_product()
    check_review_new_duplicate()
    check_review_new_validation_failure_does_not_save_photo()
    check_review_new_db_none_does_not_save_photo()
    check_review_new_success_and_done()
    check_review_done_without_last_review()
    # 검증 실패·저장 불가 케이스 전체에서 static/uploads에 파일이 남지 않았는지 최종 확인한다
    assert uploaded_files() == set()


def make_review(**fields):
    review_data = {
        "product_name": "로지텍 키보드",
        "reviewer": "tester",
        "seller": "owner",
        "rating": 5,
        "title": "제목",
        "content": "내용",
        "photo": "",
        "created_at": "2026-10-06T10:00:00+09:00",
    }
    review_data.update(fields)
    return review_data


def check_review_detail_missing():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    assert client.get("/review/" + "없는 상품").status_code == 404


def check_review_detail_found():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, name="로지텍 키보드", seller="owner")
    key = product.product_key("로지텍 키보드")
    review_data = make_review()
    fake_db.child("reviews").child(key).set(review_data)

    with captured_templates() as templates:
        response = client.get("/review/" + "로지텍 키보드")
        assert response.status_code == 200
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == "review/detail.html"
        review_ctx = context["review"]
        for field in ("product_name", "reviewer", "seller", "rating", "title", "content", "photo"):
            assert review_ctx[field] == review_data[field]
        assert review_ctx["date"] == "2026.10.06"
        assert context["product"]["name"] == "로지텍 키보드"


def check_review_detail_product_deleted():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    key = product.product_key("지워진 상품")
    fake_db.child("reviews").child(key).set(make_review(product_name="지워진 상품"))
    # 상품은 저장하지 않는다 (지워진 상태를 흉내 낸다)

    with captured_templates() as templates:
        response = client.get("/review/" + "지워진 상품")
        assert response.status_code == 200
        _, context = templates[0]
        assert context["product"] is None


def check_review_detail_name_with_slash():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_product(fake_db, seller="owner")  # 기본 상품명 "아이패드 1/2"
    key = product.product_key("아이패드 1/2")
    fake_db.child("reviews").child(key).set(make_review(product_name="아이패드 1/2"))

    with captured_templates() as templates:
        response = client.get("/review/" + "아이패드 1/2")
        assert response.status_code == 200
        _, context = templates[0]
        assert context["review"]["product_name"] == "아이패드 1/2"
        assert context["product"]["name"] == "아이패드 1/2"


def check_review_detail_date_handles_missing_created_at():
    """created_at이 빈 문자열이거나 필드 자체가 없어도 오류 없이 date를 ''로 넣는다."""
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    key = product.product_key("로지텍 키보드")

    fake_db.child("reviews").child(key).set(make_review(created_at=""))
    with captured_templates() as templates:
        response = client.get("/review/" + "로지텍 키보드")
        assert response.status_code == 200
        assert templates[0][1]["review"]["date"] == ""

    review_data = make_review()
    del review_data["created_at"]
    fake_db.child("reviews").child(key).set(review_data)
    with captured_templates() as templates:
        response = client.get("/review/" + "로지텍 키보드")
        assert response.status_code == 200
        assert templates[0][1]["review"]["date"] == ""


def test_review_detail():
    check_review_detail_missing()
    check_review_detail_found()
    check_review_detail_product_deleted()
    check_review_detail_name_with_slash()
    check_review_detail_date_handles_missing_created_at()


def seed_review(fake_db, **fields):
    review_data = make_review(**fields)
    key = product.product_key(review_data["product_name"])
    fake_db.child("reviews").child(key).set(review_data)
    return review_data


def check_review_list_empty():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db

    with captured_templates() as templates:
        response = client.get("/review")
        assert response.status_code == 200
        _, context = templates[0]
        assert context["reviews"] == []
        assert context["total"] == 0
        assert context["total_pages"] == 1
        assert context["page"] == 1
        assert context["seller"] == ""
        assert context["seller_info"] is None


def check_review_list_sorted_newest_first():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_review(fake_db, product_name="오래된 리뷰", created_at="2026-01-01T00:00:00+09:00")
    seed_review(fake_db, product_name="최신 리뷰", created_at="2026-06-01T00:00:00+09:00")
    seed_review(fake_db, product_name="중간 리뷰", created_at="2026-03-01T00:00:00+09:00")

    with captured_templates() as templates:
        response = client.get("/review")
        assert response.status_code == 200
        reviews = templates[0][1]["reviews"]
        assert [r["product_name"] for r in reviews] == ["최신 리뷰", "중간 리뷰", "오래된 리뷰"]


def check_review_list_seller_filter():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_review(fake_db, product_name="상품1", seller="owner", rating=5)
    seed_review(fake_db, product_name="상품2", seller="owner", rating=4)
    seed_review(fake_db, product_name="상품3", seller="other", rating=3)

    with captured_templates() as templates:
        response = client.get("/review?seller=owner")
        assert response.status_code == 200
        _, context = templates[0]
        assert {r["product_name"] for r in context["reviews"]} == {"상품1", "상품2"}
        assert context["total"] == 2
        assert context["seller"] == "owner"
        assert context["seller_info"] == {"id": "owner", "avg_rating": 4.5, "count": 2}


def check_review_list_unknown_seller():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_review(fake_db, seller="owner")

    with captured_templates() as templates:
        response = client.get("/review?seller=nobody")
        assert response.status_code == 200
        _, context = templates[0]
        assert context["reviews"] == []
        assert context["total"] == 0
        assert context["seller_info"] == {"id": "nobody", "avg_rating": 0, "count": 0}


def check_review_list_pagination():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    total_reviews = review.REVIEW_PAGE_SIZE + 3
    for i in range(total_reviews):
        seed_review(fake_db, product_name=f"상품{i}", created_at=f"2026-01-{i + 1:02d}T00:00:00+09:00")

    with captured_templates() as templates:
        response = client.get("/review")
        assert response.status_code == 200
        _, context = templates[0]
        assert context["total"] == total_reviews
        assert context["total_pages"] == 2
        assert context["page"] == 1
        assert len(context["reviews"]) == review.REVIEW_PAGE_SIZE

    with captured_templates() as templates:
        response = client.get("/review?page=2")
        assert response.status_code == 200
        _, context = templates[0]
        assert context["page"] == 2
        assert len(context["reviews"]) == 3


def check_review_list_page_clamped():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_review(fake_db, product_name="상품")  # 리뷰 1개뿐이라 total_pages는 1이다

    for page_value in ("abc", "0", "-5", "999"):
        with captured_templates() as templates:
            response = client.get("/review?page=" + page_value)
            assert response.status_code == 200
            assert templates[0][1]["page"] == 1


def check_seller_rating_standalone():
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_review(fake_db, product_name="상품1", seller="owner", rating=5)
    seed_review(fake_db, product_name="상품2", seller="owner", rating=4)
    seed_review(fake_db, product_name="상품3", seller="owner", rating=4)

    assert review.seller_rating("owner") == (4.3, 3)
    assert review.seller_rating("nobody") == (0, 0)


def check_review_list_reads_reviews_once():
    """review_list가 이미 읽은 reviews 목록을 seller_rating에 넘겨서 /reviews를 한 번만 읽어야 한다."""
    fake_db = FakeDb()
    review.db = fake_db
    product.db = fake_db
    seed_review(fake_db, product_name="상품1", seller="owner", rating=5)
    seed_review(fake_db, product_name="상품2", seller="owner", rating=3)

    response = client.get("/review?seller=owner")
    assert response.status_code == 200
    reads = [p for p in fake_db.get_log if p == ("reviews",)]
    assert len(reads) == 1, f"/reviews를 {len(reads)}번 읽었다"


def check_review_list_db_none():
    review.db = None
    product.db = None

    with captured_templates() as templates:
        response = client.get("/review")
        assert response.status_code == 200
        assert templates[0][1]["reviews"] == []


def test_review_list():
    check_review_list_empty()
    check_review_list_sorted_newest_first()
    check_review_list_seller_filter()
    check_review_list_unknown_seller()
    check_review_list_pagination()
    check_review_list_page_clamped()
    check_seller_rating_standalone()
    check_review_list_reads_reviews_once()
    check_review_list_db_none()
