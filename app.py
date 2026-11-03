import hashlib
import os
from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from database import DBhandler

app = Flask(__name__)
app.config["SECRET_KEY"] = "helloosp"
DB = DBhandler()
UPLOAD_DIR = os.path.join(app.static_folder, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/list")
def item_list():
    return render_template("list.html")


@app.route("/review")
def review_list():
    return render_template("review.html")


@app.route("/reg_items")
def reg_items():
    return render_template("reg_items.html")


@app.route("/reg_reviews")
def reg_reviews():
    return render_template("reg_reviews.html")


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
