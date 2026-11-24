---
layout: post
title: "BoughtIT 로컬에서 실행하기: Flask + Pyrebase4 + Firebase Realtime Database 설정"
type: Guide
order: 3
date: 2026-11-22 10:00:00 +0900
author: BoughtIT 팀
summary: 저장소를 받은 뒤 가상환경, 패키지 설치, Firebase 설정 파일, BE 서버와 FE 미리보기 서버 실행까지 처음부터 따라 할 수 있게 정리했습니다.
---

## 상황

BoughtIT는 FE와 BE가 한 저장소(모노레포)에 있습니다. `apps/fe`에는 Jinja2 템플릿과 정적 파일이, `apps/be`에는 Flask 서버 코드가 있습니다. 데이터는 Firebase Realtime Database에 저장하고, Python에서는 **Pyrebase4** 라이브러리로 접근합니다.

새 팀원이 합류하거나 다른 컴퓨터에서 작업을 이어 가려면 실행 방법부터 알아야 합니다. 특히 Firebase 설정 파일은 보안 때문에 저장소에 올리지 않아서, 저장소만 받아서는 무엇을 더 준비해야 하는지 알기 어렵습니다. 이 글은 그 과정을 한 번에 따라 할 수 있도록 정리한 가이드입니다.

## 목표

- 가상환경을 만들고 필요한 패키지를 설치한다.
- Firebase 프로젝트를 만들고 설정 파일(`authentication/firebase_auth.json`)을 준비한다.
- BE 서버(포트 5001)와 FE 미리보기 서버(포트 5002)를 실행한다.

준비물은 **Python 3.12**(팀은 3.12.8 사용), Git, Google 계정입니다. 명령은 macOS 기준이고, Windows에서 다른 부분은 따로 적었습니다.

## 단계 1. 저장소 받기

```bash
git clone https://github.com/gyesswhat/2026_osp_project_Giter.git
cd 2026_osp_project_Giter
```

저장소를 받고 그 폴더로 이동합니다. 이후 명령은 모두 이 폴더(저장소 루트)에서 시작합니다.

## 단계 2. 가상환경 만들기

프로젝트마다 패키지 버전이 섞이지 않도록 가상환경을 만듭니다.

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

```powershell
# Windows (PowerShell)
py -m venv venv
venv\Scripts\Activate.ps1
```

가상환경이 켜지면 터미널 프롬프트 앞에 `(venv)`가 붙습니다. `venv/` 폴더는 `.gitignore`에 들어 있어서 저장소에 올라가지 않습니다. Windows PowerShell에서 "스크립트를 실행할 수 없습니다"라는 오류가 나면, 한 번만 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`를 실행한 뒤 다시 켜면 됩니다.

## 단계 3. 패키지 설치

```bash
pip install -r apps/be/requirements.txt
python -c "import flask, pyrebase; print('ok')"
```

`requirements.txt`에는 `flask`와 `pyrebase4` 두 줄이 있습니다. 두 번째 명령이 `ok`를 출력하면 설치가 끝난 것입니다. 패키지 이름은 `pyrebase4`지만 코드에서는 `import pyrebase`로 불러온다는 점이 헷갈리기 쉽습니다.

## 단계 4. Firebase 프로젝트와 Realtime Database 만들기

1. [Firebase 콘솔](https://console.firebase.google.com)에서 **프로젝트 추가**를 눌러 프로젝트를 만듭니다.
2. 왼쪽 메뉴에서 **Realtime Database**를 찾아 **데이터베이스 만들기**를 누릅니다. 위치를 고르고, 개발 중에는 **테스트 모드**로 시작합니다.
3. **프로젝트 설정(톱니바퀴) → 일반 → 내 앱**에서 웹 앱(`</>` 아이콘)을 등록합니다.
4. 등록이 끝나면 `firebaseConfig`라는 JavaScript 객체가 보입니다. 이 값을 다음 단계에서 JSON 파일로 옮깁니다.

**순서가 중요합니다.** Realtime Database를 만들기 전에 웹 앱을 등록하면 `firebaseConfig`에 `databaseURL`이 빠져 있을 수 있습니다. 그런 경우 데이터베이스를 만든 뒤 설정 화면을 다시 열어 `databaseURL`이 생겼는지 확인하세요.

## 단계 5. 설정 파일 만들기

저장소 루트에 `authentication` 폴더를 만들고 `firebase_auth.json` 파일을 만듭니다. `firebaseConfig`의 값을 JSON 형식으로 옮기면 됩니다. JavaScript 객체와 달리 **키도 큰따옴표로 감싸야** 합니다.

```json
{
  "apiKey": "<내 apiKey>",
  "authDomain": "<프로젝트ID>.firebaseapp.com",
  "databaseURL": "<콘솔에 나온 databaseURL>",
  "projectId": "<프로젝트ID>",
  "storageBucket": "<콘솔에 나온 storageBucket>",
  "messagingSenderId": "<숫자>",
  "appId": "<내 appId>"
}
```

꺾쇠(`< >`) 부분을 콘솔에 나온 값으로 바꿉니다. `databaseURL`과 `storageBucket`은 데이터베이스 위치나 프로젝트를 만든 시기에 따라 주소 형식이 다르니, 직접 고쳐 쓰지 말고 콘솔 값을 그대로 복사하세요. 이 중 Pyrebase4가 **반드시 요구하는 키는 네 개**입니다. Pyrebase4 소스의 `Firebase.__init__`을 보면 다음처럼 대괄호로 바로 읽기 때문에, 하나라도 없으면 `KeyError`가 납니다.

```python
self.api_key = config["apiKey"]
self.auth_domain = config["authDomain"]
self.database_url = config["databaseURL"]
self.storage_bucket = config["storageBucket"]
```

이 파일에는 프로젝트 접근 정보가 들어 있으므로 **절대 커밋하지 않습니다.** 저장소의 `.gitignore`에 `authentication/`이 들어 있어서 `git add .`을 해도 올라가지 않습니다. 팀원끼리는 이 파일을 저장소 밖에서 따로 전달합니다.

## 단계 6. BE 서버 실행

```bash
cd apps/be
python app.py
```

정상이면 이런 출력이 나옵니다.

```text
 * Serving Flask app 'core'
 * Debug mode: on
 * Running on http://127.0.0.1:5001
```

브라우저에서 `http://127.0.0.1:5001`을 열면 상품 목록이 보입니다. BE는 `apps/fe`의 템플릿과 정적 파일을 그대로 쓰도록 설정되어 있어서, FE 팀이 고친 화면이 BE 서버에도 바로 반영됩니다.

설정 파일이 없거나 형식이 틀려도 서버는 꺼지지 않습니다. `apps/be/core.py`가 Firebase 연결에 실패하면 원인을 출력하고 **더미 데이터로 실행**하도록 만들었기 때문입니다.

```python
db = None
_config_path = os.path.join(_base, "../../authentication/firebase_auth.json")
try:
    import pyrebase  # type: ignore

    with open(_config_path) as _f:
        _config = json.load(_f)
    _firebase = pyrebase.initialize_app(_config)
    db = _firebase.database()
except Exception as e:
    print(f"Firebase 연결 실패, 더미 데이터로 실행한다: {e!r}")
```

설정 파일 없이 실행하면 첫 줄에 다음 메시지가 나옵니다. 이 메시지가 보이면 화면은 뜨지만 저장은 되지 않는 상태이니 단계 5를 다시 확인하세요.

```text
Firebase 연결 실패, 더미 데이터로 실행한다: FileNotFoundError(2, 'No such file or directory')
```

## 단계 7. FE 미리보기 서버 실행 (Firebase 없이)

화면만 확인하고 싶을 때는 FE 미리보기 서버를 씁니다. Firebase 설정이 필요 없고 Flask만 있으면 됩니다.

```bash
cd apps/fe
python preview.py
```

`http://127.0.0.1:5002`에서 더미 상품으로 모든 화면을 볼 수 있고, `http://127.0.0.1:5002/dev/components`에서는 공통 컴포넌트를 한눈에 볼 수 있습니다. 두 서버는 포트가 달라서 동시에 켜 둘 수 있습니다.

## 결과

BE 서버를 실행하고 `http://127.0.0.1:5001`을 연 화면입니다. 헤더, 검색·필터, 상품 카드가 모두 정상적으로 그려집니다.

![BE 서버로 연 상품 목록]({{ '/assets/img/guide-be-home.png' | relative_url }})
*BE 서버(포트 5001)의 상품 목록. 설정 파일이 없을 때는 이렇게 더미 상품으로 실행됩니다.*

## 자주 만나는 문제

| 증상 | 원인과 해결 |
| --- | --- |
| `Firebase 연결 실패 ... KeyError('databaseURL')` | 설정에 `databaseURL`이 없습니다. Realtime Database를 만든 뒤 설정 값을 다시 복사합니다 (단계 4). |
| `Address already in use` | 같은 포트로 서버가 이미 켜져 있습니다. 다른 터미널의 서버를 `Ctrl + C`로 끄고 다시 실행합니다. |
| `ModuleNotFoundError: No module named 'pyrebase'` | 가상환경이 꺼진 터미널에서 실행했거나 설치를 건너뛰었습니다. `(venv)` 표시를 확인하고 단계 3을 다시 합니다. |
| 저장할 때 `Permission denied` 오류 | Realtime Database 보안 규칙이 막고 있습니다. 테스트 모드는 만든 지 30일이 지나면 막히므로 콘솔의 **규칙** 탭에서 기간을 확인합니다. |

## 배운 점

- 설정 파일처럼 저장소에 올릴 수 없는 것이 있는 프로젝트일수록 **실행 문서가 필요합니다.** 파일 이름, 위치, 필요한 키를 정확히 적어 두어야 처음 받는 사람도 막히지 않습니다.
- Firebase 연결에 실패해도 더미 데이터로 실행되게 만들어 두면, 설정 파일이 없는 팀원도 화면 작업을 바로 시작할 수 있습니다. 대신 "저장이 안 되는 상태"라는 걸 알 수 있도록 원인을 출력하는 것이 중요했습니다.
- 라이브러리가 어떤 설정을 필수로 요구하는지는 소스의 생성자를 보면 가장 정확하게 알 수 있습니다.

## 참고 자료

- [Python: venv](https://docs.python.org/3/library/venv.html)
- [Flask: Installation](https://flask.palletsprojects.com/en/stable/installation/)
- [Firebase: Realtime Database 시작하기](https://firebase.google.com/docs/database/web/start)
- [Pyrebase4 (PyPI)](https://pypi.org/project/Pyrebase4/)
- 프로젝트 문서: [`apps/be/README.md`]({{ site.repo_url }}/blob/main/apps/be/README.md), [`apps/fe/README.md`]({{ site.repo_url }}/blob/main/apps/fe/README.md)
