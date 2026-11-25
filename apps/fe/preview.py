"""FE 미리보기 서버 (개발용)

BE 연동 전에 base.html과 공통 컴포넌트, 각자 만든 화면을 확인하기 위한 서버다.
헤더의 url_for가 깨지지 않도록 라우트 함수 이름 규칙(도메인_동작)대로 빈 라우트를 등록해 둔다.
화면을 만들면 아래 SCREENS에 (경로, 함수 이름, 템플릿)을 추가하면 된다.

실행: (apps/fe 에서) python preview.py → http://127.0.0.1:5002/dev/components
"""

import math
from datetime import datetime, timedelta

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from jinja2 import TemplateNotFound

app = Flask(__name__)
app.config["SECRET_KEY"] = "fe-preview"

# (경로, 라우트 함수 이름, 템플릿) — 템플릿이 아직 없으면 준비 중 안내를 띄운다
# 경로를 바꾸면 ROUTES.md(라우트 경로표)도 같이 고친다
SCREENS = [
    ("/", "product_list", "product/list.html"),
    ("/product/<path:name>", "product_detail", "product/detail.html"),
    ("/product/new", "product_new", "product/new.html"),
    ("/review", "review_list", "review/list.html"),
    ("/review/<path:name>", "review_detail", "review/detail.html"),
    ("/review/new", "review_new", "review/new.html"),
    ("/review/done", "review_done", "review/done.html"),
    ("/auction/detail/<path:name>", "auction_detail", "auction/detail.html"),
    ("/auction/end/<path:name>", "auction_end", "auction/end.html"),
    ("/chat", "chat_room", "chat/room.html"),
    ("/wanted", "wanted_list", "wanted/list.html"),
    ("/wanted/detail", "wanted_detail", "wanted/detail.html"),
    ("/wanted/new", "wanted_new", "wanted/new.html"),
    ("/my", "my_index", "my/index.html"),
    ("/my/manage", "my_manage", "my/manage.html"),
    ("/login", "auth_login", "auth/login.html"),
    ("/signup", "auth_signup", "auth/signup.html"),
]

SAMPLE_PRODUCTS = [
    {"name": "컴퓨터구조 및 설계 5판", "price": "18000", "address": "ECC 앞", "likes": 12, "sale_status": "sale"},
    {"name": "이화 과잠 M 사이즈", "price": 25000, "address": "학생문화관", "likes": 18, "sale_status": "hold"},
    {"name": "전기 주전자 1L", "price": 8000, "address": "이하우스", "likes": 7, "sale_status": "done"},
]


def _ends_in(**delta):
    """지금부터 delta 뒤의 마감 시각(ISO 문자열). 서버를 켤 때마다 남은 시간이 시안과 같게 보이도록 상대 시각으로 둔다."""
    return (datetime.now().astimezone() + timedelta(**delta)).isoformat(timespec="seconds")


# 상품 화면 미리보기용 더미 (시안 예시 데이터 기준). 목록 순서 = 최신순
# kind: fixed(가격 정해진 물건) | bid(가격 제안 받는 중). bid의 price는 지금 최고 제안가
# bid 상품: bid_count 제안 수, end_at 마감 시각(ISO), closed 마감 여부 (schema.dbml auctions)
# status: 상품 상태(최상/상/중/하). sale_status: 판매 상태(sale/hold/done)
PREVIEW_PRODUCTS = [
    {"name": "컴퓨터구조 및 설계 5판", "seller": "baekkot21", "price": "18000", "address": "ECC 앞", "status": "상",
     "likes": 12, "sale_status": "sale", "kind": "fixed", "date": "2026.10.06",
     "description": "지난 학기 컴퓨터구조 수업에서 쓴 교재입니다. 1장부터 4장까지 연필 필기가 조금 있고, "
                    "형광펜은 쓰지 않았어요. 표지 모서리가 살짝 닳은 것 말고는 깨끗합니다.",
     "places": [{"building": "ECC", "detail": "8번 출구 앞"}, {"building": "중앙도서관", "detail": "1층 로비"},
                {"building": "기타", "detail": "이대역 2번 출구"}],
     "slots": ["10.12 (월) 13:00", "10.12 (월) 15:00", "10.13 (화) 12:00", "10.13 (화) 16:30", "10.14 (수) 11:00"]},
    {"name": "아이패드 에어 5세대 64GB", "seller": "apple_ewha", "price": 435000, "address": "포스코관", "status": "최상",
     "likes": 31, "sale_status": "sale", "kind": "bid", "date": "2026.10.06",
     "bid_count": 7, "end_at": _ends_in(days=2, hours=13, minutes=22), "closed": False},
    {"name": "이화 과잠 M 사이즈", "seller": "gwajam_22", "price": 25000, "address": "학생문화관", "status": "상",
     "likes": 18, "sale_status": "hold", "kind": "fixed", "date": "2026.10.05"},
    {"name": "로지텍 K380 무선 키보드", "seller": "ewhain_sw", "price": 22000, "address": "아산공학관", "status": "중",
     "likes": 9, "sale_status": "sale", "kind": "fixed", "date": "2026.10.05",
     "description": "1년 정도 쓴 무선 키보드입니다. 키감은 그대로이고 뒷면에 스티커 자국이 조금 있어요. 건전지는 새것으로 넣어 드려요."},
    {"name": "기숙사용 미니 냉장고", "seller": "hanwoori_210", "price": 40000, "address": "한우리집", "status": "상",
     "likes": 24, "sale_status": "sale", "kind": "fixed", "date": "2026.10.04"},
    {"name": "토익 기출 문제집 세트", "seller": "baekkot21", "price": 9000, "address": "중앙도서관", "status": "중",
     "likes": 5, "sale_status": "sale", "kind": "fixed", "date": "2026.10.03"},
    {"name": "전기 주전자 1L", "seller": "ehouse_tea", "price": 8000, "address": "이하우스", "status": "하",
     "likes": 7, "sale_status": "done", "kind": "fixed", "date": "2026.10.02"},
    {"name": "접이식 독서대", "seller": "ewhain_sw", "price": 6000, "address": "중앙도서관", "status": "상",
     "likes": 3, "sale_status": "sale", "kind": "fixed", "date": "2026.10.02",
     "description": "각도 조절되는 접이식 독서대입니다. 전공책 두 권까지 올라가요."},
    {"name": "필름 카메라 올림푸스 뮤2", "seller": "film_lover", "price": 120000, "address": "조형예술관", "status": "중",
     "likes": 20, "sale_status": "sale", "kind": "bid", "date": "2026.10.01",
     "bid_count": 12, "end_at": _ends_in(hours=26), "closed": False},
    {"name": "이케아 스탠드 조명", "seller": "hanwoori_210", "price": 0, "address": "한우리집", "status": "상",
     "likes": 2, "sale_status": "sale", "kind": "bid", "date": "2026.09.30",
     "bid_count": 0, "end_at": _ends_in(hours=5), "closed": False},
    {"name": "닌텐도 스위치 라이트", "seller": "ewhain_sw", "price": 165000, "address": "ECC", "status": "상",
     "likes": 14, "sale_status": "sale", "kind": "bid", "date": "2026.09.29",
     "bid_count": 6, "end_at": _ends_in(hours=-1), "closed": True},
    {"name": "공학수학 솔루션", "seller": "math_ewha", "price": 12000, "address": "아산공학관", "status": "중",
     "likes": 4, "sale_status": "sale", "kind": "fixed", "date": "2026.09.28"},
    {"name": "무선 마우스 M330", "seller": "cse24", "price": 15000, "address": "ECC", "status": "상",
     "likes": 6, "sale_status": "hold", "kind": "fixed", "date": "2026.09.27"},
]
PAGE_SIZE = 8


def _int(value, default=None):
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def product_list():
    """상품 목록 미리보기. BE가 같은 쿼리(q, sort, sale_status, kind, price_min, price_max, page)를 처리하는 예시"""
    args = request.args
    q = args.get("q", "").strip().lower()
    sale_status = args.get("sale_status", "all")
    kind = args.get("kind", "all")
    pmin, pmax = _int(args.get("price_min")), _int(args.get("price_max"))

    rows = [p for p in PREVIEW_PRODUCTS if p["sale_status"] != "done"]  # 거래 완료는 상품 탭에서 뺀다
    if q:
        rows = [p for p in rows if q in p["name"].lower()]
    if sale_status in ("sale", "hold"):
        rows = [p for p in rows if p["sale_status"] == sale_status]
    if kind in ("fixed", "bid"):
        rows = [p for p in rows if p["kind"] == kind]
    if pmin is not None:
        rows = [p for p in rows if _int(p["price"], 0) >= pmin]
    if pmax is not None:
        rows = [p for p in rows if _int(p["price"], 0) <= pmax]

    sort = args.get("sort", "new")
    if sort == "like":
        rows.sort(key=lambda p: p["likes"], reverse=True)
    elif sort in ("low", "high"):
        rows.sort(key=lambda p: _int(p["price"], 0), reverse=(sort == "high"))

    total_pages = max(1, math.ceil(len(rows) / PAGE_SIZE))
    page = min(max(1, _int(args.get("page"), 1)), total_pages)
    return render_template(
        "product/list.html",
        products=rows[(page - 1) * PAGE_SIZE:page * PAGE_SIZE],
        total=len(rows),
        page=page,
        total_pages=total_pages,
    )


def _find_product(name):
    return next((p for p in PREVIEW_PRODUCTS if p["name"] == name), None)

def review_detail(name):
    """리뷰 상세 화면 미리보기용 더미 데이터"""
    review = {
        "product_name": name,
        "reviewer": "ewhain_sw",
        "seller": "baekkot21",
        "rating": 5,
        "title": "책 상태가 설명 그대로였어요",
        "content": "필기가 조금 있다고 하셨는데 정말 연필로 몇 군데만 있어서 지우고 바로 쓸 수 있었어요.",
        "photo": "",
        "created_at": "2026-10-05",
        "date": "2026.10.05",
    }

    product = _find_product(name)

    return render_template(
        "review/detail.html",
        review=review,
        product=product,
    )


def product_detail(name):
    """상품 상세 미리보기. /product/<상품명> 으로 찾고, 없으면 404"""
    product = _find_product(name)
    if product is None:
        abort(404)
    return render_template("product/detail.html", product=product, liked=name in session.get("liked", []))


def product_like():
    """찜 토글 미리보기. BE product_like와 같은 흐름이고, 찜 목록은 세션에만 둔다 (DB에 저장하지 않음)"""
    if not session.get("id"):
        flash("찜하려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))
    name = request.form.get("name", "")
    product = _find_product(name)
    if product is None:
        abort(404)
    if product.get("seller") == session["id"]:
        flash("내가 올린 상품은 찜할 수 없어요.", "error")
        return redirect(url_for("product_detail", name=name))
    liked = session.get("liked", [])
    if name in liked:
        liked.remove(name)
        product["likes"] = max(0, product.get("likes", 0) - 1)
        flash("찜을 취소했어요.")
    else:
        liked.append(name)
        product["likes"] = product.get("likes", 0) + 1
        flash("찜했어요.")
    session["liked"] = liked
    return redirect(url_for("product_detail", name=name))


def auction_detail(name):
    """경매 상세 미리보기: 상품명으로 경매 상품을 조회"""
    product = _find_product(name)

    if product is None or product.get("kind") != "bid":
        abort(404)

    highest_bid = int(product["price"])
    auction = {
        "top_price": highest_bid,
        "bid_count": 0,
        "end_at": product.get("end_at"),
        "closed": product.get("closed", False),
    }

    if highest_bid==0:
        bids=[]
    else:
        bids = [
            {"bidder": "ab***12", "date": "11.20 14:30", "price": highest_bid},
            {"bidder": "ki***07", "date": "11.20 12:15", "price": highest_bid - 5000},
            {"bidder": "ew***25", "date": "11.19 18:42", "price": highest_bid - 15000},
        ]   
    auction["bid_count"] = len(bids)

    return render_template(
        "auction/detail.html",
        product=product,
        auction=auction,
        bids=bids,
        my_bid=None,
       min_price=highest_bid+5000,
    )


def product_reserve():
    """약속 신청 미리보기. 폼 값(name, place, slot)을 확인하고 상세로 돌아간다 (저장하지 않음)"""
    product = _find_product(request.form.get("name", ""))
    if product is None:
        abort(404)
    places = product.get("places") or [{"building": product.get("address", ""), "detail": ""}]
    slots = product.get("slots") or []
    place, slot = _int(request.form.get("place")), _int(request.form.get("slot"))
    if place is None or slot is None or not (0 <= place < len(places)) or not (0 <= slot < len(slots)):
        flash("장소와 시간을 하나씩 골라 주세요.", "error")
    else:
        where = " ".join(v for v in (places[place]["building"], places[place].get("detail")) if v)
        flash(f"{where}, {slots[slot]}에 약속을 신청했어요. 판매자가 수락하면 마이에 표시돼요.")
    return redirect(url_for("product_detail", name=product["name"]))


def product_new():
    """상품 등록 미리보기. POST면 서버 쪽 확인을 흉내 내고, 통과하면 더미 목록 맨 앞에 넣는다 (사진 파일은 저장하지 않음)"""
    if request.method == "GET":
        return render_template("product/new.html")

    form = request.form
    errors = {}
    if not request.files.get("picture") or not request.files["picture"].filename:
        errors["picture"] = "대표 사진을 올려 주세요."
    for field, text in [("seller", "판매자 ID를 입력해 주세요."), ("name", "상품명을 입력해 주세요."),
                        ("address", "거래할 주소를 입력해 주세요."), ("description", "상세 설명을 입력해 주세요.")]:
        if not form.get(field, "").strip():
            errors[field] = text
    kind = form.get("kind", "fixed")
    if kind not in ("fixed", "bid"):
        errors["kind"] = "가격 정하는 방식을 골라 주세요."
    elif kind == "fixed" and _int(form.get("price")) is None:
        errors["price"] = "가격을 숫자로 입력해 주세요."
    elif kind == "bid" and _int(form.get("duration")) not in (1, 3, 5, 7):
        errors["duration"] = "제안 받는 기간을 골라 주세요."
    if form.get("status") not in ("최상", "상", "중", "하"):
        errors["status"] = "상품 상태를 골라 주세요."
    if form.get("name", "").strip().lower() in RESERVED_NAMES:
        errors["name"] = "이 이름으로는 등록할 수 없어요. 이름을 조금 바꿔 주세요."  # /product/new 같은 고정 경로와 겹친다
    elif _find_product(form.get("name", "").strip()):
        errors["name"] = "같은 이름의 상품이 이미 있어요. 이름을 조금 바꿔 주세요."  # Firebase에서 상품명이 키라서
    if errors:
        return render_template("product/new.html", form=form, errors=errors), 400

    product = {k: form.get(k, "").strip() for k in ("seller", "name", "address", "status", "description")}
    # bid의 price는 지금 최고 제안가라서 제안이 없는 새 상품은 0으로 둔다
    product.update(price=_int(form.get("price"), 0) if kind == "fixed" else 0,
                   likes=0, sale_status="sale", kind=kind)
    PREVIEW_PRODUCTS.insert(0, product)
    flash(f"상품을 등록했어요. {form['duration']}일 동안 제안을 받아요." if kind == "bid" else "상품을 등록했어요.")
    return redirect(url_for("product_detail", name=product["name"]))


product_new.methods = ["GET", "POST"]

# /product/<path:name>, /review/<path:name> 보다 먼저 잡히는 고정 경로.
# 이 이름의 상품은 상세(상품·리뷰)로 갈 수 없어서 등록을 막는다
RESERVED_NAMES = {"new", "reserve", "done", "like"}


def review_new():
    """리뷰 쓰기 미리보기. ?name=상품명 이면 상품 카드와 상품명 칸을 채운다.
    POST면 서버 쪽 확인을 흉내 내고, 통과하면 완료 화면으로 보낸다 (리뷰·사진은 저장하지 않음)"""
    name = request.values.get("product_name") or request.args.get("name", "")
    product = _find_product(name)
    if request.method == "GET":
        return render_template("review/new.html", product=product)

    form = request.form
    errors = {}
    reviewer = session.get("id") or form.get("reviewer", "").strip()  # 로그인 상태면 세션 값을 믿는다
    if not reviewer:
        errors["reviewer"] = "작성자 ID를 입력해 주세요."
    for field, text in [("product_name", "상품명을 입력해 주세요."), ("title", "제목을 입력해 주세요."),
                        ("content", "내용을 입력해 주세요.")]:
        if not form.get(field, "").strip():
            errors[field] = text
    rating = _int(form.get("rating"))
    if rating not in range(1, 6):
        errors["rating"] = "별점을 1~5점 중에서 골라 주세요."
    photo = request.files.get("photo")
    if photo and photo.filename and not (photo.mimetype or "").startswith("image/"):
        errors["photo"] = "사진 파일만 올릴 수 있어요."
    if errors:
        return render_template("review/new.html", product=product, form=form, errors=errors), 400

    session["last_review"] = {
        "reviewer": reviewer,
        "product_name": form["product_name"].strip(),
        "rating": rating,
        "title": form["title"].strip(),
        "content": form["content"].strip(),
        "photo": photo.filename if photo and photo.filename else "",
    }
    return redirect(url_for("review_done"))


review_new.methods = ["GET", "POST"]


def review_done():
    """리뷰 등록 완료 미리보기. 방금 제출한 값을 세션에서 꺼내 보여 준다"""
    return render_template("review/done.html", review=session.get("last_review"))

def review_list():
    """리뷰 목록 미리보기용 더미 데이터"""
    reviews = [
        {
            "product_name": "컴퓨터구조 및 설계 5판",
            "reviewer": "ewhain_sw",
            "seller": "baekkot21",
            "rating": 5,
            "title": "책 상태가 설명 그대로였어요",
            "date": "2026.10.05",
            "photo": "",
        },
        {
            "product_name": "로지텍 K380 무선 키보드",
            "reviewer": "pear_blossom",
            "seller": "ewhain_sw",
            "rating": 5,
            "title": "약속 시간을 잘 맞춰 주셨어요",
            "date": "2026.10.04",
            "photo": "",
        },
        {
            "product_name": "기숙사용 미니 냉장고",
            "reviewer": "hanwoori302",
            "seller": "hanwoori_210",
            "rating": 4,
            "title": "냉장고 소음이 거의 없어요",
            "date": "2026.10.02",
            "photo": "",
        },
    ]

    seller = request.args.get("seller", "")
    if seller:
        reviews = [r for r in reviews if r["seller"] == seller]

    total = len(reviews)
    page = max(1, int(request.args.get("page", 1)))
    total_pages = max(1, (total + 9) // 10)
    page = min(page, total_pages)

    seller_info = None
    if seller:
        avg = round(sum(r["rating"] for r in reviews) / total, 1) if total else 0
        seller_info = {
            "id": seller,
            "avg_rating": avg,
            "count": total,
        }

    return render_template(
        "review/list.html",
        reviews=reviews[(page - 1) * 10:page * 10],
        total=total,
        page=page,
        total_pages=total_pages,
        seller=seller,
        seller_info=seller_info,
    )


def auth_login():
    """로그인 미리보기. 비밀번호는 확인하지 않고, ID만 있으면 로그인 처리 후 상품 목록으로 간다"""
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        if user_id and request.form.get("password"):
            session["id"] = user_id
            return redirect(url_for("product_list"))
        flash("아이디와 비밀번호를 입력해 주세요.", "error")
    return render_template("auth/login.html")


def auth_signup():
    """회원가입 미리보기. 저장하지 않고 로그인 화면으로 보낸다"""
    if request.method == "POST":
        flash("가입했어요. 로그인해 주세요.")
        return redirect(url_for("auth_login"))
    return render_template("auth/signup.html")


auth_login.methods = ["GET", "POST"]
auth_signup.methods = ["GET", "POST"]

def auction_end(name):
    """상품별 경매 마감 화면 미리보기 (실제 DB 저장 없음)"""
    product = _find_product(name)

    if product is None or product.get("kind") != "bid":
        abort(404)

    preview_bids = {
        "닌텐도 스위치 라이트": [165000, 160000, 152000, 140000, 120000],
        "아이패드 에어 5세대 64GB": [435000, 430000, 420000, 410000, 400000],
        "필름 카메라 올림푸스 뮤2": [120000, 115000, 110000, 100000, 90000],
        "이케아 스탠드 조명": [],
    }

    amounts = preview_bids.get(name, []) if int(product["price"]) > 0 else []

    users = ["po***", "ew***", "cs***", "ha***", "ar***"]
    dates = ["11.02 20:51", "11.02 18:05", "11.01 23:11",
             "10.31 22:47", "10.30 19:31"]

    bids = [
        {"bidder": user, "price": amount, "date": date}
        for user, amount, date in zip(users, amounts, dates)
    ]
    if bids and session.get("id") == product["seller"]:
        bids[0]["bidder"] = "posco_23"

    decisions = session.get("auction_decisions", {})

    auction = {
        "top_price": max(amounts, default=0),
        "bid_count": len(bids),
        "decision": decisions.get(name, "pending"),
        "closed": True,
        "end_at": product.get("end_at"),
    }

    deadline = (
        datetime.fromisoformat(product["end_at"])
        + timedelta(hours=48)
    ).isoformat(timespec="seconds")

    return render_template(
        "auction/end.html",
        product=product,
        auction=auction,
        bids=bids,
        deadline=deadline,
    )

# 더미 데이터나 POST 처리가 필요한 화면은 make_view 대신 이 뷰를 쓴다
CUSTOM_VIEWS = {
    "product_list": product_list,
    "product_detail": product_detail,
    "auction_detail": auction_detail,
    "product_new": product_new,
    "review_new": review_new,
    "review_done": review_done,
    "review_list": review_list,
    "review_detail": review_detail,
    "auth_login": auth_login,
    "auth_signup": auth_signup,
    "auction_end": auction_end,
}


def make_view(template):
    def view(**kwargs):
        try:
            return render_template(template, **kwargs)
        except TemplateNotFound as e:
            # 찾지 못한 게 이 화면 템플릿일 때만 안내 페이지. include 경로 오류 등은 그대로 띄운다
            if e.name != template:
                raise
            return render_template("dev/todo.html", template=template)

    return view


for path, endpoint, template in SCREENS:
    app.add_url_rule(path, endpoint, CUSTOM_VIEWS.get(endpoint) or make_view(template))


app.add_url_rule("/product/reserve", "product_reserve", product_reserve, methods=["POST"])
app.add_url_rule("/product/like", "product_like", product_like, methods=["POST"])

@app.route("/auction/decide", methods=["POST"])
def auction_decide():
    name = request.form.get("name", "")
    decision = request.form.get("decision", "")
    product = _find_product(name)

    if not session.get("id"):
        return redirect(url_for("auth_login"))

    if product is None or product.get("kind") != "bid":
        abort(404)

    if session.get("id") != product["seller"]:
        flash("판매자만 거래를 결정할 수 있어요.", "error")
        return redirect(url_for("auction_end", name=name))

    decisions = session.get("auction_decisions", {})

    if decisions.get(name, "pending") != "pending":
        flash("이미 결정된 경매예요.", "error")
        return redirect(url_for("auction_end", name=name))

    if decision not in ("accepted", "rejected"):
        flash("올바른 거래 상태를 선택해 주세요.", "error")
        return redirect(url_for("auction_end", name=name))

    if decision == "accepted" and int(product["price"]) == 0:
        flash("받은 제안이 없어요.", "error")
        return redirect(url_for("auction_end", name=name))

    decisions[name] = decision
    session["auction_decisions"] = decisions

    if decision == "accepted":
        product["sale_status"] = "hold"
        flash("거래가 확정됐어요.")
    else:
        flash("이번 제안으로는 거래하지 않아요.")

    return redirect(url_for("auction_end", name=name))

@app.route("/auction/reopen", methods=["POST"])
def auction_reopen():
    name = request.form.get("name", "")
    mode = request.form.get("mode", "")
    product = _find_product(name)

    if not session.get("id"):
        return redirect(url_for("auth_login"))

    if product is None or product.get("kind") != "bid":
        abort(404)

    decisions = session.get("auction_decisions", {})

    if session.get("id") != product["seller"] or decisions.get(name) != "rejected":
        flash("다시 올릴 수 없는 경매예요.", "error")
        return redirect(url_for("auction_end", name=name))

    if mode == "bid":
        duration_days = _int(request.form.get("duration_days"))

        if duration_days not in (1, 3, 5, 7):
            flash("제안 받는 기간을 골라 주세요.", "error")
            return redirect(url_for("auction_end", name=name))

        product.update(
            price=0,
            bid_count=0,
            end_at=_ends_in(days=duration_days),
            closed=False,
            sale_status="sale",
        )

        decisions[name] = "pending"
        session["auction_decisions"] = decisions

        flash("다시 제안을 받기 시작했어요.")
        return redirect(url_for("auction_detail", name=name))

    elif mode == "fixed":
        price = request.form.get("price", "")

        if not price.isdecimal():
            flash("가격을 숫자로 입력해 주세요.", "error")
            return redirect(url_for("auction_end", name=name))

        product.update(
            kind="fixed",
            price=int(price),
            sale_status="sale",
        )

        decisions.pop(name, None)
        session["auction_decisions"] = decisions

        flash("가격을 정해서 다시 올렸어요.")
        return redirect(url_for("product_detail", name=name))

    flash("올바른 판매 방식을 선택해 주세요.", "error")
    return redirect(url_for("auction_end", name=name))

@app.route("/auction/bid", methods=["POST"])
def auction_bid():
    name = request.form.get("name", "")
    flash("미리보기에서는 실제 제안이 저장되지 않습니다.")
    return redirect(url_for("auction_detail", name=name))

@app.route("/logout")
def auth_logout():
    session.pop("id", None)
    return redirect(url_for("product_list"))


@app.route("/dev/components")
def dev_components():
    return render_template("dev/components.html", sample_products=SAMPLE_PRODUCTS)


@app.route("/dev/toggle-login")
def dev_toggle_login():
    if session.get("id"):
        session.pop("id")
    else:
        session["id"] = "ewhain_sw"
    return redirect(url_for("dev_components"))


if __name__ == "__main__":
    app.run(debug=True, port=5002)
