"""회원 라우트: auth_login, auth_signup, auth_logout"""

from flask import flash, redirect, render_template, request, session, url_for

from core import app


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
