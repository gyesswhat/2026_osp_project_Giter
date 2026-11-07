"""FE 미리보기 서버 (개발용)

BE 연동 전에 base.html과 공통 컴포넌트, 각자 만든 화면을 확인하기 위한 서버다.
헤더의 url_for가 깨지지 않도록 라우트 함수 이름 규칙(도메인_동작)대로 빈 라우트를 등록해 둔다.
화면을 만들면 아래 SCREENS에 (경로, 함수 이름, 템플릿)을 추가하면 된다.

실행: (apps/fe 에서) python preview.py → http://127.0.0.1:5002/dev/components
"""

from flask import Flask, redirect, render_template, session, url_for
from jinja2 import TemplateNotFound

app = Flask(__name__)
app.config["SECRET_KEY"] = "fe-preview"

# (경로, 라우트 함수 이름, 템플릿) — 템플릿이 아직 없으면 준비 중 안내를 띄운다
SCREENS = [
    ("/", "product_list", "product/list.html"),
    ("/product/detail", "product_detail", "product/detail.html"),
    ("/product/new", "product_new", "product/new.html"),
    ("/review", "review_list", "review/list.html"),
    ("/review/detail", "review_detail", "review/detail.html"),
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
    app.add_url_rule(path, endpoint, make_view(template))


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
