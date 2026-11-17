import hashlib
import math
import os
import uuid
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from database import DBhandler

app = Flask(__name__)
app.config["SECRET_KEY"] = "helloosp"
DB = DBhandler()
UPLOAD_DIR = os.path.join(app.static_folder, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
REVIEWS_PER_PAGE = 4  # 2*2 레이아웃


def save_upload(file):
    """업로드 파일을 static/uploads에 고유한 이름으로 저장하고 파일명을 돌려준다."""
    # secure_filename()은 한글 파일명을 지워 확장자까지 잃을 수 있어 확장자만 따로 받는다
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext[1:].isalnum():
        ext = ""
    filename = f"{uuid.uuid4().hex}{ext}"
    file.save(os.path.join(UPLOAD_DIR, filename))
    return filename


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/list")
def item_list():
    page = request.args.get("page", 1, type=int)
    per_page = 6
    items = list(DB.get_items().items())
    page_count = max(1, math.ceil(len(items) / per_page))
    page = min(max(page, 1), page_count)
    start = (page - 1) * per_page
    return render_template(
        "list.html",
        items=items[start:start + per_page],
        page=page,
        page_count=page_count,
        total=len(items),
    )


@app.route("/view_detail/<name>/")
def view_item_detail(name):
    data = DB.get_item_byname(name)
    if data is None:
        abort(404)
    liked = False
    if session.get("id"):
        liked = DB.get_heart_byname(session["id"], name).get("interested") == "Y"
    return render_template(
        "detail.html", name=name, data=data, liked=liked, like_count=DB.count_hearts(name)
    )


# ---------- 리뷰 ----------
@app.route("/review")
def review_list():
    page = request.args.get("page", 1, type=int)
    # push() 키는 시간순으로 정렬되므로 키 역순 = 최신순
    reviews = sorted(DB.get_reviews().items(), key=lambda kv: kv[0], reverse=True)
    page_count = max(1, math.ceil(len(reviews) / REVIEWS_PER_PAGE))
    page = min(max(page, 1), page_count)
    start = (page - 1) * REVIEWS_PER_PAGE
    return render_template(
        "review.html",
        reviews=reviews[start:start + REVIEWS_PER_PAGE],
        page=page,
        page_count=page_count,
        total=len(reviews),
    )


@app.route("/view_review_detail/<review_id>/")
def view_review_detail(review_id):
    data = DB.get_review_byid(review_id)
    if data is None:
        abort(404)
    return render_template("review_detail.html", review_id=review_id, data=data)


@app.route("/reg_review_init/<name>/")
def reg_review_init(name):
    if DB.get_item_byname(name) is None:
        abort(404)
    return render_template("reg_reviews.html", name=name)


@app.route("/reg_review", methods=["POST"])
def reg_review():
    data = {f: request.form.get(f, "").strip() for f in ["item_name", "title", "content", "rating"]}
    photo = request.files.get("photo")
    if (
        not all(data.values())
        or data["rating"] not in {"1", "2", "3", "4", "5"}
        or not (photo and photo.filename)
        or DB.get_item_byname(data["item_name"]) is None
    ):
        flash("상품명, 제목, 사진, 내용, 별점을 모두 입력해 주세요.")
        return redirect(url_for("reg_reviews", name=data["item_name"] or None))

    data["reviewer"] = session.get("id", "")
    filename = save_upload(photo)  # 사진은 서버에 저장하고 DB에는 파일명만 저장
    review_id = DB.insert_review(data, filename)
    return redirect(url_for("view_review_detail", review_id=review_id))


# ---------- 좋아요 (AJAX) ----------
def _set_heart(name, is_heart):
    if not session.get("id"):
        return jsonify({"msg": "로그인이 필요합니다.", "login_url": url_for("login")}), 401
    if DB.get_item_byname(name) is None:
        return jsonify({"msg": "존재하지 않는 상품입니다."}), 404
    DB.update_heart(session["id"], is_heart, name)
    return jsonify({"liked": is_heart == "Y", "count": DB.count_hearts(name)})


@app.route("/show_heart/<name>/")
def show_heart(name):
    liked = bool(session.get("id")) and DB.get_heart_byname(session["id"], name).get("interested") == "Y"
    return jsonify({"liked": liked, "count": DB.count_hearts(name)})


@app.route("/like/<name>/", methods=["POST"])
def like(name):
    return _set_heart(name, "Y")


@app.route("/unlike/<name>/", methods=["POST"])
def unlike(name):
    return _set_heart(name, "N")


@app.route("/reg_items")
def reg_items():
    return render_template("reg_items.html")


@app.route("/reg_reviews")
def reg_reviews():
    # 상품 상세의 버튼을 거치지 않고 들어온 경우 상품을 직접 고른다
    name = request.args.get("name")
    if name and DB.get_item_byname(name) is not None:
        return redirect(url_for("reg_review_init", name=name))
    return render_template("reg_reviews.html", name=None, item_names=list(DB.get_items().keys()))


@app.route("/submit_item", methods=["POST"])
def submit_item():
    fields = ["name", "seller", "price", "address", "status", "email"]
    data = {f: request.form.get(f, "") for f in fields}

    picture = request.files.get("picture")
    image_url = None
    filename = ""
    if picture and picture.filename:
        filename = secure_filename(picture.filename)
        picture.save(os.path.join(UPLOAD_DIR, filename))
        image_url = f"uploads/{filename}"

    DB.insert_item(data["name"], data, filename)
    return render_template("result.html", data=data, image_url=image_url)


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/login_confirm", methods=["POST"])
def login_user():
    id_ = request.form["id"]
    pw_hash = hashlib.sha256(request.form["pw"].encode("utf-8")).hexdigest()
    if DB.find_user(id_, pw_hash):
        session["id"] = id_
        return redirect(url_for("item_list"))
    flash("Wrong ID or PW!")
    return render_template("login.html")


@app.route("/logout")
def logout_user():
    session.clear()
    return redirect(url_for("index"))


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/signup_post", methods=["POST"])
def register_user():
    data = request.form
    pw_hash = hashlib.sha256(data["pw"].encode("utf-8")).hexdigest()
    if DB.insert_user(data, pw_hash):
        return redirect(url_for("login"))
    flash("이미 존재하는 ID입니다.")
    return redirect(url_for("signup"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
