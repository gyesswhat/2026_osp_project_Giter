"""BE 서버 (BoughtIT)

FE 템플릿을 그대로 사용한다. template_folder와 static_folder를 apps/fe로 지정한다.
실행: (apps/be 에서) python app.py  → http://127.0.0.1:5001/
"""

import json
import math
import os

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

# 1. 경로 설정
_base = os.path.dirname(__file__)
_fe = os.path.join(_base, "../fe")

app = Flask(
    __name__,
    template_folder=os.path.join(_fe, "templates"),
    static_folder=os.path.join(_fe, "static"),
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "boughtit-dev")

# 2. Firebase 초기화 (설정 파일이 없으면 db는 None으로 유지한다)
db = None
_config_path = os.path.join(_base, "../../authentication/firebase_auth.json")
try:
    import pyrebase  # type: ignore

    with open(_config_path) as _f:
        _config = json.load(_f)
    _firebase = pyrebase.initialize_app(_config)
    db = _firebase.database()
except Exception as e:
    # 연결에 실패하면 더미 데이터로 동작한다. 원인을 확인할 수 있도록 출력한다.
    print(f"Firebase 연결 실패, 더미 데이터로 실행한다: {e!r}")

# 3. 더미 데이터 (BE 연동 전 템플릿 확인용)
# kind: fixed(가격 고정) | bid(가격 제안). sale_status: sale/hold/done
PREVIEW_PRODUCTS = [
    {
        "name": "컴퓨터구조 및 설계 5판",
        "seller": "baekkot21",
        "price": "18000",
        "address": "ECC 앞",
        "status": "상",
        "likes": 12,
        "sale_status": "sale",
        "kind": "fixed",
        "date": "2026.10.06",
        "description": "지난 학기 컴퓨터구조 수업에서 쓴 교재입니다.",
        "places": [
            {"building": "ECC", "detail": "8번 출구 앞"},
            {"building": "중앙도서관", "detail": "1층 로비"},
        ],
        "slots": ["10.12 (월) 13:00", "10.12 (월) 15:00", "10.13 (화) 12:00"],
    },
    {
        "name": "아이패드 에어 5세대 64GB",
        "seller": "apple_ewha",
        "price": 435000,
        "address": "포스코관",
        "status": "최상",
        "likes": 31,
        "sale_status": "sale",
        "kind": "bid",
        "date": "2026.10.06",
    },
    {
        "name": "이화 과잠 M 사이즈",
        "seller": "gwajam_22",
        "price": 25000,
        "address": "학생문화관",
        "status": "상",
        "likes": 18,
        "sale_status": "hold",
        "kind": "fixed",
        "date": "2026.10.05",
    },
    {
        "name": "로지텍 K380 무선 키보드",
        "seller": "ewhain_sw",
        "price": 22000,
        "address": "아산공학관",
        "status": "중",
        "likes": 9,
        "sale_status": "sale",
        "kind": "fixed",
        "date": "2026.10.05",
        "description": "1년 정도 쓴 무선 키보드입니다.",
    },
    {
        "name": "기숙사용 미니 냉장고",
        "seller": "hanwoori_210",
        "price": 40000,
        "address": "한우리집",
        "status": "상",
        "likes": 24,
        "sale_status": "sale",
        "kind": "fixed",
        "date": "2026.10.04",
    },
    {
        "name": "전기 주전자 1L",
        "seller": "ehouse_tea",
        "price": 8000,
        "address": "이하우스",
        "status": "하",
        "likes": 7,
        "sale_status": "done",
        "kind": "fixed",
        "date": "2026.10.02",
    },
]

PAGE_SIZE = 8
RESERVED_NAMES = {"new", "reserve", "done"}


def _int(value, default=None):
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def _find_product(name):
    return next((p for p in PREVIEW_PRODUCTS if p["name"] == name), None)


# 4. 라우트 (ROUTES.md 기준, 화면/미리보기 상태인 항목만 등록)


@app.route("/")
def product_list():
    """상품 목록. 쿼리: q, sort, sale_status, kind, price_min, price_max, page"""
    args = request.args
    q = args.get("q", "").strip().lower()
    sale_status = args.get("sale_status", "all")
    kind = args.get("kind", "all")
    pmin, pmax = _int(args.get("price_min")), _int(args.get("price_max"))

    rows = [p for p in PREVIEW_PRODUCTS if p["sale_status"] != "done"]
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
        products=rows[(page - 1) * PAGE_SIZE : page * PAGE_SIZE],
        total=len(rows),
        page=page,
        total_pages=total_pages,
    )


@app.route("/product/new", methods=["GET", "POST"])
def product_new():
    """상품 등록. POST: seller, name, price, address, status, description, picture"""
    if request.method == "GET":
        return render_template("product/new.html")

    form = request.form
    errors = {}
    if not request.files.get("picture") or not request.files["picture"].filename:
        errors["picture"] = "대표 사진을 올려 주세요."
    for field, text in [
        ("seller", "판매자 ID를 입력해 주세요."),
        ("name", "상품명을 입력해 주세요."),
        ("address", "거래할 주소를 입력해 주세요."),
        ("description", "상세 설명을 입력해 주세요."),
    ]:
        if not form.get(field, "").strip():
            errors[field] = text
    if _int(form.get("price")) is None:
        errors["price"] = "가격을 숫자로 입력해 주세요."
    if form.get("status") not in ("최상", "상", "중", "하"):
        errors["status"] = "상품 상태를 골라 주세요."
    if form.get("name", "").strip().lower() in RESERVED_NAMES:
        errors["name"] = "이 이름으로는 등록할 수 없어요. 이름을 조금 바꿔 주세요."
    elif _find_product(form.get("name", "").strip()):
        errors["name"] = "같은 이름의 상품이 이미 있어요. 이름을 조금 바꿔 주세요."
    if errors:
        return render_template("product/new.html", form=form, errors=errors), 400

    product = {k: form.get(k, "").strip() for k in ("seller", "name", "address", "status", "description")}
    product.update(price=_int(form["price"]), likes=0, sale_status="sale", kind="fixed")
    PREVIEW_PRODUCTS.insert(0, product)
    flash("상품을 등록했어요.")
    return redirect(url_for("product_detail", name=product["name"]))


@app.route("/product/reserve", methods=["POST"])
def product_reserve():
    """약속 신청. 폼: name, place, slot → 상세로 redirect"""
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
        flash(f"{where}, {slots[slot]}에 약속을 신청했어요.")
    return redirect(url_for("product_detail", name=product["name"]))


@app.route("/product/<path:name>")
def product_detail(name):
    """상품 상세. 없으면 404"""
    product = _find_product(name)
    if product is None:
        abort(404)
    return render_template("product/detail.html", product=product, liked=False)


@app.route("/review")
def review_list():
    """리뷰 목록. 쿼리: seller, page"""
    seller = request.args.get("seller", "")
    return render_template("review/list.html", seller=seller, reviews=[], total=0, page=1, total_pages=1)


@app.route("/review/new", methods=["GET", "POST"])
def review_new():
    """리뷰 작성. GET: ?name=상품명. POST: product_name, reviewer, rating, title, photo, content"""
    name = request.values.get("product_name") or request.args.get("name", "")
    product = _find_product(name)
    if request.method == "GET":
        return render_template("review/new.html", product=product)

    form = request.form
    errors = {}
    reviewer = session.get("id") or form.get("reviewer", "").strip()
    if not reviewer:
        errors["reviewer"] = "작성자 ID를 입력해 주세요."
    for field, text in [
        ("product_name", "상품명을 입력해 주세요."),
        ("title", "제목을 입력해 주세요."),
        ("content", "내용을 입력해 주세요."),
    ]:
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


@app.route("/review/done")
def review_done():
    """리뷰 등록 완료. 세션에 저장한 last_review를 보여 준다."""
    return render_template("review/done.html", review=session.get("last_review"))


@app.route("/review/<path:name>")
def review_detail(name):
    """리뷰 상세. name은 리뷰를 쓴 상품명이다."""
    return render_template("review/detail.html", review=None, name=name)


@app.route("/login", methods=["GET", "POST"])
def auth_login():
    """로그인. POST: user_id, password → 성공 시 product_list로 redirect"""
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")
        if user_id and password:
            # TODO: DB에서 사용자 확인 후 session['id'] 저장
            session["id"] = user_id
            return redirect(url_for("product_list"))
        flash("아이디와 비밀번호를 입력해 주세요.", "error")
    return render_template("auth/login.html")


@app.route("/signup", methods=["GET", "POST"])
def auth_signup():
    """회원가입. POST: user_id, password, password_confirm, email, auth_code, phone(선택)"""
    if request.method == "POST":
        # TODO: 유효성 검사 및 DB 저장
        flash("가입했어요. 로그인해 주세요.")
        return redirect(url_for("auth_login"))
    return render_template("auth/signup.html")


@app.route("/logout")
def auth_logout():
    """로그아웃. session에서 id를 삭제하고 product_list로 redirect"""
    session.pop("id", None)
    return redirect(url_for("product_list"))


# 5. 팀 특화 라우트 스텁
# 헤더 탭과 product/detail.html이 url_for로 호출하는 라우트만 등록한다.
# 나머지 팀 특화 라우트는 담당자가 ROUTES.md의 이름과 URL로 추가한다.


@app.route("/wanted")
def wanted_list():
    abort(501)


@app.route("/chat")
def chat_room():
    abort(501)


@app.route("/my")
def my_index():
    abort(501)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
