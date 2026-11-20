"""BE 서버 (BoughtIT) 실행 파일

실행: (apps/be에서) python app.py  → http://127.0.0.1:5001/
"""

from core import app

# 라우트 모듈을 import하면 각 모듈의 @app.route가 app에 등록된다.
from routes import auction, auth, chat, my, product, review, wanted  # noqa: E402, F401

if __name__ == "__main__":
    app.run(debug=True, port=5001)
