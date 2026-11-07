# FE (Flask 템플릿)

시안: `docs/벗잇 시안 마이 통합안 (1).html` · 규칙: `docs/fe_milestone.md`

## 미리보기 실행

BE 연동 전에 화면을 확인하는 개발용 서버입니다. Flask만 있으면 됩니다.

```bash
cd apps/fe
pip install flask
python preview.py
```

- 공통 컴포넌트: http://127.0.0.1:5002/dev/components (로그인 전/후 헤더 전환 링크 포함)
- 각 화면: `preview.py`의 `SCREENS`에 적힌 경로. 템플릿 파일을 만들면 바로 보입니다.

## 폴더 구조

```
apps/fe/
├─ preview.py                 개발용 미리보기 서버
├─ templates/
│  ├─ base.html               Tailwind CDN, 글꼴, 헤더·푸터, flash 메시지
│  ├─ components/             공통 매크로 (수정은 이다영, 필요하면 요청)
│  │  ├─ _header.html
│  │  ├─ _product_card.html   product_card, status_badge, won
│  │  ├─ _pagination.html     pagination
│  │  └─ _form_fields.html    button, chip, chip_group, input, textarea, select
│  ├─ product/ review/ auction/ chat/ wanted/ my/ auth/   도메인별 화면
│  └─ dev/                    미리보기 전용 페이지 (서비스 화면 아님)
└─ static/
   ├─ css/common.css          색상 토큰, 종이·도장 등 공통 스타일
   ├─ js/tailwind.config.js   Tailwind 색상·글꼴 토큰
   ├─ js/common.js            칩 그룹 동작
   └─ img/product/ review/ wanted/ common/
```

## 새 화면 만들기

```jinja
{% extends "base.html" %}
{% from "components/_form_fields.html" import button, input, chip_group %}
{% set active_tab = 'product' %}   {# 헤더에서 켜질 탭: product | wanted | review | chat | my #}

{% block title %}상품 목록 | BoughtIT{% endblock %}
{% block head %}<link rel="stylesheet" href="{{ url_for('static', filename='css/product.css') }}">{% endblock %}

{% block content %}
  <h1 class="page-title">지금 올라온 물건</h1>
  ...
{% endblock %}
```

매크로 인자는 각 파일 맨 위 주석에, 사용 예시는 `templates/dev/components.html`에 있습니다.

## 자주 쓰는 클래스

| 클래스 | 용도 |
| --- | --- |
| `panel` / `slip` | 아래가 톱니로 잘린 종이 (폼·목록 상자 / 카드) |
| `page-title` | 화면 제목 |
| `btn-primary` `btn-outline` `btn-quiet` | 버튼 |
| `chip` + `aria-pressed` | 칩 |
| `field` `label` `help` `error` | 입력칸, 라벨, 안내, 오류 |
| `tag-sale` `tag-hold` `tag-bid` `stamp` | 상태 뱃지, 도장 |
| `row` + `leader` | `가격 ······ 18,000원` 영수증 줄 |
| `tear` | 점선 구분선 |
| `num` | 가격·날짜 (고정폭 숫자, 굵게) |

색은 Tailwind 클래스로 씁니다: `bg-brand` `text-brandink` `text-muted` `bg-tint` `text-stamp` `bg-paper` 등.

## BE 연동 시 맞출 것

- 라우트 함수 이름은 `도메인_동작` (예: `product_list`, `auth_login`). 헤더가 `product_list` `wanted_list` `review_list` `chat_room` `my_index` `product_new` `auth_login` `auth_logout`을 `url_for`로 부릅니다.
- 로그인 여부는 `session['id']`로 판단합니다.
- 상품 카드의 판매 상태는 `sale_status`(`sale` | `hold` | `done`) 필드를 씁니다. DB의 `status`는 상품 상태(최상/상/중/하)라 따로 둡니다.
- 상품 이미지는 `img_path`(파일명)를 `static/uploads/`에서 찾습니다.
