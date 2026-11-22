"""리뷰 라우트: review_list, review_new, review_done, review_detail, 찜(product_like)"""

from datetime import datetime

from flask import abort, flash, redirect, render_template, request, session, url_for

from core import app, db, to_int
from dummy import find_product
from routes.product import get_product, product_key


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
    """리뷰 작성. GET: ?name=상품명. POST: product_name, reviewer, rating, title, photo, content"""
    name = request.values.get("product_name") or request.args.get("name", "")
    product = find_product(name)
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
    rating = to_int(form.get("rating"))
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
