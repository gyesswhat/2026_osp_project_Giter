# BoughtIT 기술 블로그

11주차 팀 과제(Web Application Practice 3)로 만든 기술 블로그입니다. GitHub Pages가 기본으로 지원하는 Jekyll 형식이라 따로 빌드할 필요 없이 올리면 사이트가 됩니다. 이 README는 사이트에 포함되지 않습니다(`_config.yml`의 `exclude`).

## 구성

```
blog/
├─ _config.yml          사이트 설정. baseurl을 올리는 저장소에 맞게 바꾼다
├─ index.html           메인 페이지. 글 5편으로 링크한다 (order 순서)
├─ _layouts/
│  ├─ default.html      헤더, 푸터
│  └─ post.html         글 화면, 이전·다음 글 링크
├─ _posts/              글 5편 (Markdown)
└─ assets/
   ├─ css/style.css     서비스와 같은 색 토큰
   └─ img/              글에 넣은 스크린샷
```

| 순서 | 종류 | 글 |
| --- | --- | --- |
| 1 | Concept | Jinja2 템플릿 상속과 매크로 |
| 2 | Debugging | 한글 파일명과 secure_filename |
| 3 | Guide | Flask + Pyrebase4 + Firebase 로컬 실행 |
| 4 | Explanation | 상품 목록의 검색·필터·정렬·페이지 |
| 5 | Explanation | 가격 제안 받기(경매) 기능 |

## 글 쓰기 규칙

- 파일 이름은 `YYYY-MM-DD-영문-슬러그.md`이고, 주소는 `/posts/영문-슬러그/`가 됩니다.
- 앞부분(front matter)에 `layout: post`, `title`, `type`(Concept, Debugging, Tip, Guide, Explanation), `order`, `date`, `summary`를 씁니다.
- **날짜를 미래로 쓰지 않습니다.** Jekyll은 기본 설정에서 미래 날짜의 글을 사이트에 올리지 않습니다.
- Jinja 코드처럼 `{{ }}`, `{% %}`가 들어간 코드 블록은 `{% raw %}`와 `{% endraw %}`로 감쌉니다. 감싸지 않으면 Jekyll이 Liquid 문법으로 해석해서 빌드가 깨집니다.
- 이미지는 `assets/img/`에 두고 `![설명]({{ '/assets/img/파일.png' | relative_url }})`로 넣습니다. 바로 아래 줄에 `*설명*`을 쓰면 캡션으로 보입니다.

## GitHub Pages로 올리기

`_config.yml`의 `baseurl`만 올리는 곳에 맞추면 됩니다.

### A. 팀 저장소에 올리기

주소: `https://gyesswhat.github.io/2026_osp_project_Giter/` (`baseurl: "/2026_osp_project_Giter"`, 지금 설정)

Pages 설정은 저장소 관리자만 바꿀 수 있습니다. 관리자가 **Settings → Pages → Build and deployment → Source**를 **GitHub Actions**로 바꾸고, `blog/` 폴더를 빌드해 배포하는 워크플로를 추가합니다. (Pages가 브랜치에서 바로 배포할 수 있는 폴더는 루트와 `/docs`뿐인데, 이 저장소는 `/docs`를 `.gitignore`에 넣어 두었기 때문입니다.)

### B. 개인 저장소에 따로 올리기

주소: `https://<아이디>.github.io/<저장소이름>/`

1. GitHub에서 공개 저장소를 새로 만듭니다.
2. `blog/` 폴더 안의 내용을 그 저장소의 루트에 복사합니다.
3. `_config.yml`의 `baseurl`을 `"/<저장소이름>"`으로 바꿉니다.
4. 커밋하고 푸시한 뒤 **Settings → Pages → Source: Deploy from a branch**, 브랜치 `main`, 폴더 `/ (root)`를 고릅니다.
5. 1~2분 뒤 Settings → Pages 위쪽에 사이트 주소가 나타납니다.
