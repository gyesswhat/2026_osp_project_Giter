---
layout: post
title: "상품 목록 페이지는 어떻게 동작하나: 검색·필터·정렬·페이지를 URL 쿼리 하나로"
type: Explanation
order: 4
date: 2026-11-23 10:00:00 +0900
author: BoughtIT 팀
summary: BoughtIT의 첫 화면인 상품 목록이 검색어, 판매 상태, 거래 방식, 가격, 정렬, 페이지를 어떻게 주고받고 처리하는지 FE와 BE 코드로 설명합니다.
---

## 상황

상품 목록은 BoughtIT에 들어오면 가장 먼저 보이는 화면이자 가장 많이 쓰는 화면입니다. 물건이 몇 개 없을 때는 최신순으로 늘어놓기만 해도 충분하지만, 물건이 늘어나면 사용자는 "판매 중인 것만", "만 원 이하만", "가격 제안을 받는 물건만"처럼 원하는 것만 골라 보고 싶어 합니다.

그래서 상품 목록에는 다음 기능을 넣었습니다.

- **검색**: 상품 이름에 검색어가 들어간 상품만
- **필터**: 판매 상태(전체·판매중·예약중), 거래 방식(전체·가격 정해진 물건·가격 제안 받는 중), 가격 범위
- **정렬**: 최신순, 인기순(찜 많은 순), 낮은 가격순, 높은 가격순
- **페이지**: 한 페이지에 8개씩

## 목표

이 기능들을 만들 때 정한 원칙은 하나였습니다. **"지금 보고 있는 목록의 상태가 모두 URL에 들어 있어야 한다."** 예를 들어 판매 중인 경매 상품을 높은 가격순으로 본 2페이지는 이런 주소가 됩니다.

```text
/?sale_status=sale&kind=bid&sort=high&page=2
```

이렇게 하면 주소를 복사해 친구에게 보내도 같은 목록이 보이고, 브라우저의 뒤로 가기도 자연스럽게 동작하며, 새로고침해도 필터가 풀리지 않습니다. 서버 입장에서도 요청 하나만 보면 무엇을 보여 줘야 하는지 알 수 있습니다.

## 단계 1. FE: 필터 전체를 GET 폼 하나로

필터 영역 전체가 `method="get"`인 폼 하나입니다. GET 폼은 제출할 때 입력값을 `?이름=값` 형태로 주소에 붙이므로, 위 원칙을 그대로 만족합니다.

{% raw %}
```html
<form id="productFilter" method="get" action="{{ url_for('product_list') }}" role="search">
  <input id="q" name="q" type="search" class="field" placeholder="상품 이름으로 검색"
         value="{{ request.args.get('q', '') }}">
  {{ select('sort', [('new', '최신순'), ('like', '인기순'), ('low', '낮은 가격순'), ('high', '높은 가격순')],
            selected=request.args.get('sort', 'new'), label='정렬', sr_label=true, attrs={'data-autosubmit': true}) }}
  {{ chip_group('sale_status', [('all', '전체'), ('sale', '판매중'), ('hold', '예약중')],
                selected=request.args.get('sale_status', 'all'), label='판매 상태', sr_label=true, required=true) }}
  ...
</form>
```
{% endraw %}

각 입력칸의 현재 값은 `request.args`(지금 주소의 쿼리)에서 다시 읽어 채웁니다. 그래서 페이지가 새로 그려져도 사용자가 고른 필터가 그대로 보입니다. 판매 상태 칩은 `chip_group` 매크로가 그리고, 고른 값은 숨긴 `<input name="sale_status">`에 담겨 함께 전송됩니다.

가격 필터는 손잡이가 두 개인 슬라이더입니다. 슬라이더 자체는 "몇 번째 눈금인지"만 알고 있으므로, JS가 칸 번호를 원 단위 금액으로 바꿔 숨긴 입력칸 `price_min`, `price_max`에 넣습니다. 눈금은 `[0, 5000, 10000, 20000, 30000, 50000, 100000, 200000, 300000, 500000]`이고, 마지막 칸은 "상한 없음"입니다. 균일한 간격이 아니라 중고 물건 가격대에 맞춰 낮은 금액을 촘촘하게 나눴습니다.

## 단계 2. FE: 고르는 즉시 검색하고, 빈 값은 주소에서 뺀다

"필터 적용" 버튼을 따로 누르게 하면 한 단계가 늘어나므로, 칩이나 정렬을 바꾸면 바로 폼을 제출하도록 했습니다.

```js
// apps/fe/static/js/product.js (일부)
const submit = () => (form.requestSubmit ? form.requestSubmit() : form.submit());

form.addEventListener('chipchange', (e) => {
  if (e.target.closest('[data-chip-group]')) submit();
});
form.querySelectorAll('[data-autosubmit]').forEach((el) => el.addEventListener('change', submit));

// 빈 값과 '전체'는 주소에서 빼서 링크를 짧게 둔다
form.addEventListener('submit', () => {
  form.querySelectorAll('[name]').forEach((el) => {
    if (el.value === '' || ((el.name === 'sale_status' || el.name === 'kind') && el.value === 'all')
        || (el.name === 'sort' && el.value === 'new')) {
      el.disabled = true;
    }
  });
});
```

`chipchange`는 칩 그룹이 값이 바뀔 때 보내는 이벤트입니다. 제출 직전에는 비어 있거나 기본값인 칸을 `disabled`로 바꿉니다. **disabled인 입력칸은 폼 전송에서 빠진다**는 HTML 규칙을 이용한 것으로, 덕분에 아무것도 고르지 않은 상태의 주소는 `/?q=&sort=new&sale_status=all&...`이 아니라 그냥 `/`가 됩니다. 가격 슬라이더는 드래그하는 동안 계속 검색하지 않도록, 손을 뗄 때 발생하는 `change` 이벤트에서만 제출합니다. JS가 꺼진 환경을 위해 `<noscript>` 안에 "필터 적용" 버튼도 남겨 두었습니다.

## 단계 3. BE: 쿼리를 읽어 거르고, 정렬하고, 자른다

BE의 `product_list`는 세 단계로 목록을 만듭니다.

```python
# apps/be/routes/product.py
@app.route("/")
def product_list():
    products = filter_products(load_products(), request.args)
    sort_products(products, request.args.get("sort", "new"))

    total_pages = max(1, math.ceil(len(products) / PAGE_SIZE))
    page = min(max(1, to_int(request.args.get("page"), 1)), total_pages)
    return render_template(
        "product/list.html",
        products=products[(page - 1) * PAGE_SIZE : page * PAGE_SIZE],
        total=len(products),
        page=page,
        total_pages=total_pages,
    )
```

전체 상품을 읽어 조건에 맞게 거르고(`filter_products`), 정렬한 다음(`sort_products`), 현재 페이지에 해당하는 8개만 잘라서 템플릿에 넘깁니다. `page`는 `max(1, …)`와 `min(…, total_pages)`로 범위를 제한합니다. 사용자가 주소를 `?page=99`나 `?page=abc`로 바꿔도 오류 없이 마지막 페이지나 첫 페이지를 보여 줍니다. `to_int()`는 숫자로 바꿀 수 없으면 기본값을 돌려주는 작은 함수입니다.

필터는 조건마다 목록을 한 번씩 거르는 단순한 구조입니다.

```python
def filter_products(products, args):
    query = args.get("q", "").strip().lower()
    sale_status = args.get("sale_status", "all")
    kind = args.get("kind", "all")
    price_min = to_int(args.get("price_min"))
    price_max = to_int(args.get("price_max"))

    products = [p for p in products if p["sale_status"] != "done"]
    if query:
        products = [p for p in products if query in p["name"].lower()]
    if sale_status in ("sale", "hold"):
        products = [p for p in products if p["sale_status"] == sale_status]
    if kind in ("fixed", "bid"):
        products = [p for p in products if p["kind"] == kind]
    if price_min is not None:
        products = [p for p in products if to_int(p["price"], 0) >= price_min]
    if price_max is not None:
        products = [p for p in products if to_int(p["price"], 0) <= price_max]
    return products
```

몇 가지 정한 규칙이 코드에 드러나 있습니다.

- **거래 완료(`done`) 상품은 항상 뺍니다.** 이미 팔린 물건은 목록에서 볼 이유가 없기 때문입니다.
- `sale_status`와 `kind`는 **허용한 값일 때만** 거릅니다. 주소에 이상한 값이 들어와도 "전체"로 처리됩니다.
- 검색은 대소문자를 구분하지 않도록 양쪽을 `lower()`로 맞춥니다.
- Firebase에서 가격이 문자열로 올 수도 있어서 `to_int(p["price"], 0)`으로 숫자로 바꿔 비교합니다.

정렬은 `sort` 값에 따라 기준만 바꿉니다.

```python
def sort_products(products, sort):
    if sort == "like":
        products.sort(key=lambda p: p["likes"], reverse=True)
    elif sort in ("low", "high"):
        products.sort(key=lambda p: to_int(p["price"], 0), reverse=(sort == "high"))
    else:
        products.sort(key=lambda p: p.get("created_at", ""), reverse=True)
```

최신순은 등록 시각 문자열(`2026-11-20T15:00:00+09:00` 형식)로 정렬합니다. ISO 8601 형식은 문자열로 비교해도 시간 순서와 같아서 날짜로 바꾸지 않고 그대로 비교할 수 있습니다.

## 단계 4. 페이지 링크에 필터를 함께 싣기

페이지 번호 링크를 `?page=2`로만 만들면 2페이지로 넘어가는 순간 필터가 풀립니다. 그래서 템플릿에서 지금 쿼리 중 `page`를 뺀 값들을 모아 페이지네이션 매크로에 넘깁니다.

{% raw %}
```html
{% set filter_args = {} %}
{% for k in ['q', 'sort', 'sale_status', 'kind', 'price_min', 'price_max'] if request.args.get(k) %}
  {% set _ = filter_args.update({k: request.args.get(k)}) %}
{% endfor %}
...
{{ pagination(page | default(1), total_pages | default(1), 'product_list', **filter_args) }}
```
{% endraw %}

페이지네이션 매크로는 받은 값을 `url_for('product_list', page=n, **args)`에 그대로 넣어 링크를 만듭니다. 결과적으로 모든 페이지 링크가 지금 필터를 유지합니다.

## 결과

필터를 고르지 않은 첫 화면입니다. 검색창과 정렬, 판매 상태·거래 방식 칩, 가격 슬라이더가 한 상자에 있고, 그 아래에 상품 카드가 4열로 놓입니다.

![상품 목록의 필터 영역]({{ '/assets/img/list-filter.png' | relative_url }})
*주소가 `/`인 기본 상태. 전체 12개 상품이 최신순으로 보입니다.*

"가격 제안 받는 중" 칩과 "높은 가격순"을 고르면 주소가 `/?kind=bid&sort=high`로 바뀌고, 경매 상품만 최고 제안가가 높은 순서로 남습니다.

![경매 상품만 높은 가격순으로 본 목록]({{ '/assets/img/list-bid-high.png' | relative_url }})
*`/?kind=bid&sort=high`. 칩과 정렬 선택이 주소에서 다시 읽혀 그대로 표시됩니다.*

상품이 8개를 넘으면 아래에 페이지 번호가 생깁니다. 현재 페이지는 파란 칸으로 표시되고, 마지막 페이지에서는 "다음"이 비활성화됩니다.

![페이지 번호]({{ '/assets/img/list-pagination.png' | relative_url }})
*2페이지. 판매 중인 물건, 예약 중인 물건, 경매 물건이 함께 보입니다.*

## 배운 점

- **상태를 URL에 두면** 공유, 뒤로 가기, 새로고침이 따로 코드를 쓰지 않아도 해결됩니다. 서버도 요청 하나만 보고 화면을 그릴 수 있어 단순해집니다.
- 쿼리 값은 사용자가 마음대로 바꿀 수 있으므로, BE에서는 **허용한 값만 쓰고 숫자는 안전하게 변환**해야 합니다. 범위를 벗어난 페이지도 오류 대신 가까운 페이지로 보내는 편이 친절합니다.
- 지금은 전체 상품을 읽은 뒤 Python에서 거르고 자릅니다. 상품 수가 적은 지금은 충분하지만, 상품이 많아지면 Firebase 쿼리(`order_by_child` 등)로 DB에서 먼저 거르는 방식으로 바꿔야 합니다.

## 참고 자료

- [MDN: `<form>`의 method 속성](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/form#method)
- [MDN: disabled 속성과 폼 전송](https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/disabled)
- [Flask: The Request Object (`request.args`)](https://flask.palletsprojects.com/en/stable/api/#flask.Request.args)
- [Python: Sorting Techniques](https://docs.python.org/3/howto/sorting.html)
- 프로젝트 코드: [`product.py`]({{ site.repo_url }}/blob/main/apps/be/routes/product.py), [`list.html`]({{ site.repo_url }}/blob/main/apps/fe/templates/product/list.html), [`product.js`]({{ site.repo_url }}/blob/main/apps/fe/static/js/product.js)
