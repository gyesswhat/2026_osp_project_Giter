"""찜(product_like) 라우트 확인

실행: (apps/be에서) python -m pytest test_review.py
pyrebase db를 흉내 내는 FakeDb를 review.db, product.db에 주입해서 찜 추가/취소를 확인한다.
"""

from urllib.parse import quote

from core import app
# 헤더의 url_for가 찾는 라우트를 모두 등록한다 (app.py와 같은 import)
from routes import auction, auth, chat, my, product, review, wanted  # noqa: F401

client = app.test_client()


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

    def child(self, key):
        self.path.append(str(key))
        return self

    def get(self):
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
