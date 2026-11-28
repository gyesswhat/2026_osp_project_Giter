"""구해요 글쓰기(wanted_new) 라우트 확인

실행: (apps/be에서) python -m pytest test_wanted.py
pyrebase db를 흉내 내는 FakeDb를 wanted.db에 주입해서 저장 내용을 확인한다.
"""

import io
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import date, timedelta

import pytest
from flask import template_rendered

from core import app
# 헤더의 url_for가 찾는 라우트를 모두 등록한다 (app.py와 같은 import)
from routes import auction, auth, chat, my, product, review, wanted  # noqa: F401

client = app.test_client()


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


class FakeSnapshot:
    def __init__(self, value):
        self._value = value

    def val(self):
        return self._value


class FakeDb:
    """pyrebase처럼 하나의 객체가 경로 상태를 들고 있다. (test_review.py의 FakeDb + push)

    child()는 self.path에 이어 붙이고 self를 반환한다(새 객체를 만들지 않는다).
    get()/set()/remove()/push()는 실행 후 self.path를 비운다.
    """

    def __init__(self):
        self.store = {}
        self.path = []
        self.get_log = []

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

    def push(self, value):
        """새 키를 만들어 path 아래에 저장하고 pyrebase처럼 {"name": 키}를 반환한다."""
        assert self.path, "루트 경로(path가 비어 있음)에 push()를 호출했어요."
        key = "-" + uuid.uuid4().hex
        node = self.store
        for key_part in self.path:
            node = node.setdefault(key_part, {})
        node[key] = value
        self.path = []
        return {"name": key}

    def update(self, value):
        """path 아래 dict에 value의 키만 덮어쓴다 (pyrebase update처럼 나머지 필드는 그대로)."""
        assert self.path, "루트 경로(path가 비어 있음)에 update()를 호출했어요."
        node = self.store
        for key_part in self.path:
            node = node.setdefault(key_part, {})
        node.update(value)
        self.path = []
        return value


@pytest.fixture(autouse=True)
def fake_env():
    """테스트마다 새 FakeDb와 깨끗한 업로드 폴더, 로그인 상태를 준비한다."""
    original_db = wanted.db
    original_upload = product.UPLOAD_DIR
    fake_db = FakeDb()
    wanted.db = fake_db
    product.UPLOAD_DIR = tempfile.mkdtemp()
    login("tester")
    yield fake_db
    wanted.db = original_db
    product.UPLOAD_DIR = original_upload


def login(user_id):
    with client.session_transaction() as sess:
        sess["id"] = user_id


def logout():
    with client.session_transaction() as sess:
        sess.pop("id", None)


def uploaded_files():
    return set(os.listdir(product.UPLOAD_DIR))


def valid_form(**overrides):
    form = {
        "name": "운영체제 10판",
        "category": "book",
        "budget": "30000",
        "condition": "light_use",
        "due_date": (date.today() + timedelta(days=3)).isoformat(),
        "places": ["ECC"],
        "description": "  표지 상태만 괜찮으면 돼요.  ",
    }
    form.update(overrides)
    return {key: value for key, value in form.items() if value is not None}


def post_new(form):
    return client.post("/wanted/new", data=form, content_type="multipart/form-data")


def saved_posts(fake_db):
    return list(fake_db.store.get("wanted", {}).values())


def post_and_capture(form):
    with captured_templates() as templates:
        response = post_new(form)
    return response, templates


# 1. 로그인
def test_get_requires_login():
    logout()
    response = client.get("/wanted/new")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_post_requires_login(fake_env):
    logout()
    response = post_new(valid_form())
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    assert saved_posts(fake_env) == []


def test_get_renders_form():
    with captured_templates() as templates:
        response = client.get("/wanted/new")
    assert response.status_code == 200
    template, context = templates[0]
    assert template.name == "wanted/new.html"
    assert "form" not in context and "errors" not in context


# 2. 검증 실패
@pytest.mark.parametrize(
    "overrides, field, message",
    [
        ({"name": "   "}, "name", "찾는 물건 이름을 입력해 주세요."),
        ({"name": None}, "name", "찾는 물건 이름을 입력해 주세요."),
        ({"budget": None}, "budget", "예산은 1원 이상 올바른 금액으로 입력해 주세요."),
        ({"budget": "0"}, "budget", "예산은 1원 이상 올바른 금액으로 입력해 주세요."),
        ({"budget": "-5000"}, "budget", "예산은 1원 이상 올바른 금액으로 입력해 주세요."),
        ({"budget": "삼만원"}, "budget", "예산은 1원 이상 올바른 금액으로 입력해 주세요."),
        ({"condition": None}, "condition", "괜찮은 상태를 골라 주세요."),
        ({"condition": "broken"}, "condition", "괜찮은 상태를 골라 주세요."),
        ({"category": "food"}, "category", "분류를 골라 주세요."),
        ({"due_date": None}, "due_date", "필요한 날을 선택해 주세요."),
        ({"due_date": "2026/12/01"}, "due_date", "날짜 형식이 올바르지 않아요."),
        ({"due_date": "2026-02-30"}, "due_date", "날짜 형식이 올바르지 않아요."),
        (
            {"due_date": (date.today() - timedelta(days=1)).isoformat()},
            "due_date",
            "오늘 이후 날짜로 선택해 주세요.",
        ),
        ({"places": None}, "places", "거래 장소를 하나 이상 골라 주세요."),
        ({"places": ["ECC", "강남역"]}, "places", "거래 장소를 다시 골라 주세요."),
        ({"picture": (io.BytesIO(b"GIF"), "a.gif")}, "picture", "JPG, PNG 파일만 올릴 수 있어요."),
    ],
)
def test_validation_errors(fake_env, overrides, field, message):
    response, templates = post_and_capture(valid_form(**overrides))
    assert response.status_code == 400
    template, context = templates[0]
    assert template.name == "wanted/new.html"
    assert context["errors"][field] == message
    assert list(context["errors"]) == [field]
    assert saved_posts(fake_env) == []
    assert uploaded_files() == set()


def test_failure_passes_form_dict_with_places_list():
    form = valid_form(name="", places=["ECC", "아산공학관", "기숙사"])
    response, templates = post_and_capture(form)
    assert response.status_code == 400
    context = templates[0][1]
    assert isinstance(context["form"], dict)
    assert context["form"]["places"] == ["ECC", "아산공학관", "기숙사"]
    assert context["form"]["budget"] == "30000"
    # 다시 그린 화면에서 칩 세 개가 모두 선택된 상태로 나온다
    html = response.get_data(as_text=True)
    for place in ("ECC", "아산공학관", "기숙사"):
        assert f'value="{place}"' in html


def test_validation_failure_does_not_save_picture(fake_env):
    form = valid_form(name="", picture=(io.BytesIO(b"\x89PNG"), "사진.png"))
    response = post_new(form)
    assert response.status_code == 400
    assert uploaded_files() == set()
    assert saved_posts(fake_env) == []


# 3. 저장 불가
def test_db_none_shows_form_without_saving_picture():
    wanted.db = None
    form = valid_form(picture=(io.BytesIO(b"\x89PNG"), "사진.png"))
    response, templates = post_and_capture(form)
    assert response.status_code == 200
    assert templates[0][0].name == "wanted/new.html"
    assert "지금은 글을 저장할 수 없어요." in response.get_data(as_text=True)
    assert uploaded_files() == set()


# 4. 성공
def test_success_saves_post_and_redirects(fake_env):
    response = post_new(valid_form())
    assert response.status_code == 302
    assert response.headers["Location"] == "/wanted"
    with client.session_transaction() as sess:
        assert ("message", "글을 올렸어요.") in sess["_flashes"]

    [post] = saved_posts(fake_env)
    created_at = post.pop("created_at")
    assert "T" in created_at and created_at.startswith(date.today().isoformat()[:4])
    assert post == {
        "writer": "tester",
        "name": "운영체제 10판",
        "category": "book",
        "budget": 30000,
        "condition": "light_use",
        "due_date": (date.today() + timedelta(days=3)).isoformat(),
        "places": {"ECC": True},
        "description": "표지 상태만 괜찮으면 돼요.",
        "img_path": "",
        "state": "open",
        "picked_offer_id": "",
        "offer_count": 0,
    }
    assert uploaded_files() == set()


def test_writer_comes_from_session_not_form(fake_env):
    post_new(valid_form(writer="someone_else"))
    [post] = saved_posts(fake_env)
    assert post["writer"] == "tester"


def test_budget_with_comma_is_saved_as_int(fake_env):
    response = post_new(valid_form(budget="30,000"))
    assert response.status_code == 302
    assert saved_posts(fake_env)[0]["budget"] == 30000


def test_due_date_today_is_allowed(fake_env):
    response = post_new(valid_form(due_date=date.today().isoformat()))
    assert response.status_code == 302
    assert saved_posts(fake_env)[0]["due_date"] == date.today().isoformat()


def test_empty_category_is_saved_as_etc(fake_env):
    response = post_new(valid_form(category=""))
    assert response.status_code == 302
    assert saved_posts(fake_env)[0]["category"] == "etc"


def test_missing_category_is_saved_as_etc(fake_env):
    response = post_new(valid_form(category=None))
    assert response.status_code == 302
    assert saved_posts(fake_env)[0]["category"] == "etc"


def test_multiple_places_are_saved_as_keys(fake_env):
    response = post_new(valid_form(places=["ECC", "아산공학관", "포스코관"]))
    assert response.status_code == 302
    assert saved_posts(fake_env)[0]["places"] == {"ECC": True, "아산공학관": True, "포스코관": True}


def test_success_with_picture_saves_file(fake_env):
    response = post_new(valid_form(picture=(io.BytesIO(b"\x89PNG"), "photo.png")))
    assert response.status_code == 302
    img_path = saved_posts(fake_env)[0]["img_path"]
    assert img_path.endswith("_photo.png")
    assert uploaded_files() == {img_path}


# 5. 목록 (wanted_list)
def seed_wanted(fake_db, wanted_id, **fields):
    post = {
        "writer": "owner",
        "name": f"글 {wanted_id}",
        "category": "book",
        "budget": 10000,
        "condition": "any",
        "due_date": "2026-11-30",
        "places": {"ECC": True},
        "description": "",
        "img_path": "",
        "state": "open",
        "picked_offer_id": "",
        "offer_count": 0,
        "created_at": "2026-11-26T10:00:00+09:00",
    }
    post.update(fields)
    fake_db.child("wanted").child(wanted_id).set(post)
    return post


def get_list(query=""):
    with captured_templates() as templates:
        response = client.get("/wanted" + query)
    assert response.status_code == 200
    template, context = templates[0]
    assert template.name == "wanted/list.html"
    return response, context


def ids(context):
    return [item["id"] for item in context["items"]]


def seed_many(fake_db, count):
    """created_at이 1분씩 늦어지는 글 count개. 가장 최신은 w{count-1:02d}"""
    for i in range(count):
        seed_wanted(fake_db, f"w{i:02d}", created_at=f"2026-11-26T10:{i:02d}:00+09:00")


def test_list_does_not_require_login():
    logout()
    get_list()


def test_list_empty():
    response, context = get_list()
    assert context["items"] == []
    assert context["total"] == 0
    assert context["page"] == 1
    assert context["total_pages"] == 1
    assert context["category"] == "all"
    assert context["state"] == "all"
    assert "해당 분류에 올라온 구해요 글이 없어요." in response.get_data(as_text=True)


def test_list_db_none_is_empty():
    wanted.db = None
    _, context = get_list()
    assert context["items"] == []
    assert context["total"] == 0
    assert context["total_pages"] == 1


def test_list_reads_wanted_once(fake_env):
    seed_many(fake_env, 3)
    get_list("?category=book&state=open&page=2")
    assert fake_env.get_log == [("wanted",)]


def test_list_sorted_newest_first(fake_env):
    seed_wanted(fake_env, "old", created_at="2026-11-01T09:00:00+09:00")
    seed_wanted(fake_env, "new", created_at="2026-11-26T09:00:00+09:00")
    seed_wanted(fake_env, "mid", created_at="2026-11-15T09:00:00+09:00")
    _, context = get_list()
    assert ids(context) == ["new", "mid", "old"]


def test_list_category_filter(fake_env):
    seed_wanted(fake_env, "b", category="book")
    seed_wanted(fake_env, "d", category="digital")
    seed_wanted(fake_env, "e", category="etc")
    _, context = get_list("?category=digital")
    assert ids(context) == ["d"]
    assert context["category"] == "digital"
    assert context["total"] == 1


@pytest.mark.parametrize("state, expected", [("open", {"o"}), ("done", {"d"}), ("all", {"o", "d"})])
def test_list_state_filter(fake_env, state, expected):
    seed_wanted(fake_env, "o", state="open")
    seed_wanted(fake_env, "d", state="done")
    _, context = get_list(f"?state={state}")
    assert set(ids(context)) == expected
    assert context["state"] == state


def test_list_invalid_category_and_state_are_all(fake_env):
    seed_wanted(fake_env, "b", category="book", state="open")
    seed_wanted(fake_env, "d", category="digital", state="done")
    _, context = get_list("?category=food&state=sold")
    assert context["category"] == "all"
    assert context["state"] == "all"
    assert set(ids(context)) == {"b", "d"}


def test_list_pages(fake_env):
    seed_many(fake_env, 13)
    _, first = get_list()
    assert len(first["items"]) == 12
    assert first["items"][0]["id"] == "w12"
    assert first["total"] == 13
    assert first["total_pages"] == 2

    _, second = get_list("?page=2")
    assert ids(second) == ["w00"]
    assert second["page"] == 2


@pytest.mark.parametrize("page, expected", [("abc", 1), ("0", 1), ("-1", 1), ("99", 2)])
def test_list_page_is_clamped(fake_env, page, expected):
    seed_many(fake_env, 13)
    _, context = get_list(f"?page={page}")
    assert context["page"] == expected


def test_list_item_fields(fake_env):
    seed_wanted(
        fake_env,
        "x1",
        writer="kim",
        name="공학용 계산기",
        category="digital",
        budget=15000,
        condition="like_new",
        due_date="2026-11-30",
        places={"ECC": True, "아산공학관": True},
        img_path="calc.png",
        state="open",
        offer_count=4,
        created_at="2026-11-26T10:00:00+09:00",
    )
    _, context = get_list()
    [item] = context["items"]
    assert item["id"] == "x1"
    assert item["writer"] == "kim"
    assert item["name"] == "공학용 계산기"
    assert item["category"] == "digital"
    assert item["budget"] == 15000
    assert item["condition"] == "like_new"
    assert item["due_date"] == "2026-11-30"
    assert sorted(item["places"]) == ["ECC", "아산공학관"]
    assert isinstance(item["places"], list)
    assert item["img_path"] == "calc.png"
    assert item["state"] == "open"
    assert item["offers"] == 4
    assert item["when"] == "11.30까지"
    assert item["date"] == "2026.11.26"


@pytest.mark.parametrize("bad", [None, "", "내일", "2026-02-30", "2026/11/30"])
def test_list_when_and_date_are_empty_when_missing_or_invalid(fake_env, bad):
    post = seed_wanted(fake_env, "x1")
    if bad is None:
        del post["due_date"], post["created_at"]
    else:
        post["due_date"] = post["created_at"] = bad
    _, context = get_list()
    [item] = context["items"]
    assert item["when"] == ""
    assert item["date"] == ""


def test_list_with_items_renders_detail_link(fake_env):
    """카드는 글 id를 넣어 url_for('wanted_detail', id=...)로 상세에 연결한다 (#67)."""
    seed_wanted(fake_env, "x1", name="공학용 계산기")
    response, _ = get_list()
    html = response.get_data(as_text=True)
    assert 'href="/wanted/detail/x1"' in html
    assert "공학용 계산기" in html


def test_detail_stub_returns_501():
    assert client.get("/wanted/detail").status_code == 501
    assert client.get("/wanted/detail/abc").status_code == 501


def test_new_post_appears_in_list_after_redirect():
    with captured_templates() as templates:
        response = client.post(
            "/wanted/new",
            data=valid_form(name="새로 올린 글", places=["ECC", "기숙사"]),
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert response.status_code == 200
    assert response.request.path == "/wanted"
    html = response.get_data(as_text=True)
    assert "글을 올렸어요." in html
    assert "새로 올린 글" in html
    template, context = templates[-1]
    assert template.name == "wanted/list.html"
    [item] = context["items"]
    assert item["name"] == "새로 올린 글"
    assert item["places"] == ["ECC", "기숙사"]
    assert item["writer"] == "tester"
    assert item["offers"] == 0
    assert item["state"] == "open"
    assert item["date"] == date.today().strftime("%Y.%m.%d")


# 6. 제안 보내기 (wanted_offer)
OFFER_DETAIL = "/wanted/detail/w1"


def seed_offer_target(fake_db, **fields):
    """제안을 받을 글. 글쓴이 owner, 예산 30000, 장소 ECC·아산공학관"""
    fields.setdefault("writer", "owner")
    fields.setdefault("budget", 30000)
    fields.setdefault("places", {"ECC": True, "아산공학관": True})
    return seed_wanted(fake_db, "w1", **fields)


def offer_form(**overrides):
    form = {"wanted_id": "w1", "price": "25000", "description": "  상태 좋아요  ", "place": "ECC"}
    form.update(overrides)
    return {key: value for key, value in form.items() if value is not None}


def post_offer(form):
    return client.post("/wanted/offer", data=form, content_type="multipart/form-data")


def saved_offers(fake_db, wanted_id="w1"):
    return list(fake_db.store.get("offers", {}).get(wanted_id, {}).values())


def offer_count(fake_db, wanted_id="w1"):
    return fake_db.store["wanted"][wanted_id]["offer_count"]


def last_flash():
    with client.session_transaction() as sess:
        return sess["_flashes"][-1]


def test_offer_requires_login(fake_env):
    seed_offer_target(fake_env)
    logout()
    response = post_offer(offer_form())
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    assert last_flash() == ("error", "제안하려면 로그인해 주세요.")
    assert saved_offers(fake_env) == []


@pytest.mark.parametrize("wanted_id", [None, "", "a/b", "a.b", "a#b", "a$b", "a[b]", "nope"])
def test_offer_bad_or_missing_wanted_is_404(fake_env, wanted_id):
    seed_offer_target(fake_env)
    response = post_offer(offer_form(wanted_id=wanted_id))
    assert response.status_code == 404
    assert saved_offers(fake_env) == []
    assert offer_count(fake_env) == 0


@pytest.mark.parametrize("wanted_id", [None, "", "a/b", "a[b]"])
def test_offer_bad_id_is_404_even_when_db_none(wanted_id):
    wanted.db = None
    response = post_offer(offer_form(wanted_id=wanted_id))
    assert response.status_code == 404


def test_offer_db_none_flashes_and_redirects():
    wanted.db = None
    response = post_offer(offer_form(picture=(io.BytesIO(b"\x89PNG"), "사진.png")))
    assert response.status_code == 302
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("error", "지금은 제안을 저장할 수 없어요.")
    assert uploaded_files() == set()


@pytest.mark.parametrize(
    "target, overrides, message",
    [
        ({"writer": "tester"}, {}, "내 글에는 제안할 수 없어요."),
        ({"state": "done"}, {}, "이미 구한 글이에요."),
        ({}, {"price": None}, "제안 금액을 1원 이상으로 입력해 주세요."),
        ({}, {"price": ""}, "제안 금액을 1원 이상으로 입력해 주세요."),
        ({}, {"price": "0"}, "제안 금액을 1원 이상으로 입력해 주세요."),
        ({}, {"price": "-5000"}, "제안 금액을 1원 이상으로 입력해 주세요."),
        ({}, {"price": "이만원"}, "제안 금액을 1원 이상으로 입력해 주세요."),
        ({}, {"price": "30001"}, "예산 30,000원 이하로 제안할 수 있어요."),
        ({"budget": 1500000}, {"price": "1,500,001"}, "예산 1,500,000원 이하로 제안할 수 있어요."),
        ({}, {"place": "기숙사"}, "거래 장소를 다시 골라 주세요."),
        ({}, {"picture": (io.BytesIO(b"GIF"), "a.gif")}, "JPG, PNG 파일만 올릴 수 있어요."),
        # 앞 단계에서 실패하면 뒤 단계의 사진은 저장하지 않는다
        ({}, {"price": "0", "picture": (io.BytesIO(b"\x89PNG"), "ok.png")}, "제안 금액을 1원 이상으로 입력해 주세요."),
        ({}, {"place": "기숙사", "picture": (io.BytesIO(b"\x89PNG"), "ok.png")}, "거래 장소를 다시 골라 주세요."),
    ],
)
def test_offer_failures(fake_env, target, overrides, message):
    seed_offer_target(fake_env, **target)
    response = post_offer(offer_form(**overrides))
    assert response.status_code == 302
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("error", message)
    assert saved_offers(fake_env) == []
    assert offer_count(fake_env) == 0
    assert uploaded_files() == set()


def test_offer_success_saves_offer_and_counts(fake_env):
    seed_offer_target(fake_env)
    response = post_offer(offer_form(seller="someone_else"))
    assert response.status_code == 302
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("message", "제안을 보냈어요.")

    [offer] = saved_offers(fake_env)
    created_at = offer.pop("created_at")
    assert created_at.startswith(date.today().isoformat()) and "T" in created_at
    assert offer == {
        "seller": "tester",
        "price": 25000,
        "description": "상태 좋아요",
        "place": "ECC",
        "img_path": "",
    }
    assert offer_count(fake_env) == 1
    # update는 offer_count만 바꾸고 나머지 필드는 그대로 둔다
    post = fake_env.store["wanted"]["w1"]
    assert post["state"] == "open" and post["budget"] == 30000 and post["writer"] == "owner"
    assert uploaded_files() == set()


def test_offer_price_equal_to_budget_is_allowed(fake_env):
    seed_offer_target(fake_env)
    response = post_offer(offer_form(price="30000"))
    assert response.status_code == 302
    assert saved_offers(fake_env)[0]["price"] == 30000


def test_offer_price_with_comma(fake_env):
    seed_offer_target(fake_env)
    post_offer(offer_form(price="25,000"))
    assert saved_offers(fake_env)[0]["price"] == 25000


def test_offer_empty_place_is_saved_as_empty(fake_env):
    seed_offer_target(fake_env)
    post_offer(offer_form(place=""))
    post_offer(offer_form(place=None))
    assert [offer["place"] for offer in saved_offers(fake_env)] == ["", ""]


def test_offer_with_picture_saves_file(fake_env):
    seed_offer_target(fake_env)
    post_offer(offer_form(picture=(io.BytesIO(b"\x89PNG"), "photo.png")))
    img_path = saved_offers(fake_env)[0]["img_path"]
    assert img_path.endswith("_photo.png")
    assert uploaded_files() == {img_path}


def test_offer_twice_counts_two(fake_env):
    seed_offer_target(fake_env)
    post_offer(offer_form(price="20000"))
    post_offer(offer_form(price="25000"))
    assert sorted(offer["price"] for offer in saved_offers(fake_env)) == [20000, 25000]
    assert offer_count(fake_env) == 2


def test_offer_helpers(fake_env):
    seed_offer_target(fake_env)
    offer_id = wanted.save_offer("w1", {"seller": "kim", "price": 1000})
    assert wanted.get_wanted("w1")["writer"] == "owner"
    assert wanted.get_wanted("nope") is None
    assert wanted.get_offer("w1", offer_id) == {"seller": "kim", "price": 1000}
    assert wanted.get_offer("w1", "a/b") is None
    assert wanted.load_offers("w1") == [{"seller": "kim", "price": 1000, "id": offer_id}]
    assert wanted.load_offers("nope") == []
    wanted.db = None
    assert wanted.get_wanted("w1") is None
    assert wanted.load_offers("w1") == []
    assert wanted.get_offer("w1", offer_id) is None


# 7. 제안 고르기 (wanted_pick)
def seed_pick_target(fake_db, **fields):
    """로그인 사용자(tester)가 쓴 글 w1과 그 글에 달린 제안 하나. offer_id를 반환한다."""
    fields.setdefault("writer", "tester")
    seed_offer_target(fake_db, **fields)
    return wanted.save_offer("w1", {"seller": "kim", "price": 25000, "description": "", "place": "ECC", "img_path": ""})


def pick_form(offer_id, **overrides):
    form = {"wanted_id": "w1", "offer_id": offer_id}
    form.update(overrides)
    return {key: value for key, value in form.items() if value is not None}


def post_pick(form):
    return client.post("/wanted/pick", data=form)


def stored_post(fake_db, wanted_id="w1"):
    return dict(fake_db.store["wanted"][wanted_id])


def test_pick_requires_login(fake_env):
    offer_id = seed_pick_target(fake_env)
    logout()
    response = post_pick(pick_form(offer_id))
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    assert last_flash() == ("error", "제안을 고르려면 로그인해 주세요.")
    assert stored_post(fake_env)["state"] == "open"


@pytest.mark.parametrize("wanted_id", [None, "", "a/b", "a.b", "a#b", "a$b", "a[b]", "nope"])
def test_pick_bad_or_missing_wanted_is_404(fake_env, wanted_id):
    offer_id = seed_pick_target(fake_env)
    response = post_pick(pick_form(offer_id, wanted_id=wanted_id))
    assert response.status_code == 404
    assert stored_post(fake_env)["state"] == "open"


def test_pick_bad_id_is_404_even_when_db_none():
    wanted.db = None
    assert post_pick(pick_form("o1", wanted_id="a/b")).status_code == 404


def test_pick_db_none_flashes_and_redirects():
    wanted.db = None
    response = post_pick(pick_form("o1"))
    assert response.status_code == 302
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("error", "지금은 저장할 수 없어요.")


def test_pick_not_writer_is_403(fake_env):
    offer_id = seed_pick_target(fake_env, writer="owner")
    before = stored_post(fake_env)
    response = post_pick(pick_form(offer_id))
    assert response.status_code == 403
    assert stored_post(fake_env) == before


def test_pick_already_done(fake_env):
    offer_id = seed_pick_target(fake_env, state="done", picked_offer_id="old")
    response = post_pick(pick_form(offer_id))
    assert response.status_code == 302
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("error", "이미 제안을 고른 글이에요.")
    assert stored_post(fake_env)["picked_offer_id"] == "old"


@pytest.mark.parametrize("offer_id", [None, "", "a/b", "a.b", "a#b", "a$b", "a[b]", "nope"])
def test_pick_bad_or_missing_offer(fake_env, offer_id):
    seed_pick_target(fake_env)
    before = stored_post(fake_env)
    response = post_pick(pick_form(offer_id))
    assert response.status_code == 302
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("error", "제안을 찾을 수 없어요.")
    assert stored_post(fake_env) == before


def test_pick_offer_of_another_post_fails(fake_env):
    seed_pick_target(fake_env)
    seed_wanted(fake_env, "w2", writer="tester")
    other_offer_id = wanted.save_offer("w2", {"seller": "lee", "price": 5000})
    before = stored_post(fake_env)
    response = post_pick(pick_form(other_offer_id))
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("error", "제안을 찾을 수 없어요.")
    assert stored_post(fake_env) == before


def test_pick_success_changes_only_pick_fields(fake_env):
    offer_id = seed_pick_target(fake_env, offer_count=1)
    before = stored_post(fake_env)
    response = post_pick(pick_form(offer_id))
    assert response.status_code == 302
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("message", "제안을 골랐어요.")
    assert stored_post(fake_env) == {**before, "picked_offer_id": offer_id, "state": "done"}
    assert "reservations" not in fake_env.store
    assert "chat_rooms" not in fake_env.store
    assert set(fake_env.store) == {"wanted", "offers"}


def test_pick_again_after_pick(fake_env):
    offer_id = seed_pick_target(fake_env)
    second_id = wanted.save_offer("w1", {"seller": "lee", "price": 20000})
    post_pick(pick_form(offer_id))
    response = post_pick(pick_form(second_id))
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("error", "이미 제안을 고른 글이에요.")
    assert stored_post(fake_env)["picked_offer_id"] == offer_id


def test_offer_after_pick_is_rejected(fake_env):
    offer_id = seed_pick_target(fake_env)
    post_pick(pick_form(offer_id))
    login("buyer")
    response = post_offer(offer_form())
    assert response.headers["Location"] == OFFER_DETAIL
    assert last_flash() == ("error", "이미 구한 글이에요.")
    assert len(saved_offers(fake_env)) == 1
    assert offer_count(fake_env) == 0
