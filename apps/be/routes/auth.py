"""회원 라우트: auth_login, auth_signup, auth_logout"""

from flask import flash, redirect, render_template, request, session, url_for
import hashlib, re, os, secrets, smtplib, hmac
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from dotenv import load_dotenv

from core import app, db

load_dotenv()

def get_user(user_id):
    return db.child("users").child(user_id).get().val()


def user_duplicate_check(user_id):
    return get_user(user_id) is not None


def email_duplicate_check(email):
    users = db.child("users").get().val() or {}

    for user in users.values():
        if user and user.get("email", "").lower() == email.lower():
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

# 이메일 입력값 검증 및 오류 변환
def validate_email(email):
    errors = {}

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


# 회원가입 입력값 검증 및 오류 반환
def validate_signup(user_id, password, password_confirm, email, verification):
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
    errors.update(validate_email(email))

    # 이메일 인증 여부 검사
    if (
        not verification
        or not verification.get("verified")
        or verification.get("email") != email
        or datetime.now(timezone.utc).timestamp()
            >= verification.get("expires_at", 0)
    ):
        errors["auth_code"] = "이화인 메일 인증을 완료해 주세요."

    return errors


# 인증 메일 발송
def send_verification_email(email, code):
    """Gmail SMTP를 이용해 인증 코드 발송"""

    mail_user = os.getenv("MAIL_USER")
    mail_password = os.getenv("MAIL_PASSWORD")

    # 개발환경：환경변수가 없는 경우
    if not mail_user or not mail_password:
        return False

    message = EmailMessage()
    message["Subject"] = "[BoughtIT] 이메일 인증 코드"
    message["From"] = mail_user
    message["To"] = email

    message.set_content(f"""
안녕하세요. BoughtIT입니다.

이메일 인증 코드는 다음과 같습니다.

인증 코드: {code}

인증 코드는 발급 시점부터 5분 동안 유효합니다.
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
        smtp.login(mail_user, mail_password)
        smtp.send_message(message)

    return True


# 이메일 인증 코드 발송
@app.route("/signup/code", methods=["POST"])
def auth_send_code():
    email = request.form.get("email", "").strip().lower()

    errors = validate_email(email)

    if errors:
        return errors["email"], 400

    # 6자리 인증 코드 생성
    code = f"{secrets.randbelow(1000000):06d}"

    try:
        sent = send_verification_email(email, code)

    except Exception:
        app.logger.exception("인증 메일 발송 실패")
        return "인증 메일 발송 중 오류가 발생했어요.", 500

    expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=5)
    ).timestamp()

    # 세션에 인증 정보 저장
    session["email_verification"] = {
        "email": email,
        "code_hash": hashlib.sha256(
            code.encode("utf-8")
        ).hexdigest(),
        "expires_at": expires_at,
        "verified": False
    }

     # 개발 환경: 이메일을 발송하지 않고 인증 코드 표시
    if not sent:
        message = f"개발용 인증 코드: {code}"
        flash(message, "info")
        return message, 200

    return "인증 코드가 이메일로 발송되었어요.", 200


# 이메일 인증 코드 확인
@app.route("/signup/verify", methods=["POST"])
def auth_verify_code():
    email = request.form.get("email", "").strip().lower()
    auth_code = request.form.get("auth_code", "").strip()

    verification = session.get("email_verification")

    if not verification:
        return "먼저 인증 코드를 요청해 주세요.", 400

    if verification.get("email") != email:
        return "인증을 요청한 이메일과 일치하지 않아요.", 400

    if datetime.now(timezone.utc).timestamp() >= verification.get("expires_at", 0):
        session.pop("email_verification", None)
        return "인증 코드가 만료되었어요. 다시 발급해 주세요.", 400

    if not re.fullmatch(r"\d{6}", auth_code):
        return "인증 코드는 숫자 6자리로 입력해 주세요.", 400

    input_hash = hashlib.sha256(
        auth_code.encode("utf-8")
    ).hexdigest()

    if not hmac.compare_digest(
        input_hash,
        verification["code_hash"]
    ):
        return "인증 코드가 일치하지 않아요.", 400

    verification["verified"] = True
    session["email_verification"] = verification

    return "메일 인증이 완료되었어요.", 200


@app.route("/login", methods=["GET", "POST"])
def auth_login():
    """로그인. POST: user_id, password → 성공 시 product_list로 redirect"""
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")

        if not user_id or not password:
            flash("아이디 또는 비밀번호를 입력해 주세요.", "error")
            return render_template("auth/login.html"), 400
        
        user = get_user(user_id)

        if user is None:
            flash("아이디 또는 비밀번호가 맞지 않아요.", "error")
            return render_template("auth/login.html"), 401

        pw_hash = hashlib.sha256(
            password.encode("utf-8")
            ).hexdigest()

        if user.get("pw_hash") == pw_hash:
            session["id"] = user_id
            return redirect(url_for("product_list"))

        flash("아이디 또는 비밀번호가 맞지 않아요.", "error")
        return render_template("auth/login.html"), 401

    return render_template("auth/login.html")


@app.route("/signup", methods=["GET", "POST"])
def auth_signup():
    """회원가입. POST: user_id, password, password_confirm, email, auth_code, phone(선택)"""
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        email = request.form.get("email", "").strip().lower()
        #TODO : auth_code 코드 작성
        phone = request.form.get("phone", "").strip() or None

        form = {
            "user_id": user_id,
            "email": email,
            "phone": phone or ""
        }

        verification = session.get("email_verification")

        errors = validate_signup(
            user_id,
            password,
            password_confirm,
            email,
            verification
        )

        if errors:

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
        session.pop("email_verification", None)

        return redirect(url_for("auth_login"))
    
    return render_template("auth/signup.html")


@app.route("/logout")
def auth_logout():
    """로그아웃. session에서 id를 삭제하고 product_list로 redirect"""
    session.pop("id", None)
    return redirect(url_for("product_list"))