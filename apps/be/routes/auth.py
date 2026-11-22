"""회원 라우트: auth_login, auth_signup, auth_logout"""

from flask import flash, redirect, render_template, request, session, url_for
import hashlib, re
from datetime import datetime, timezone

from core import app, db

def get_user(user_id):
    return db.child("users").child(user_id).get().val()


def user_duplicate_check(user_id):
    return get_user(user_id) is not None


def email_duplicate_check(email):
    users = db.child("users").get().val() or {}

    for user in users.values():
        if user.get("email") == email:
            return True
        
    return False


def insert_user(user_id, pw_hash, email, phone=None):
    user_info = {
        "pw_hash": pw_hash,
        "email": email,
        "phone": phone,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    db.child("users").child(user_id).set(user_info)


# 회원가입 입력값 검증 및 오류 반환
def validate_signup(user_id, password, password_confirm, email):
    errors = {}

    # 아이디 검사
    if not user_id:
        errors["user_id"] = "아이디를 입력해 주세요."

    elif any(char in user_id for char in ".$#[]/"):
        errors["user_id"] = "아이디에 사용할 수 없는 문자가 포함되어 있어요."

    elif user_duplicate_check(user_id):
        errors["user_id"] = "이미 사용 중인 아이디에요."

    # 비밀번호 검사
    if not password:
        errors["password"] = "비밀번호를 입력해 주세요."

    elif not re.fullmatch(r"(?=.*[A-Za-z])(?=.*\d).{8,}", password):
        errors["password"] = "영문과 숫자를 섞어 8자 이상 입력해 주세요."

    # 비밀번호 확인 검사
    if not password_confirm:
        errors["password_confirm"] = "비밀번호 확인을 입력해 주세요."

    elif password != password_confirm:
        errors["password_confirm"] = "비밀번호가 일치하지 않아요."

    # 이메일 검사
    if not email:
        errors["email"] = "이메일을 입력해 주세요."

    elif not re.fullmatch(
        r"[^@\s]+@(?:ewhain\.net|ewha\.ac\.kr)",
        email,
        re.IGNORECASE
    ):
        errors["email"] = "ewhain.net 또는 ewha.ac.kr 이메일만 사용할 수 있어요."

    elif email_duplicate_check(email):
        errors["email"] = "이미 가입된 이메일이에요."

    return errors


@app.route("/login", methods=["GET", "POST"])
def auth_login():
    """로그인. POST: user_id, password → 성공 시 product_list로 redirect"""
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")
        if not user_id or not password:
            flash("아이디 또는 비밀번호를 입력해 주세요.", "error")
            return render_template("auth/login.html")
        
        user = get_user(user_id)

        if user is None:
            flash("아이디 또는 비밀번호가 맞지 않아요.", "error")
            return render_template("auth/login.html")

        pw_hash = hashlib.sha256(
            password.encode("utf-8")
            ).hexdigest()

        if user.get("pw_hash") == pw_hash:
            session["id"] = user_id
            return redirect(url_for("product_list"))

        flash("아이디 또는 비밀번호가 맞지 않아요.", "error")
        return render_template("auth/login.html")

    return render_template("auth/login.html")


@app.route("/signup", methods=["GET", "POST"])
def auth_signup():
    """회원가입. POST: user_id, password, password_confirm, email, auth_code, phone(선택)"""
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        email = request.form.get("email", "").strip()
        #TODO : auth_code 코드 작성
        # auth_code = request.form.get("auth_code", "").strip()
        phone = request.form.get("phone", "").strip() or None

        form = {
            "user_id": user_id,
            "email": email,
            "phone": phone or ""
        }

        errors = validate_signup(
            user_id,
            password,
            password_confirm,
            email
        )

        if errors:
            print("회원가입 오류:", errors) # 오류 확인용
            return render_template(
                "auth/signup.html",
                form=form,
                errors=errors
            ), 400

        pw_hash = hashlib.sha256(
            password.encode("utf-8")
        ).hexdigest()
        
        try:
            insert_user(user_id, pw_hash, email, phone)

        except Exception:
            errors = {
                "general": "회원가입 처리 중 오류가 발생했어요."
            }

            return render_template(
                "auth/signup.html",
                form=form,
                errors=errors
            ), 500
        
        flash("회원가입을 완료했어요.")
        return redirect(url_for("auth_login"))
    
    return render_template("auth/signup.html")


@app.route("/logout")
def auth_logout():
    """로그아웃. session에서 id를 삭제하고 product_list로 redirect"""
    session.pop("id", None)
    return redirect(url_for("product_list"))
