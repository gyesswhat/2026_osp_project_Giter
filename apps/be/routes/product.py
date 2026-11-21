"""상품 라우트: product_list, product_new, product_reserve, product_detail

db가 None이면(Firebase 설정 파일 없음) dummy.PREVIEW_PRODUCTS를 상품 저장소로 사용한다.
"""

import math
import os
import uuid
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from core import app, db, to_int
from dummy import PREVIEW_PRODUCTS, find_product

PAGE_SIZE = 8
# /product/new, /product/reserve, /review/done 등 고정 경로와 겹치는 상품명 (schema.dbml products.name)
RESERVED_NAMES = {"new", "reserve", "done", "like"}
# Firebase 키에 쓸 수 없는 문자. "/"는 막지 않고 product_key()에서 바꾼다
FORBIDDEN_NAME_CHARS = ".$#[]"
# "/" 대신 Firebase 키에 저장하는 문자 (U+2215 DIVISION SLASH)
KEY_SLASH = "∕"
CONDITIONS = ("최상", "상", "중", "하")
PICTURE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PICTURE_MAX_BYTES = 5 * 1024 * 1024
UPLOAD_DIR = os.path.join(app.static_folder, "uploads")


@app.route("/")
def product_list():
    """상품 목록. 쿼리: q, sort, sale_status, kind, price_min, price_max, page"""
    products = filter_products(load_products(), request.args)
    sort_products(products, request.args.get("sort", "new"))

    total_pages = max(1, math.ceil(len(products) / PAGE_SIZE))
    page = min(max(1, to_int(request.args.get("page"), 1)), total_pages)
    return render_template(
        "product/list.html",
        products=products[(page - 1) * PAGE_SIZE : page * PAGE_SIZE],
        total=len(products),
        page=page,
        total_pages=total_pages,
    )


@app.route("/product/new", methods=["GET", "POST"])
def product_new():
    """상품 등록. POST: name, price, address, status, description, picture. 판매자는 session['id']이다."""
    seller = session.get("id")
    if seller is None:
        flash("상품을 등록하려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))
    if request.method == "GET":
        return render_template("product/new.html")

    form = request.form
    picture = request.files.get("picture")
    errors = validate_product_form(form, picture)
    if len(errors) > 0:
        return render_template("product/new.html", form=form, errors=errors), 400

    product = {field: form[field].strip() for field in ("name", "address", "status", "description")}
    product.update(
        seller=seller,
        kind="fixed",
        price=to_int(form["price"]),
        img_path=save_picture(picture),
        sale_status="sale",
        likes=0,
        created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    save_product(product)
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
    product = get_product(name)
    if product is None:
        abort(404)
    return render_template("product/detail.html", product=product, liked=is_liked(name))


# 1. 목록 필터와 정렬
def filter_products(products, args):
    """거래 완료 상품을 제외하고 쿼리 조건에 맞는 상품만 남긴다."""
    query = args.get("q", "").strip().lower()
    sale_status = args.get("sale_status", "all")
    kind = args.get("kind", "all")
    price_min = to_int(args.get("price_min"))
    price_max = to_int(args.get("price_max"))

    products = [p for p in products if p["sale_status"] != "done"]
    if query:
        products = [p for p in products if query in p["name"].lower()]
    if sale_status in ("sale", "hold"):
        products = [p for p in products if p["sale_status"] == sale_status]
    if kind in ("fixed", "bid"):
        products = [p for p in products if p["kind"] == kind]
    if price_min is not None:
        products = [p for p in products if to_int(p["price"], 0) >= price_min]
    if price_max is not None:
        products = [p for p in products if to_int(p["price"], 0) <= price_max]
    return products


def sort_products(products, sort):
    """sort: new(최신순, 기본값) | like | low | high"""
    if sort == "like":
        products.sort(key=lambda p: p["likes"], reverse=True)
    elif sort in ("low", "high"):
        products.sort(key=lambda p: to_int(p["price"], 0), reverse=(sort == "high"))
    else:
        # 더미 상품에는 created_at이 없다. 안정 정렬이므로 더미 상품은 PREVIEW_PRODUCTS 순서(최신순)를 유지한다
        products.sort(key=lambda p: p.get("created_at", ""), reverse=True)


# 2. 등록 검증
def validate_product_form(form, picture):
    """필드별 오류 메시지 dict를 반환한다. 오류가 없으면 빈 dict이다."""
    errors = {}
    for field, message in [
        ("address", "거래할 주소를 입력해 주세요."),
        ("description", "상세 설명을 입력해 주세요."),
    ]:
        if not form.get(field, "").strip():
            errors[field] = message

    name_error = validate_name(form.get("name", "").strip())
    if name_error is not None:
        errors["name"] = name_error
    price = to_int(form.get("price"))
    if price is None or price <= 0:
        errors["price"] = "가격을 0보다 큰 숫자로 입력해 주세요."
    if form.get("status") not in CONDITIONS:
        errors["status"] = "상품 상태를 골라 주세요."
    picture_error = validate_picture(picture)
    if picture_error is not None:
        errors["picture"] = picture_error
    return errors


def validate_name(name):
    if not name:
        return "상품명을 입력해 주세요."
    if name.lower() in RESERVED_NAMES:
        return "이 이름으로는 등록할 수 없어요. 이름을 조금 바꿔 주세요."
    if any(char in FORBIDDEN_NAME_CHARS for char in name):
        return "상품명에는 . $ # [ ] 문자를 쓸 수 없어요."
    if get_product(name) is not None:
        return "같은 이름의 상품이 이미 있어요. 이름을 조금 바꿔 주세요."
    return None


def validate_picture(picture):
    if picture is None or not picture.filename:
        return "대표 사진을 올려 주세요."
    extension = os.path.splitext(picture.filename)[1].lower()
    if extension not in PICTURE_EXTENSIONS:
        return "JPG, PNG 파일만 올릴 수 있어요."
    picture.stream.seek(0, os.SEEK_END)
    size = picture.stream.tell()
    picture.stream.seek(0)
    if size > PICTURE_MAX_BYTES:
        return "5MB 이하의 사진만 올릴 수 있어요."
    return None


# 3. 사진 저장
def save_picture(picture):
    """사진을 UPLOAD_DIR에 저장하고 파일명을 반환한다.

    파일명이 겹치지 않도록 앞에 uuid를 추가한다. 한글만으로 된 이름은 secure_filename이 빈 문자열을
    반환하므로 그때는 uuid와 확장자만 사용한다.
    """
    stem, extension = os.path.splitext(picture.filename)
    safe_stem = secure_filename(stem)
    filename = "_".join(part for part in (uuid.uuid4().hex, safe_stem) if part) + extension.lower()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    picture.save(os.path.join(UPLOAD_DIR, filename))
    return filename


# 4. 상품 저장소 (Firebase /products/{key} 또는 더미)
def product_key(name):
    """상품명을 Firebase 키로 바꾼다. Firebase 키에 쓸 수 없는 "/"를 KEY_SLASH로 바꾼다."""
    # ponytail: 상품명에 KEY_SLASH가 직접 들어가면 "/"가 들어간 이름과 키가 같아진다. 충돌이 실제로 생기면 키 인코딩을 다시 정한다
    return name.replace("/", KEY_SLASH)


def load_products():
    if db is None:
        return list(PREVIEW_PRODUCTS)
    stored = db.child("products").get().val() or {}
    return [with_date(product) for product in stored.values()]


def get_product(name):
    if db is None:
        return find_product(name)
    product = db.child("products").child(product_key(name)).get().val()
    return None if product is None else with_date(product)


def save_product(product):
    if db is None:
        PREVIEW_PRODUCTS.insert(0, with_date(product))
        return
    db.child("products").child(product_key(product["name"])).set(product)


def with_date(product):
    """FE가 쓰는 date(예: 2026.10.06)를 created_at에서 만들어 추가한다."""
    return {**product, "date": product["created_at"][:10].replace("-", ".")}


def is_liked(name):
    """로그인한 사용자가 이 상품을 찜했는지. Firebase 경로: /likes/{user_id}/{key}"""
    user_id = session.get("id")
    if db is None or user_id is None:
        return False
    return db.child("likes").child(user_id).child(product_key(name)).get().val() is not None
