"""구해요 라우트: wanted_list, wanted_detail, wanted_new, wanted_offer, wanted_pick"""

import math
import re
from datetime import date, datetime

from flask import abort, flash, redirect, render_template, request, session, url_for

from core import app, db, to_int
from routes.product import save_picture, validate_picture
from routes.review import load_reviews, seller_rating

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


@app.route("/wanted/detail/<id>")
def wanted_detail(id):
    """구해요 상세. 로그인 불필요. 쿼리: sort(low 기본 | new)

    id 형식이 틀리거나 글이 없거나 DB에 연결하지 못하면 404.
    제안은 low면 낮은 가격순(같은 금액이면 최신 먼저), new면 최신순으로 정렬해 넘긴다.
    제안이 있을 때만 /reviews를 한 번 읽어 판매자 평균 별점(rating, 리뷰가 없으면 None)을 붙인다.
    """
    if not is_valid_key(id):
        abort(404)
    stored = get_wanted(id)
    if stored is None:
        abort(404)

    sort = request.args.get("sort", "low")
    if sort not in ("low", "new"):
        sort = "low"

    post = {
        **to_list_item(id, stored),
        "description": stored.get("description", ""),
        "picked_offer_id": stored.get("picked_offer_id") or "",
        "offer_count": stored.get("offer_count") or 0,
    }

    raw_offers = load_offers(id)
    reviews = load_reviews() if raw_offers else []
    offers = [to_offer_item(offer, reviews) for offer in raw_offers]
    # 정렬은 안정적이므로 최신순으로 먼저 정렬한 뒤 금액순으로 다시 정렬하면 같은 금액은 최신이 먼저 남는다
    offers.sort(key=lambda offer: offer["created_at"], reverse=True)
    if sort == "low":
        offers.sort(key=lambda offer: offer["price"])

    user_id = session.get("id")
    is_writer = bool(user_id) and user_id == stored.get("writer")
    return render_template("wanted/detail.html", post=post, offers=offers, is_writer=is_writer, sort=sort)


def to_offer_item(offer, reviews):
    """저장된 제안을 detail.html이 쓰는 필드로 바꾼다. reviews는 이미 읽은 /reviews 목록이다."""
    seller = offer.get("seller", "")
    avg_rating, count = seller_rating(seller, reviews)
    created_at = offer.get("created_at") or ""
    return {
        "id": offer["id"],
        "seller": seller,
        "price": offer.get("price", 0),
        "description": offer.get("description", ""),
        "place": offer.get("place", ""),
        "img_path": offer.get("img_path", ""),
        "rating": avg_rating if count else None,
        "date": format_date(created_at),
        "created_at": created_at,
    }


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
    new_id = save_wanted(post)
    flash("글을 올렸어요.")
    return redirect(url_for("wanted_detail", id=new_id))


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


# Firebase 키에 쓸 수 없는 문자. 이런 값이 child()에 들어가면 다른 경로를 가리키게 된다
KEY_FORBIDDEN = re.compile(r"[/.#$\[\]]")


@app.route("/wanted/offer", methods=["POST"])
def wanted_offer():
    """제안 보내기. 로그인 필요. POST(multipart/form-data): wanted_id, price, description, place, picture

    글이 없거나 id 형식이 틀리면 404. 그 밖의 실패는 flash 후 wanted_detail로 redirect한다.
    """
    seller = session.get("id")
    if seller is None:
        flash("제안하려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))

    wanted_id = request.form.get("wanted_id", "")
    if not is_valid_key(wanted_id):
        abort(404)
    detail_url = url_for("wanted_detail", id=wanted_id)

    # get_wanted는 db가 없으면 None이라 404가 되므로, 저장 불가 안내를 먼저 확인한다
    if db is None:
        flash("지금은 제안을 저장할 수 없어요.", "error")
        return redirect(detail_url)

    post = get_wanted(wanted_id)
    if post is None:
        abort(404)

    picture = request.files.get("picture")
    offer, error = validate_offer_form(request.form, picture, post, seller)
    if error is not None:
        flash(error, "error")
        return redirect(detail_url)

    offer.update(
        {
            "seller": seller,
            "img_path": save_picture(picture) if picture and picture.filename else "",
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
    )
    save_offer(wanted_id, offer)
    # ponytail: 읽은 값 + 1을 저장하므로 두 명이 동시에 보내면 하나가 덮일 수 있다. 문제가 되면 transaction으로 바꾼다
    db.child("wanted").child(wanted_id).update({"offer_count": post.get("offer_count", 0) + 1})
    flash("제안을 보냈어요.")
    return redirect(detail_url)


@app.route("/wanted/pick", methods=["POST"])
def wanted_pick():
    """제안 고르기. 로그인 필요, 글쓴이만. POST: wanted_id, offer_id

    picked_offer_id와 state=done만 저장한다. 약속·채팅방은 만들지 않고(겨레님 결정), 다시 고르기는 없다.
    글이 없거나 id 형식이 틀리면 404, 글쓴이가 아니면 403. 그 밖의 실패는 flash 후 wanted_detail로 redirect한다.
    """
    user_id = session.get("id")
    if user_id is None:
        flash("제안을 고르려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))

    wanted_id = request.form.get("wanted_id", "")
    if not is_valid_key(wanted_id):
        abort(404)
    detail_url = url_for("wanted_detail", id=wanted_id)

    if db is None:
        flash("지금은 저장할 수 없어요.", "error")
        return redirect(detail_url)

    post = get_wanted(wanted_id)
    if post is None:
        abort(404)
    if post.get("writer") != user_id:
        abort(403)
    if post.get("state") != "open":
        flash("이미 제안을 고른 글이에요.", "error")
        return redirect(detail_url)

    # 제안은 /offers/{wanted_id}/{offer_id}에서 찾으므로 다른 글의 제안 id는 여기서 걸린다
    offer_id = request.form.get("offer_id", "")
    if not is_valid_key(offer_id) or get_offer(wanted_id, offer_id) is None:
        flash("제안을 찾을 수 없어요.", "error")
        return redirect(detail_url)

    db.child("wanted").child(wanted_id).update({"picked_offer_id": offer_id, "state": "done"})
    flash("제안을 골랐어요.")
    return redirect(detail_url)


def validate_offer_form(form, picture, post, seller):
    """제안 폼을 브리프 순서(3~7)대로 검증한다. (저장할 필드 dict, 첫 오류 문구 또는 None)을 반환한다."""
    if post.get("writer") == seller:
        return None, "내 글에는 제안할 수 없어요."
    if post.get("state") != "open":
        return None, "이미 구한 글이에요."

    price = to_int(re.sub(r"\s", "", form.get("price", "")))
    if price is None or price <= 0:
        return None, "제안 금액을 1원 이상으로 입력해 주세요."
    budget = post.get("budget", 0)
    if price > budget:
        return None, f"예산 {budget:,}원 이하로 제안할 수 있어요."

    place = form.get("place", "").strip()
    if place and place not in (post.get("places") or {}):
        return None, "거래 장소를 다시 골라 주세요."

    if picture and picture.filename:
        picture_error = validate_picture(picture)
        if picture_error is not None:
            return None, picture_error

    return {"price": price, "description": form.get("description", "").strip(), "place": place}, None


def is_valid_key(key):
    """child()에 넣어도 되는 Firebase 키인지. 빈 값이면 상위 경로 전체를 읽게 되므로 막는다."""
    return isinstance(key, str) and bool(key) and not KEY_FORBIDDEN.search(key)


def get_wanted(wanted_id):
    """/wanted/{id} 글 하나. db가 없거나 id 형식이 틀리거나 글이 없으면 None"""
    if db is None or not is_valid_key(wanted_id):
        return None
    return db.child("wanted").child(wanted_id).get().val()


def load_offers(wanted_id):
    """/offers/{wanted_id}의 제안 목록. 각 제안에 id를 넣는다. db가 없으면 빈 목록"""
    if db is None or not is_valid_key(wanted_id):
        return []
    stored = db.child("offers").child(wanted_id).get().val() or {}
    return [{**offer, "id": offer_id} for offer_id, offer in stored.items()]


def get_offer(wanted_id, offer_id):
    """/offers/{wanted_id}/{offer_id} 제안 하나. 없으면 None"""
    if db is None or not is_valid_key(wanted_id) or not is_valid_key(offer_id):
        return None
    return db.child("offers").child(wanted_id).child(offer_id).get().val()


def save_offer(wanted_id, offer):
    """/offers/{wanted_id}/{push id}에 저장하고 새 id를 반환한다."""
    return db.child("offers").child(wanted_id).push(offer)["name"]
