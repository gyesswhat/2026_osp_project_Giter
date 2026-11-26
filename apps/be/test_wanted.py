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
