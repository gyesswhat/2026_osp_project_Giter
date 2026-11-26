"""구해요 라우트: wanted_list, wanted_detail, wanted_new

wanted_detail은 아직 501을 반환하는 스텁이다(PR B에서 구현).
"""

import math
import re
from datetime import date, datetime

from flask import abort, flash, redirect, render_template, request, session, url_for

from core import app, db, to_int
from routes.product import save_picture, validate_picture

# 분류. 화면: 도서, 전자기기, 생활용품, 기타
CATEGORIES = ("book", "digital", "dorm", "etc")
# 괜찮은 상태. 화면: 거의 새것만, 사용감 조금, 상태 상관없음
CONDITIONS = ("like_new", "light_use", "any")
# 거래 장소(건물). 화면은 이 중 일부만 보여 준다
PLACES = ("ECC", "중앙도서관", "학생문화관", "포스코관", "아산공학관", "조형예술관", "학관", "기숙사", "기타")
# 글 상태. open: 구하는 중, done: 구했어요
STATES = ("open", "done")
WANTED_PAGE_SIZE = 12
FORM_FIELDS =("name", "category", "budget", "condition", "due_date", "description")


@app.route("/wanted")
def wanted_list():
    """구해요 목록. 로그인 불필요. 쿼리: category(all 기본), state(all 기본), page(1부터)"""
    category = request.args.get("category", "all")
    if category not in CATEGORIES:
        category = "all"
    state = request.args.get("state", "all")
    if state not in STATES:
        state = "all"

    posts = load_wanted()
    posts.sort(key=lambda post: post["created_at"], reverse=True)
    if category != "all":
        posts = [post for post in posts if post["category"] == category]
    if state != "all":
        posts = [post for post in posts if post["state"] == state]

    total = len(posts)
    total_pages = max(1, math.ceil(total / WANTED_PAGE_SIZE))
    page = min(max(1, to_int(request.args.get("page"), 1)), total_pages)
    return render_template(
        "wanted/list.html",
        items=posts[(page - 1) * WANTED_PAGE_SIZE : page * WANTED_PAGE_SIZE],
        category=category,
        state=state,
        page=page,
        total_pages=total_pages,
        total=total,
    )


def load_wanted():
    """/wanted 전체를 한 번 읽어 목록 카드용 dict 리스트로 만든다. db가 없으면 빈 목록이다."""
    if db is None:
        return []
    stored = db.child("wanted").get().val() or {}
    return [to_list_item(wanted_id, post) for wanted_id, post in stored.items()]


def to_list_item(wanted_id, post):
    """저장된 글을 list.html이 쓰는 필드로 바꾼다. places는 리스트, offers는 offer_count."""
    places = post.get("places") or {}
    return {
        "id": wanted_id,
        "writer": post.get("writer", ""),
        "name": post.get("name", ""),
        "category": post.get("category", "etc"),
        "budget": post.get("budget", 0),
        "condition": post.get("condition", ""),
        "due_date": post.get("due_date", ""),
        "places": list(places) if isinstance(places, dict) else [],
        "img_path": post.get("img_path", ""),
        "state": post.get("state", "open"),
        "offers": post.get("offer_count", 0),
        "when": format_when(post.get("due_date")),
        "date": format_date(post.get("created_at")),
        "created_at": post.get("created_at") or "",
    }


def parse_day(value):
    """YYYY-MM-DD로 시작하는 문자열이면 date, 아니면 None"""
    if not isinstance(value, str) or not re.match(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def format_when(due_date):
    """2026-11-30 → "11.30까지". 없거나 형식이 틀리면 "" """
    day = parse_day(due_date)
    return f"{day:%m.%d}까지" if day else ""


def format_date(created_at):
    """2026-11-26T10:00:00+09:00 → "2026.11.26". 없거나 형식이 틀리면 "" """
    day = parse_day(created_at)
    return f"{day:%Y.%m.%d}" if day else ""


@app.route("/wanted/detail")
@app.route("/wanted/detail/<id>")
def wanted_detail(id=None):
    """구해요 상세 스텁. list.html 카드가 url_for('wanted_detail')을 호출하므로 등록해 둔다. PR B에서 구현한다."""
    abort(501)


@app.route("/wanted/new", methods=["GET", "POST"])
def wanted_new():
    """구해요 글쓰기. 로그인 필요.

    POST(multipart/form-data): name, category, budget, condition, due_date, places(여러 개), description, picture
    """
    writer = session.get("id")
    if writer is None:
        flash("글을 쓰려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))

    if request.method == "GET":
        return render_template("wanted/new.html")

    # 템플릿이 f.get('places', [...])로 여러 칩을 다시 고르므로 request.form 대신 dict + 리스트로 넘긴다
    form = {field: request.form.get(field, "") for field in FORM_FIELDS}
    form["places"] = request.form.getlist("places")
    picture = request.files.get("picture")

    post, errors = validate_wanted_form(form, picture)
    if errors:
        return render_template("wanted/new.html", form=form, errors=errors), 400

    if db is None:
        flash("지금은 글을 저장할 수 없어요.", "error")
        return render_template("wanted/new.html", form=form, errors={})

    post.update(
        {
            "writer": writer,
            "img_path": save_picture(picture) if picture and picture.filename else "",
            "state": "open",
            "picked_offer_id": "",
            "offer_count": 0,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
    )
    save_wanted(post)
    flash("글을 올렸어요.")
    # ponytail: PR B에서 wanted_detail(id=새 id)로 바꾼다
    return redirect(url_for("wanted_list"))


def validate_wanted_form(form, picture):
    """글쓰기 폼을 검증한다. (저장할 필드 dict, errors dict)를 반환한다.

    form은 dict이고 places는 리스트다. 사진은 검증만 하고 저장하지 않는다.
    """
    errors = {}
    post = {}

    post["name"] = form.get("name", "").strip()
    if not post["name"]:
        errors["name"] = "찾는 물건 이름을 입력해 주세요."

    post["category"] = form.get("category", "").strip() or "etc"
    if post["category"] not in CATEGORIES:
        errors["category"] = "분류를 골라 주세요."

    # 공백은 여기 정규식이 지우고, 쉼표는 to_int가 지운다.
    # "-5000"이 5000으로 통과하지 않도록 다른 문자는 지우지 않는다
    post["budget"] = to_int(re.sub(r"\s", "", form.get("budget", "")))
    if post["budget"] is None or post["budget"] <= 0:
        errors["budget"] = "예산은 1원 이상 올바른 금액으로 입력해 주세요."

    post["condition"] = form.get("condition", "")
    if post["condition"] not in CONDITIONS:
        errors["condition"] = "괜찮은 상태를 골라 주세요."

    post["due_date"] = form.get("due_date", "").strip()
    due_date_error = validate_due_date(post["due_date"])
    if due_date_error is not None:
        errors["due_date"] = due_date_error

    places = form.get("places", [])
    if not places:
        errors["places"] = "거래 장소를 하나 이상 골라 주세요."
    elif any(place not in PLACES for place in places):
        errors["places"] = "거래 장소를 다시 골라 주세요."
    post["places"] = {place: True for place in places}

    post["description"] = form.get("description", "").strip()

    if picture and picture.filename:
        picture_error = validate_picture(picture)
        if picture_error is not None:
            errors["picture"] = picture_error

    return post, errors


def validate_due_date(value):
    """YYYY-MM-DD이고 오늘 포함 이후면 None, 아니면 오류 문구"""
    if not value:
        return "필요한 날을 선택해 주세요."
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return "날짜 형식이 올바르지 않아요."
    try:
        due = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return "날짜 형식이 올바르지 않아요."
    if due < date.today():
        return "오늘 이후 날짜로 선택해 주세요."
    return None


def save_wanted(post):
    """/wanted/{push id}에 저장하고 새 id를 반환한다. pyrebase 규칙대로 한 줄 체인으로 실행한다."""
    return db.child("wanted").push(post)["name"]
