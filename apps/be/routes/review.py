"""리뷰 라우트: review_list, review_new, review_done, review_detail, 찜(product_like)"""

from datetime import datetime

from flask import abort, flash, redirect, render_template, request, session, url_for

from core import app, db, to_int
from routes.product import get_product, product_key, save_picture, validate_picture


@app.route("/product/like", methods=["POST"])
def product_like():
    """찜 토글. 폼: name(필수). 로그인 필요, 없는 상품은 404, 자기 상품은 상세로 redirect."""
    user_id = session.get("id")
    if user_id is None:
        flash("찜하려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))

    name = request.form.get("name", "")
    product = get_product(name)
    if product is None:
        abort(404)
    if product.get("seller") == user_id:
        flash("내가 올린 상품은 찜할 수 없어요.", "error")
        return redirect(url_for("product_detail", name=name))

    toggle_like(user_id, name, product)
    return redirect(url_for("product_detail", name=name))


def toggle_like(user_id, name, product):
    """/likes/{user_id}/{key}를 토글하고 /products/{key}/likes를 ±1(0 미만 금지)한다.

    db가 없으면 저장하지 않고 flash로만 알린다. pyrebase의 db.child()는 같은 db 객체에
    경로를 이어 붙이고 get()/set()/remove() 실행 후에야 경로를 비우므로, ref를 변수에
    저장해 재사용하지 않고 매번 db.child(...)...부터 다시 체인으로 실행한다.
    """
    if db is None:
        flash("지금은 찜을 저장할 수 없어요.", "error")
        return

    key = product_key(name)
    likes = product.get("likes", 0)

    if db.child("likes").child(user_id).child(key).get().val() is None:
        db.child("likes").child(user_id).child(key).set(
            {"created_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        )
        db.child("products").child(key).child("likes").set(likes + 1)
        flash("찜했어요.")
    else:
        db.child("likes").child(user_id).child(key).remove()
        db.child("products").child(key).child("likes").set(max(0, likes - 1))
        flash("찜을 취소했어요.")


@app.route("/review")
def review_list():
    """리뷰 목록. 쿼리: seller, page"""
    seller = request.args.get("seller", "")
    return render_template("review/list.html", seller=seller, reviews=[], total=0, page=1, total_pages=1)


@app.route("/review/new", methods=["GET", "POST"])
def review_new():
    """리뷰 작성. 로그인 필요. GET: ?name=상품명. POST(multipart/form-data): product_name, rating, title, content, photo"""
    reviewer = session.get("id")
    if reviewer is None:
        flash("리뷰를 쓰려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))

    if request.method == "GET":
        name = request.args.get("name", "")
        product = get_product(name) if name else None
        return render_template("review/new.html", product=product)

    form = request.form
    errors = {}

    product_name = form.get("product_name", "").strip()
    product = None
    if not product_name:
        errors["product_name"] = "상품명을 입력해 주세요."
    else:
        product = get_product(product_name)
        if product is None:
            errors["product_name"] = "없는 상품이에요."
        elif product.get("seller") == reviewer:
            errors["product_name"] = "내가 올린 상품에는 리뷰를 쓸 수 없어요."
        elif get_review(product_name) is not None:
            errors["product_name"] = "이미 리뷰를 작성한 상품이에요."

    for field, text in [("title", "제목을 입력해 주세요."), ("content", "내용을 입력해 주세요.")]:
        if not form.get(field, "").strip():
            errors[field] = text

    rating = to_int(form.get("rating"))
    if rating not in range(1, 6):
        errors["rating"] = "별점을 1~5점 중에서 골라 주세요."

    photo = request.files.get("photo")
    if photo and photo.filename:
        photo_error = validate_picture(photo)
        if photo_error is not None:
            errors["photo"] = photo_error

    if errors:
        return render_template("review/new.html", product=product, form=form, errors=errors), 400

    if db is None:
        flash("지금은 리뷰를 저장할 수 없어요.", "error")
        return render_template("review/new.html", product=product, form=form, errors=errors)

    review = {
        "product_name": product_name,
        "reviewer": reviewer,
        "seller": product.get("seller"),
        "rating": rating,
        "title": form["title"].strip(),
        "content": form["content"].strip(),
        "photo": save_picture(photo) if photo and photo.filename else "",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    save_review(review)
    session["last_review"] = product_name
    flash("리뷰를 등록했어요.")
    return redirect(url_for("review_done"))


@app.route("/review/done")
def review_done():
    """리뷰 등록 완료. 세션에 저장한 last_review(상품명)로 리뷰를 읽어 보여 준다."""
    name = session.get("last_review")
    review = get_review(name) if name else None
    return render_template("review/done.html", review=review)


def get_review(name):
    """/reviews/{product_key(name)}를 읽는다. db가 없으면 None."""
    if db is None:
        return None
    return db.child("reviews").child(product_key(name)).get().val()


def save_review(review):
    """/reviews/{product_key(product_name)}에 저장한다."""
    db.child("reviews").child(product_key(review["product_name"])).set(review)


def with_review_date(review):
    """FE가 쓰는 date(예: 2026.10.06)를 created_at에서 만들어 추가한다. created_at이 없거나 비어 있으면 date는 ''이다."""
    created_at = review.get("created_at") or ""
    date = created_at[:10].replace("-", ".") if created_at else ""
    return {**review, "date": date}


@app.route("/review/<path:name>")
def review_detail(name):
    """리뷰 상세. name은 리뷰를 쓴 상품의 상품명이다. 리뷰가 없으면 404."""
    review = get_review(name)
    if review is None:
        abort(404)
    return render_template("review/detail.html", review=with_review_date(review), product=get_product(name))
