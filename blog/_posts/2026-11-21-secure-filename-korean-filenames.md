---
layout: post
title: "한글 파일명을 올리면 확장자가 사라진다: secure_filename 디버깅"
type: Debugging
order: 2
date: 2026-11-21 10:00:00 +0900
author: BoughtIT 팀
summary: "'사진.JPG'가 'JPG'로, '리뷰 사진 1.png'가 '1.png'로 저장되는 원인을 Werkzeug 소스에서 찾고, uuid로 파일명을 새로 만들어 해결했습니다."
---

## 상황

BoughtIT에서는 상품과 리뷰에 사진을 올립니다. 요구사항은 "사진 파일은 서버에 저장하고, DB에는 파일 이름만 저장한다"였습니다. 그래서 업로드된 파일을 `static/uploads/` 폴더에 저장하고, 그 파일 이름을 Firebase Realtime Database의 `img_path` 같은 필드에 넣기로 했습니다.

Flask 문서의 업로드 예제는 파일을 저장하기 전에 Werkzeug의 `secure_filename()`으로 이름을 정리하라고 안내합니다. 사용자가 보낸 파일 이름을 그대로 쓰면 `../../app.py`처럼 다른 폴더를 가리키는 이름으로 서버 파일을 덮어쓸 수 있기 때문입니다. 처음 코드도 예제를 따라 이렇게 작성했습니다.

```python
filename = secure_filename(picture.filename)
picture.save(os.path.join(UPLOAD_DIR, filename))
```

`secure_filename()`이 정리한 이름으로 바로 저장하는 코드입니다. 영어 이름으로 테스트하면 문제가 없습니다.

## 문제

이 서비스의 사용자는 대부분 한국어 환경에서 사진을 올립니다. 휴대폰이나 PC에 있는 사진 이름도 `사진.JPG`, `리뷰 사진 1.png`처럼 한글인 경우가 많습니다. 한글 이름으로 시험해 보니 저장되는 이름이 이상했습니다. Python 셸에서 직접 확인한 결과입니다.

```python
>>> from werkzeug.utils import secure_filename
>>> secure_filename("사진.JPG")
'JPG'
>>> secure_filename("리뷰 사진 1.png")
'1.png'
>>> secure_filename("상품 사진 1.png")
'1.png'
>>> secure_filename("사진")
''
>>> secure_filename("ipad photo.jpg")
'ipad_photo.jpg'
```

결과를 보면 문제가 세 가지입니다.

1. **확장자가 사라진다.** `사진.JPG`가 `JPG`라는, 점도 확장자도 없는 이름이 됩니다. 확장자가 없으면 파일 종류를 이름으로 알 수 없습니다. 실제로 `mimetypes.guess_type("JPG")`는 `(None, None)`을 돌려줍니다.
2. **다른 파일이 같은 이름이 된다.** `리뷰 사진 1.png`와 `상품 사진 1.png`가 둘 다 `1.png`가 됩니다. 두 사람이 이런 사진을 올리면 나중 사진이 먼저 사진을 덮어써서, 앞사람의 리뷰에 다른 사람의 사진이 보이게 됩니다.
3. **이름이 아예 비어 버린다.** 확장자 없는 한글 이름 `사진`은 빈 문자열이 됩니다. 이대로 `os.path.join(UPLOAD_DIR, "")`에 저장하면 폴더 경로에 파일을 쓰려는 것이 되어 `IsADirectoryError`가 납니다.

## 원인 찾기: secure_filename 소스 읽기

`secure_filename()`이 무엇을 하는지 Werkzeug 소스(`werkzeug/utils.py`, 우리가 쓰는 3.1.x)를 직접 열어 봤습니다. 핵심 부분은 다음과 같습니다.

```python
filename = unicodedata.normalize("NFKD", filename)
# only keep ASCII chars
filename = filename.encode("ascii", "ignore").decode("ascii")

for sep in os.sep, os.path.altsep:
    if sep:
        filename = filename.replace(sep, " ")

# replace any whitespace with _
filename = "_".join(filename.split())
# only allow ASCII letters, numbers, and _.-
filename = _filename_ascii_strip_re.sub("", filename)
# remove surrounding ._, left behind after replacing slash in ../
filename = filename.strip("._")
```

한 줄씩 `사진.JPG`에 적용해 보면 원인이 보입니다.

1. `unicodedata.normalize("NFKD", ...)`는 문자를 분해합니다. 한글 음절 `사`는 초성 `ᄉ`(U+1109)와 중성 `ᅡ`(U+1161) 두 글자로 나뉩니다. 악센트가 붙은 라틴 문자(`é` → `e` + 악센트)를 ASCII로 바꾸기 위한 단계지만, 한글은 분해해도 ASCII가 아닙니다.
2. `encode("ascii", "ignore")`는 **ASCII가 아닌 글자를 모두 버립니다.** 여기서 한글이 전부 사라지고 `.JPG`만 남습니다.
3. 마지막 `strip("._")`는 이름 앞뒤의 점과 밑줄을 지웁니다. `../` 같은 경로 조각을 없애려는 단계인데, 이번에는 확장자 앞의 점까지 지워서 `JPG`가 됩니다.

즉 `secure_filename()`은 **"서버에 안전하게 저장할 수 있는 ASCII 이름"을 만드는 함수**이지, 원래 이름을 지키거나 이름이 겹치지 않게 해 주는 함수가 아니었습니다. 함수가 잘못된 것이 아니라 우리가 기대한 역할이 달랐던 것입니다.

## 해결: 파일 이름은 서버가 새로 만든다

해결 방향은 "사용자가 보낸 이름을 저장 이름으로 쓰지 않는다"였습니다. 저장 이름은 서버가 겹치지 않게 새로 만들고, 확장자만 원래 이름에서 가져옵니다. BE의 사진 저장 함수는 이렇게 바뀌었습니다.

```python
# apps/be/routes/product.py
def save_picture(picture):
    stem, extension = os.path.splitext(picture.filename)
    safe_stem = secure_filename(stem)
    filename = "_".join(part for part in (uuid.uuid4().hex, safe_stem) if part) + extension.lower()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    picture.save(os.path.join(UPLOAD_DIR, filename))
    return filename
```

- `os.path.splitext()`로 **원래 이름에서 확장자를 먼저 떼어 둡니다.** `secure_filename()`을 거치기 전이라 `.JPG`가 그대로 남고, `lower()`로 `.jpg`처럼 소문자로 맞춥니다.
- 이름 앞에 `uuid.uuid4().hex`(32자리 무작위 문자열)를 붙여서 **같은 이름의 파일이 와도 겹치지 않게** 합니다.
- 영어 이름이면 `secure_filename(stem)`이 남긴 부분을 뒤에 붙여 알아보기 쉽게 하고, 한글만 있는 이름이면 빈 문자열이므로 uuid와 확장자만 씁니다. 빈 문자열을 이어 붙이지 않도록 `if part`로 거릅니다.

확장자를 원래 이름에서 그대로 가져오면 `.exe` 같은 파일도 들어올 수 있습니다. 그래서 저장하기 **전에** 확장자와 크기를 먼저 검사합니다.

```python
PICTURE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PICTURE_MAX_BYTES = 5 * 1024 * 1024

def validate_picture(picture):
    if picture is None or not picture.filename:
        return "대표 사진을 올려 주세요."
    extension = os.path.splitext(picture.filename)[1].lower()
    if extension not in PICTURE_EXTENSIONS:
        return "JPG, PNG 파일만 올릴 수 있어요."
    picture.stream.seek(0, os.SEEK_END)
    size = picture.stream.tell()
    picture.stream.seek(0)
    if size > PICTURE_MAX_BYTES:
        return "5MB 이하의 사진만 올릴 수 있어요."
    return None
```

검사를 통과하지 못하면 오류 메시지를 돌려주고, 등록 화면이 그 메시지를 사진 칸 아래에 보여 줍니다. 크기를 잴 때는 스트림 끝으로 이동해 위치를 읽은 다음, 저장할 때를 위해 `seek(0)`으로 처음으로 되돌려 둡니다.

## 결과

같은 입력이 이제 이렇게 저장됩니다.

| 올린 파일 이름 | 이전 저장 이름 | 바꾼 뒤 저장 이름 |
| --- | --- | --- |
| `아이패드 사진.PNG` | `PNG` | `e73bf8e7afee4e2f9fd956dba6d1d8c1.png` |
| `리뷰 사진 1.png` | `1.png` (다른 사진과 겹침) | `<uuid>_1.png` |
| `사진` | `''` (저장 실패) | 확장자 검사에서 "JPG, PNG 파일만 올릴 수 있어요." |
| `ipad photo.jpg` | `ipad_photo.jpg` | `<uuid>_ipad_photo.jpg` |

아래는 실제 BE 코드의 `save_picture()`로 `아이패드 사진.PNG`를 저장한 뒤 상품 상세 화면에서 연 모습입니다. DB에는 `e73bf8e7afee4e2f9fd956dba6d1d8c1.png`라는 이름만 들어가고, 화면은 그 이름으로 `static/uploads/`에서 사진을 찾아 정상적으로 보여 줍니다.

![한글 이름 사진을 올린 상품 상세 화면]({{ '/assets/img/debug-detail.png' | relative_url }})
*원래 이름이 '아이패드 사진.PNG'인 사진. uuid로 바꾼 이름으로 저장되어 정상적으로 보입니다.*

## 배운 점

- `secure_filename()`은 **보안용**입니다. 경로 조작을 막아 주지만 원래 이름을 지키거나 이름이 겹치지 않게 해 주지는 않습니다. ASCII가 아닌 글자는 모두 지워진다는 점을 기억해야 합니다.
- 업로드 파일의 저장 이름은 **서버가 만드는 것이 안전합니다.** 원래 이름을 보여 줘야 하는 서비스라면 저장 이름과 별도로 DB에 원래 이름을 따로 저장하면 됩니다.
- 라이브러리 함수가 예상과 다르게 동작할 때는 문서보다 **소스를 직접 읽는 것**이 가장 빨랐습니다. 이번에도 10줄 남짓한 코드를 따라가는 것만으로 원인을 정확히 찾을 수 있었습니다.

## 참고 자료

- [Werkzeug: secure_filename](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.utils.secure_filename)
- [Flask: Uploading Files](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
- [Python: unicodedata.normalize](https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize), [uuid](https://docs.python.org/3/library/uuid.html)
- 프로젝트 코드: [`apps/be/routes/product.py`]({{ site.repo_url }}/blob/main/apps/be/routes/product.py)
