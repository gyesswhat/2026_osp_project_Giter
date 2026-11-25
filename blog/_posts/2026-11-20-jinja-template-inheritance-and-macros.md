---
layout: post
title: "Jinja2 템플릿 상속과 매크로: 화면이 늘어나도 헤더와 버튼은 한 곳에서"
type: Concept
order: 1
date: 2026-11-20 10:00:00 +0900
author: BoughtIT 팀
summary: base.html 하나와 components/ 매크로로, 세 명이 나눠 만든 화면을 같은 모양으로 맞춘 방법을 정리합니다.
---

## 상황

BoughtIT 프론트엔드는 세 명이 화면을 나눠 맡았습니다. 한 사람은 상품 목록·상세·등록을, 한 사람은 리뷰와 경매를, 한 사람은 로그인·회원가입과 구해요를 만들었습니다. 화면은 모두 Flask가 그려 주는 HTML 템플릿이고, 템플릿 엔진은 Flask에 기본으로 들어 있는 **Jinja2**입니다.

화면을 나눌 때 가장 먼저 정해야 했던 것은 "공통 부분을 어떻게 맞출까"였습니다. 모든 화면에는 같은 헤더(로고, 상품·구해요·리뷰 탭, 로그인 버튼)와 푸터가 있고, 버튼·입력칸·칩(선택 버튼) 같은 부품도 화면마다 반복해서 나옵니다. 각자 HTML 파일에 이 마크업을 복사해 넣으면 처음에는 빠르지만, 버튼 색 하나를 바꿀 때 파일 여덟 개를 모두 고쳐야 하고, 누군가 한 곳을 빠뜨리면 화면마다 모양이 조금씩 달라집니다.

## 목표

- 모든 화면이 같은 헤더, 푸터, 글꼴, 색 토큰을 쓴다.
- 버튼, 칩, 입력칸은 한 곳에서 정의하고 화면에서는 가져다 쓰기만 한다.
- 화면 담당자는 자기 화면의 본문만 작성한다.

이 목표를 Jinja2의 세 가지 기능, **템플릿 상속**(`extends`, `block`), **include**, **매크로**(`macro`, `import`)로 해결했습니다. 이 글은 이 세 가지가 각각 무엇이고 언제 쓰는지를 프로젝트 코드로 설명합니다.

## 단계 1. 템플릿 상속: 뼈대는 base.html 하나

템플릿 상속은 "빈칸이 뚫린 뼈대"를 하나 만들고, 각 화면이 그 빈칸만 채우는 방식입니다. 빈칸의 이름이 `block`입니다. 아래는 `base.html`에서 block이 있는 부분만 추린 것입니다.

{% raw %}
```html
<!-- apps/fe/templates/base.html (일부) -->
<title>{% block title %}BoughtIT 벗잇{% endblock %}</title>
<link rel="stylesheet" href="{{ url_for('static', filename='css/common.css') }}">
{% block head %}{% endblock %}
</head>
<body class="min-h-screen">
  {% include "components/_header.html" %}
  <main class="mx-auto max-w-6xl px-4 pb-20 pt-8 sm:pt-10">
    {% block content %}{% endblock %}
  </main>
  <script src="{{ url_for('static', filename='js/common.js') }}"></script>
  {% block scripts %}{% endblock %}
</body>
```
{% endraw %}

block은 네 개입니다. `title`은 브라우저 탭 제목, `head`는 화면 전용 CSS, `content`는 본문, `scripts`는 화면 전용 JS 자리입니다. `title`처럼 block 안에 내용을 적어 두면, 화면이 그 block을 채우지 않을 때 기본값으로 쓰입니다.

각 화면은 첫 줄에서 `extends`로 뼈대를 고르고, 필요한 block만 다시 정의합니다. 상품 목록 화면은 이렇게 시작합니다.

{% raw %}
```html
<!-- apps/fe/templates/product/list.html (일부) -->
{% extends "base.html" %}
{% from "components/_form_fields.html" import chip_group, chip, select %}
{% from "components/_product_card.html" import product_card %}
{% set active_tab = 'product' %}

{% block title %}상품 목록 | BoughtIT{% endblock %}
{% block head %}<link rel="stylesheet" href="{{ url_for('static', filename='css/product.css') }}">{% endblock %}
{% block content %}
  <h1 class="page-title">지금 올라온 물건</h1>
  ...
{% endblock %}
```
{% endraw %}

이 화면 파일에는 헤더도 푸터도 없습니다. 그래도 렌더링 결과에는 `base.html`의 헤더와 푸터가 들어갑니다. 덕분에 헤더 디자인을 바꿀 때는 `base.html`과 헤더 파일만 고치면 됩니다. 맨 위의 `{% raw %}{% set active_tab = 'product' %}{% endraw %}`는 헤더에서 "상품" 탭을 켜는 데 쓰입니다. block 밖에 둔 `set`은 뼈대 쪽에서도 읽을 수 있어서, 화면이 "나는 상품 탭"이라고 알려 주는 용도로 썼습니다.

## 단계 2. include: 고정된 조각을 그대로 끼워 넣기

헤더처럼 인자 없이 항상 같은 모양인 조각은 `include`로 넣었습니다. 위 `base.html`의 `{% raw %}{% include "components/_header.html" %}{% endraw %}`가 그 예입니다. include된 템플릿은 **현재 컨텍스트를 그대로 받습니다.** 그래서 헤더 안에서 `session`으로 로그인 여부를 확인하고, 화면이 정한 `active_tab`으로 켜질 탭을 고를 수 있습니다.

## 단계 3. 매크로: 인자를 받는 부품

버튼이나 칩처럼 "모양은 같고 글자와 링크만 다른" 부품은 매크로로 만들었습니다. 매크로는 Jinja의 함수입니다. 아래는 버튼 매크로입니다.

{% raw %}
```html
<!-- apps/fe/templates/components/_form_fields.html (일부) -->
{% macro button(text, variant='primary', type='button', href=none, class='', disabled=false, attrs={}) -%}
  {%- set cls = 'btn-' ~ variant ~ (' ' ~ class if class else '') -%}
  {%- if href -%}
    <a href="{{ href }}" class="{{ cls }}"{{ _attrs(attrs) }}>{{ text }}</a>
  {%- else -%}
    <button type="{{ type }}" class="{{ cls }}"{% if disabled %} disabled{% endif %}{{ _attrs(attrs) }}>{{ text }}</button>
  {%- endif -%}
{%- endmacro %}
```
{% endraw %}

`href`를 넘기면 링크(`<a>`), 아니면 `<button>`을 그립니다. `variant`는 `primary`, `outline`, `quiet` 중 하나이고 CSS 클래스 이름으로 바뀝니다. 화면에서는 이렇게 한 줄로 씁니다.

{% raw %}
```html
{{ button('상품 등록', type='submit') }}
{{ button('취소', variant='quiet', href=url_for('product_list')) }}
```
{% endraw %}

매크로를 가장 크게 체감한 곳은 **칩 그룹**입니다. 상품 목록의 "판매 상태" 필터는 칩 세 개 중 하나를 고르는 UI인데, 고른 값이 폼으로 전송되려면 숨긴 `<input>`도 같이 있어야 하고, 접근성을 위해 `role="group"`과 라벨도 연결해야 합니다. 이것을 `chip_group` 매크로가 모두 그려 주고, 클릭 동작은 `common.js`가 `data-chip-group` 속성을 보고 처리합니다. 화면 담당자는 아래 한 줄만 씁니다.

{% raw %}
```html
{{ chip_group('sale_status', [('all', '전체'), ('sale', '판매중'), ('hold', '예약중')],
              selected=request.args.get('sale_status', 'all'), label='판매 상태', sr_label=true, required=true) }}
```
{% endraw %}

### 매크로를 쓸 때 알아 둘 점: import는 컨텍스트를 넘기지 않는다

include와 달리 `from ... import`로 가져온 매크로는 **기본적으로 현재 컨텍스트를 받지 않습니다.** 그래서 매크로 안에서는 화면에서 만든 변수를 바로 읽을 수 없고, 필요한 값은 인자로 넘겨야 합니다. `url_for`처럼 Flask가 전역으로 등록한 함수는 매크로 안에서도 쓸 수 있습니다. 화면 변수가 매크로 안에서 비어 보인다면 대부분 이 차이 때문입니다. 반대로 생각하면 장점도 있습니다. 필요한 값을 모두 인자로 받으니, 매크로가 어떤 값에 의존하는지 시그니처만 봐도 알 수 있습니다. 상품 카드 매크로 `product_card(product, href=none, image=none, show_sale=false)`가 그 예입니다.

## 단계 4. 자주 걸리는 함정: for 안의 set은 밖으로 나오지 않는다

상품 목록에서는 주소의 가격 필터 값(`price_min`, `price_max`)이 가격 슬라이더의 몇 번째 칸인지 찾아야 합니다. 눈금 목록을 for로 돌면서 일치하는 칸 번호를 변수에 담으면 될 것 같지만, 그렇게 하면 for가 끝나는 순간 값이 처음 값으로 돌아갑니다. Jinja에서 **for 블록 안의 `set`은 그 블록 안에서만 유효**하기 때문입니다. Python의 for와 다르게 동작해서 놓치기 쉬운 부분입니다. 해결 방법은 `namespace` 객체에 값을 담는 것입니다.

{% raw %}
```html
{% set ns = namespace(pmin=0, pmax=last_step) %}
{% for v in price_steps %}
  {% if q_min | string == v | string %}{% set ns.pmin = loop.index0 %}{% endif %}
  {% if q_max | string == v | string %}{% set ns.pmax = loop.index0 %}{% endif %}
{% endfor %}
```
{% endraw %}

`ns.pmin`처럼 namespace의 속성을 바꾸면 for 밖에서도 바뀐 값이 남습니다.

## 결과

아래는 매크로를 한곳에 모아 확인하는 개발용 페이지입니다. 버튼, 상태 뱃지, 칩, 입력칸이 모두 `components/` 매크로 하나에서 나옵니다. 새 부품을 만들면 이 페이지에 먼저 올려 보고 화면에 가져다 썼습니다.

![공통 컴포넌트 확인 페이지]({{ '/assets/img/concept-components.png' | relative_url }})
*개발용 페이지 `/dev/components`. 버튼, 뱃지, 도장, 칩, 입력칸이 모두 매크로로 그려집니다.*

상품 목록 화면도 헤더와 푸터는 `base.html`에서, 필터 칩과 상품 카드는 매크로에서 가져옵니다.

![상품 목록 화면]({{ '/assets/img/concept-list.png' | relative_url }})
*상품 목록. 헤더의 "상품" 탭은 화면이 정한 `active_tab` 값으로 켜집니다.*

## 배운 점

세 기능은 쓰임새가 분명히 다릅니다.

| 기능 | 언제 쓰나 | 컨텍스트 |
| --- | --- | --- |
| `extends` + `block` | 모든 화면이 공유하는 뼈대 | 화면과 뼈대가 같은 컨텍스트 |
| `include` | 인자 없이 항상 같은 조각 (헤더) | 현재 컨텍스트를 그대로 받음 |
| `macro` + `import` | 인자로 모양이 바뀌는 부품 (버튼, 칩, 카드) | 기본으로 받지 않음, 인자로 넘김 |

팀 규칙으로는 "두 화면 이상에서 쓰는 조각만 `components/`에 매크로로 둔다"를 정했습니다. 한 화면에서만 쓰는 부분까지 매크로로 빼면 오히려 코드를 찾기 어려워졌기 때문입니다. 공통 부분이 한 곳에 있으니 리뷰할 때도 "이 화면이 버튼을 직접 그리고 있는지"만 보면 되어 편했습니다.

## 참고 자료

- [Jinja Template Designer Documentation: Template Inheritance](https://jinja.palletsprojects.com/en/stable/templates/#template-inheritance)
- [Jinja: Macros](https://jinja.palletsprojects.com/en/stable/templates/#macros), [Import Context Behavior](https://jinja.palletsprojects.com/en/stable/templates/#import-visibility)
- [Jinja: Assignments와 namespace](https://jinja.palletsprojects.com/en/stable/templates/#assignments)
- [Flask: Templates](https://flask.palletsprojects.com/en/stable/templating/)
- 프로젝트 코드: [`base.html`]({{ site.repo_url }}/blob/main/apps/fe/templates/base.html), [`_form_fields.html`]({{ site.repo_url }}/blob/main/apps/fe/templates/components/_form_fields.html)
