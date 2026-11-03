# 2026_osp_project_Giter

2026 Open Software Platform 팀 프로젝트 (Giter)

## 실행 방법

Firebase 웹 앱 config(`databaseURL` 포함)를 JSON 형식으로 `authentication/firebase_auth.json`에 저장한다. 이 폴더는 GitHub에 올리지 않는다.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

브라우저에서 `http://127.0.0.1:5001` 접속
