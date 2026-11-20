"""Flask 앱(app)과 Firebase 연결(db)을 생성한다.

라우트 모듈은 이 파일에서 app, db를 import해서 사용한다.
"""

import json
import os

from flask import Flask

# 1. 경로 설정
_base = os.path.dirname(__file__)
_fe = os.path.join(_base, "../fe")

app = Flask(
    __name__,
    template_folder=os.path.join(_fe, "templates"),
    static_folder=os.path.join(_fe, "static"),
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "boughtit-dev")

# 2. Firebase 초기화 (설정 파일이 없으면 db는 None으로 유지한다)
db = None
_config_path = os.path.join(_base, "../../authentication/firebase_auth.json")
try:
    import pyrebase  # type: ignore

    with open(_config_path) as _f:
        _config = json.load(_f)
    _firebase = pyrebase.initialize_app(_config)
    db = _firebase.database()
except Exception as e:
    # 연결에 실패하면 더미 데이터로 동작한다. 원인을 확인할 수 있도록 출력한다.
    print(f"Firebase 연결 실패, 더미 데이터로 실행한다: {e!r}")


# 3. 공통 함수
def to_int(value, default=None):
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default
