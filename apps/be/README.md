# BoughtIT BE

Flask 백엔드 서버. `apps/fe`의 템플릿과 static을 그대로 사용한다.

## 실행 방법

```bash
cd apps/be
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5001/ 에서 확인
```

Firebase 설정 파일(`authentication/firebase_auth.json`)이 없으면 더미 데이터로 실행된다.

| 서버 | 포트 |
| --- | --- |
| BE | 5001 |
| FE 미리보기 | 5002 |

## 구조와 담당

```
apps/be/
├─ app.py          # 실행 파일. 라우트 모듈을 import한다
├─ core.py         # Flask 앱(app), Firebase 연결(db), 공통 함수
├─ dummy.py        # 더미 데이터. DB 로직으로 교체한 뒤 삭제한다
└─ routes/         # 도메인별 라우트
   ├─ auth.py      # 회원가입, 로그인, 로그아웃
   ├─ product.py   # 상품 등록, 목록, 상세, 약속 신청
   ├─ review.py    # 리뷰 작성, 목록, 상세
   ├─ auction.py   # 경매 (라우트 없음)
   ├─ wanted.py    # 구해요 (스텁)
   ├─ my.py        # 마이, 내 상품 관리 (스텁)
   └─ chat.py      # 채팅 (스텁)
```

| 파일 | 담당 | 이슈 |
| --- | --- | --- |
| `routes/auth.py` | 소정 | #25 |
| `routes/product.py` | 겨레 (약속 신청 `product_reserve`는 소정) | #26, #41 |
| `routes/review.py` | 소현 (찜 포함) | #27 |
| `routes/auction.py` | 겨레 | #39, #40 |
| `routes/wanted.py` | 소현 | #42 |
| `routes/my.py` | 소정 | #41 |
| `routes/chat.py` | 소정 | #43 |
| `core.py`, `app.py` | 겨레 | 수정이 필요하면 먼저 알린다 |

## 작업 규칙

- 자기 담당 파일에서만 작업한다. 다른 파일을 수정해야 하면 담당자에게 먼저 알린다.
- 라우트 함수 이름, URL, 폼 필드 이름은 `apps/fe/ROUTES.md`를 따른다. 템플릿이 `url_for('auth_login')`처럼 함수 이름으로 호출하므로 Blueprint를 사용하지 않고 `from core import app`으로 가져온 `app`에 `@app.route`로 등록한다.
- DB는 `from core import db`로 사용한다. 설정 파일이 없으면 `db`는 `None`이다.
- 라우트 파일을 새로 만들면 `app.py`의 import 줄에 추가한다.
- 스텁(`abort(501)`)은 헤더 탭의 `url_for` 오류를 막기 위한 것이다. 구현할 때 교체한다.
