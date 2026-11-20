"""상품 라우트: product_list, product_new, product_reserve, product_detail"""

import math

from flask import abort, flash, redirect, render_template, request, url_for

from core import app, to_int
from dummy import PREVIEW_PRODUCTS, find_product

PAGE_SIZE = 8
RESERVED_NAMES = {"new", "reserve", "done"}


@app.route("/")
def product_list():
    """상품 목록. 쿼리: q, sort, sale_status, kind, price_min, price_max, page"""
    args = request.args
    q = args.get("q", "").strip().lower()
    sale_status = args.get("sale_status", "all")
    kind = args.get("kind", "all")
    pmin, pmax = to_int(args.get("price_min")), to_int(args.get("price_max"))

    rows = [p for p in PREVIEW_PRODUCTS if p["sale_status"] != "done"]
    if q:
        rows = [p for p in rows if q in p["name"].lower()]
    if sale_status in ("sale", "hold"):
        rows = [p for p in rows if p["sale_status"] == sale_status]
    if kind in ("fixed", "bid"):
        rows = [p for p in rows if p["kind"] == kind]
    if pmin is not None:
        rows = [p for p in rows if to_int(p["price"], 0) >= pmin]
    if pmax is not None:
        rows = [p for p in rows if to_int(p["price"], 0) <= pmax]

    sort = args.get("sort", "new")
    if sort == "like":
        rows.sort(key=lambda p: p["likes"], reverse=True)
    elif sort in ("low", "high"):
        rows.sort(key=lambda p: to_int(p["price"], 0), reverse=(sort == "high"))

    total_pages = max(1, math.ceil(len(rows) / PAGE_SIZE))
    page = min(max(1, to_int(args.get("page"), 1)), total_pages)
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
    if to_int(form.get("price")) is None:
        errors["price"] = "가격을 숫자로 입력해 주세요."
    if form.get("status") not in ("최상", "상", "중", "하"):
        errors["status"] = "상품 상태를 골라 주세요."
    if form.get("name", "").strip().lower() in RESERVED_NAMES:
        errors["name"] = "이 이름으로는 등록할 수 없어요. 이름을 조금 바꿔 주세요."
    elif find_product(form.get("name", "").strip()):
        errors["name"] = "같은 이름의 상품이 이미 있어요. 이름을 조금 바꿔 주세요."
    if errors:
        return render_template("product/new.html", form=form, errors=errors), 400

    product = {k: form.get(k, "").strip() for k in ("seller", "name", "address", "status", "description")}
    product.update(price=to_int(form["price"]), likes=0, sale_status="sale", kind="fixed")
    PREVIEW_PRODUCTS.insert(0, product)
    flash("상품을 등록했어요.")
    return redirect(url_for("product_detail", name=product["name"]))


@app.route("/product/reserve", methods=["POST"])
def product_reserve():
    """약속 신청. 폼: name, place, slot → 상세로 redirect"""
    product = find_product(request.form.get("name", ""))
    if product is None:
        abort(404)
    places = product.get("places") or [{"building": product.get("address", ""), "detail": ""}]
    slots = product.get("slots") or []
    place, slot = to_int(request.form.get("place")), to_int(request.form.get("slot"))
    if place is None or slot is None or not (0 <= place < len(places)) or not (0 <= slot < len(slots)):
        flash("장소와 시간을 하나씩 골라 주세요.", "error")
    else:
        where = " ".join(v for v in (places[place]["building"], places[place].get("detail")) if v)
        flash(f"{where}, {slots[slot]}에 약속을 신청했어요.")
    return redirect(url_for("product_detail", name=product["name"]))


@app.route("/product/<path:name>")
def product_detail(name):
    """상품 상세. 없으면 404"""
    product = find_product(name)
    if product is None:
        abort(404)
    return render_template("product/detail.html", product=product, liked=False)
