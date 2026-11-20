"""리뷰 라우트: review_list, review_new, review_done, review_detail"""

from flask import redirect, render_template, request, session, url_for

from core import app, to_int
from dummy import find_product


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
