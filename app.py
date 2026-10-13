import os
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

app = Flask(__name__)
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
    if picture and picture.filename:
        filename = secure_filename(picture.filename)
        picture.save(os.path.join(UPLOAD_DIR, filename))
        image_url = f"uploads/{filename}"

    return render_template("result.html", data=data, image_url=image_url)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
