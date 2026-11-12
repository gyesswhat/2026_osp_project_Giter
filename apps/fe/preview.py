"""FE 미리보기 서버 (개발용)

BE 연동 전에 base.html과 공통 컴포넌트, 각자 만든 화면을 확인하기 위한 서버다.
헤더의 url_for가 깨지지 않도록 라우트 함수 이름 규칙(도메인_동작)대로 빈 라우트를 등록해 둔다.
화면을 만들면 아래 SCREENS에 (경로, 함수 이름, 템플릿)을 추가하면 된다.

실행: (apps/fe 에서) python preview.py → http://127.0.0.1:5002/dev/components
"""

import math

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
    ("/auction/detail", "auction_detail", "auction/detail.html"),
    ("/auction/end", "auction_end", "auction/end.html"),
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

# 상품 화면 미리보기용 더미 (시안 예시 데이터 기준). 목록 순서 = 최신순
# kind: fixed(가격 정해진 물건) | bid(가격 제안 받는 중). bid의 price는 지금 최고 제안가
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
     "likes": 31, "sale_status": "sale", "kind": "bid", "date": "2026.10.06"},
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
     "likes": 20, "sale_status": "sale", "kind": "bid", "date": "2026.10.01"},
    {"name": "이케아 스탠드 조명", "seller": "hanwoori_210", "price": 0, "address": "한우리집", "status": "상",
     "likes": 2, "sale_status": "sale", "kind": "bid", "date": "2026.09.30"},
    {"name": "닌텐도 스위치 라이트", "seller": "ewhain_sw", "price": 165000, "address": "ECC", "status": "상",
     "likes": 14, "sale_status": "sale", "kind": "bid", "date": "2026.09.29"},
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


def product_detail(name):
    """상품 상세 미리보기. /product/<상품명> 으로 찾고, 없으면 404"""
    product = _find_product(name)
    if product is None:
        abort(404)
    return render_template("product/detail.html", product=product, liked=False)


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
    if _int(form.get("price")) is None:
        errors["price"] = "가격을 숫자로 입력해 주세요."
    if form.get("status") not in ("최상", "상", "중", "하"):
        errors["status"] = "상품 상태를 골라 주세요."
    if form.get("name", "").strip().lower() in RESERVED_NAMES:
        errors["name"] = "이 이름으로는 등록할 수 없어요. 이름을 조금 바꿔 주세요."  # /product/new 같은 고정 경로와 겹친다
    elif _find_product(form.get("name", "").strip()):
        errors["name"] = "같은 이름의 상품이 이미 있어요. 이름을 조금 바꿔 주세요."  # Firebase에서 상품명이 키라서
    if errors:
        return render_template("product/new.html", form=form, errors=errors), 400

    product = {k: form.get(k, "").strip() for k in ("seller", "name", "address", "status", "description")}
    product.update(price=_int(form["price"]), likes=0, sale_status="sale", kind="fixed")
    PREVIEW_PRODUCTS.insert(0, product)
    flash("상품을 등록했어요.")
    return redirect(url_for("product_detail", name=product["name"]))


product_new.methods = ["GET", "POST"]

# /product/<path:name> 보다 먼저 잡히는 고정 경로. 이 이름의 상품은 상세로 갈 수 없어서 등록을 막는다
RESERVED_NAMES = {"new", "reserve"}


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


# 더미 데이터나 POST 처리가 필요한 화면은 make_view 대신 이 뷰를 쓴다
CUSTOM_VIEWS = {
    "product_list": product_list,
    "product_detail": product_detail,
    "product_new": product_new,
    "auth_login": auth_login,
    "auth_signup": auth_signup,
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
