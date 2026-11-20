# BoughtIT BE

Flask 백엔드 서버. FE 템플릿을 그대로 사용한다.

## 실행 방법

```bash
# 프로젝트 루트에서
cd apps/be
pip install -r requirements.txt
python app.py
# http://127.0.0.1:5001/ 에서 확인
```

Firebase 설정 파일(`authentication/firebase_auth.json`)이 없어도 실행된다. 더미 데이터로 동작한다.

## 포트

| 서버 | 포트 |
| --- | --- |
| BE (본 서버) | 5001 |
| FE 미리보기 | 5002 |
