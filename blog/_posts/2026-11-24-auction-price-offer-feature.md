---
layout: post
title: "가격 제안 받기(경매) 기능은 어떻게 동작하나: 등록부터 목록 카드, 제안까지"
type: Explanation
order: 5
date: 2026-11-24 10:00:00 +0900
author: BoughtIT 팀
summary: 가격을 정하지 않고 올린 물건에 정해진 기간 동안 금액 제안을 받는 BoughtIT의 팀 특화 기능을, 데이터 구조와 세 화면(등록, 목록 카드, 경매 상세)의 코드로 설명합니다.
---

## 상황

중고 거래를 하다 보면 "얼마에 팔아야 할지 모르겠다"는 물건이 있습니다. 거의 새것인 아이패드나 단종된 필름 카메라처럼 시세를 알기 어려운 물건은, 가격을 낮게 정하면 손해이고 높게 정하면 팔리지 않습니다.

그래서 BoughtIT에는 **가격 제안 받기** 기능을 넣었습니다. 판매자는 가격 없이 물건을 올리고 기간(1·3·5·7일)을 정합니다. 그동안 구매자들이 금액을 제안하고, 마감되면 판매자가 가장 높은 제안을 보고 거래할지 정합니다. 일반적인 경매와 달리 **최고가에 자동으로 낙찰되지 않고 판매자가 마지막에 결정한다**는 점이 다릅니다. 금액이 아쉬우면 거래하지 않아도 됩니다.

## 목표

이 기능은 세 화면에 걸쳐 있습니다.

1. **상품 등록**: 가격 정하는 방식을 고르고, 제안을 받을 기간을 정한다.
2. **상품 목록 카드**: 경매 상품은 남은 시간, 최고 제안가, 제안 수를 보여 준다.
3. **경매 상세**: 남은 시간이 실시간으로 줄어들고, 최고가보다 5,000원 이상 높은 금액만 제안할 수 있다.

## 단계 1. 데이터 구조: 상품에 kind 하나, 경매 정보는 따로

DB 설계(`schema.dbml`)에서는 상품(`products`)에 `kind` 필드를 두어 `fixed`(가격 정해서 올리기)와 `bid`(가격 제안 받기)를 구분했습니다. 경매에만 필요한 값은 `auctions` 노드에 따로 둡니다.

```text
/products/{상품명}   kind: "bid", price: 지금 최고 제안가(제안이 없으면 0), ...
/auctions/{상품명}   duration_days, end_at, top_price, bid_count, decision
/bids/{상품명}/{push 키}   bidder, price, created_at
```

`end_at`(마감 시각)은 `2026-11-25T14:30:00+09:00`처럼 **시간대가 붙은 ISO 8601 문자열**로 저장하기로 했습니다. 이 형식은 Python과 JavaScript가 모두 바로 해석할 수 있어서, 남은 시간을 화면에서 계산하기 좋습니다. `top_price`와 `bid_count`는 목록 카드에서 매번 제안 목록을 세지 않으려고 따로 들고 있는 값입니다. 마감 여부는 스케줄러 없이 **요청이 올 때 현재 시각과 `end_at`을 비교**해서 정합니다.

## 단계 2. 등록 화면: 방식에 맞는 칸만 보내기

등록 화면에서는 가격 정하는 방식을 카드 두 개 중에서 고릅니다. 시안에서는 버튼으로 그렸지만, 실제로는 **기본 라디오 버튼(`<input type="radio">`)을 카드 모양으로 꾸몄습니다.** 라디오 버튼이라 JS 없이도 값이 전송되고, 키보드 방향키로도 고를 수 있습니다.

{% raw %}
```html
<!-- apps/fe/templates/product/new.html (설명에 필요한 부분만 줄임) -->
<div class="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-labelledby="kind-label" aria-describedby="kind-msg">
  {% for value, title, desc in kinds %}
    <label class="mode-card cursor-pointer rounded-sm border border-dashed border-muted p-4">
      <input type="radio" name="kind" value="{{ value }}" class="sr-only" {% if value == kind %}checked{% endif %}>
      <span class="block font-bold">{{ title }}</span>
      <span class="mt-1 block text-sm text-muted">{{ desc }}</span>
    </label>
  {% endfor %}
</div>
```
{% endraw %}

고른 카드는 CSS `:has()` 선택자로 강조합니다. `.mode-card:has(input:checked)`는 "체크된 라디오를 안에 가진 카드"를 뜻해서, JS로 클래스를 바꾸지 않아도 됩니다.

방식에 따라 보이는 칸이 다릅니다. "가격 정해서 올리기"면 가격 입력칸이, "가격 제안 받기"면 기간 칩과 안내 상자가 보입니다. 이때 숨긴 칸은 **`disabled`로 바꿔서 폼 전송에서 빠지게** 했습니다.

```js
// apps/fe/static/js/product.js (일부)
function renderKind() {
  const kind = kindOf();
  form.querySelectorAll('[data-kind-box]').forEach((box) => {
    const on = box.dataset.kindBox === kind;
    box.hidden = !on;
    box.querySelectorAll('input, button').forEach((el) => { el.disabled = !on; });
  });
  if (submitBtn) submitBtn.textContent = kind === 'bid' ? '제안 받기 시작' : '상품 등록';
  renderDuration();
}
```

숨기기만 하고 disabled로 바꾸지 않으면, 사용자가 가격을 입력했다가 "가격 제안 받기"로 바꾼 경우 가격 값이 그대로 서버로 갑니다. disabled로 바꾸면 경매 상품은 `kind=bid`와 `duration`만, 고정가 상품은 `kind=fixed`와 `price`만 보내게 되어 서버가 헷갈릴 일이 없습니다. 기간 칩을 바꾸면 `renderDuration()`이 "마감 12.01 (화) 10:05"처럼 예상 마감 시각을 보여 줍니다. 실제 마감 시각은 서버가 등록 시각에 기간을 더해 정합니다.

## 단계 3. 목록 카드: 같은 카드 매크로에서 경매만 다르게

상품 카드는 모든 상품이 같은 `product_card` 매크로로 그립니다. 경매 상품일 때만 세 군데가 달라집니다.

첫째, **카드를 누르면 가는 곳**입니다. 고정가 상품은 상품 상세로, 진행 중인 경매는 경매 상세로, 마감된 경매는 경매 마감 화면으로 갑니다.

{% raw %}
```html
{% macro product_url(product) -%}
  {%- if product.get('kind') == 'bid' -%}
    {{ url_for('auction_end' if product.get('closed') else 'auction_detail', name=product.name) }}
  {%- else -%}
    {{ url_for('product_detail', name=product.name) }}
  {%- endif -%}
{%- endmacro %}
```
{% endraw %}

경로를 문자열로 쓰지 않고 `url_for`에 라우트 이름만 넘긴 덕분에, 개발 중에 경매 상세 경로가 `/auction/detail?name=…`에서 `/auction/detail/<상품명>`으로 바뀌었을 때도 이 매크로는 고치지 않았습니다. 그리고 `kind`, `closed` 같은 경매 필드는 고정가 상품에는 없으므로 `product.get()`으로 읽습니다. `product.bid_count | int`처럼 없는 속성을 바로 숫자로 바꾸면 Jinja가 `UndefinedError`를 내서 목록 페이지 전체가 깨지기 때문입니다.

둘째, **가격 줄**입니다. 제안이 있으면 "최고 제안 435,000원", 없으면 "첫 제안 대기"를 보여 줍니다. 제안이 없는 경매 상품의 `price`는 0이라서, 이 처리가 없으면 "0원"으로 보여 공짜 물건처럼 오해할 수 있습니다.

셋째, **남은 시간 태그**입니다. 서버가 "2일 13시간 남음" 같은 문자열을 만들어 넘기면, 페이지를 오래 열어 두었을 때 시간이 맞지 않게 됩니다. 그래서 서버는 `end_at`만 `data-end-at` 속성에 넣고, 남은 시간은 브라우저가 계산해 1분마다 갱신합니다.

```js
// apps/fe/static/js/common.js (일부)
function auctionLeftText(ms) {
  if (ms <= 0) return '제안 마감';
  const m = Math.floor(ms / 60000);
  const d = Math.floor(m / 1440);
  const h = Math.floor((m % 1440) / 60);
  if (d) return `${d}일 ${h}시간 남음`;
  if (h) return `${h}시간 ${m % 60}분 남음`;
  return `${Math.max(1, m % 60)}분 남음`;
}

function renderAuctionLeft() {
  document.querySelectorAll('[data-end-at]').forEach((el) => {
    const end = Date.parse(el.dataset.endAt);
    if (!Number.isNaN(end)) el.textContent = auctionLeftText(end - Date.now());
  });
}
```

`Date.parse()`는 ISO 8601 문자열을 밀리초로 바꿔 줍니다. 마감까지 남은 밀리초를 분으로 바꾼 뒤, 하루(1440분) 이상이면 "일·시간", 한 시간 이상이면 "시간·분", 그보다 적으면 "분"으로 보여 줍니다. 1분 미만일 때 "0분 남음"이 되지 않도록 `Math.max(1, …)`로 최소 1분을 보장합니다. JS가 꺼져 있으면 서버가 미리 넣어 둔 "11.25 14:30 마감"이 그대로 보입니다.

## 단계 4. 경매 상세: 실시간 카운트다운과 최소 금액 검사

경매 상세에서는 남은 시간을 1초마다 `1일 07:54:56`처럼 보여 주고, 제안 금액을 입력받습니다. 제안 규칙은 **지금 최고가보다 5,000원 이상 높아야 한다**입니다. "최고가 +5,000", "+10,000", "+30,000" 버튼을 누르면 그 금액이 입력칸에 채워지고, 제출할 때 금액을 한 번 더 검사합니다.

```js
// apps/fe/static/js/auction_detail.js (일부)
form.addEventListener("submit", (event) => {
  event.preventDefault();

  const rawValue = input.value.replace(/,/g, "").trim();
  const amount = Number(rawValue);

  if (!/^\d+$/.test(rawValue) || !Number.isSafeInteger(amount)) {
    message.textContent = "제안 금액을 숫자로 입력해 주세요.";
    return;
  }
  if (amount < minimumBid) {
    message.textContent = `최소 ${minimumBid.toLocaleString("ko-KR")}원 이상 제안해야 합니다.`;
    return;
  }
  input.value = String(amount);
  form.submit();
});
```

먼저 제출을 막고(`preventDefault`), 쉼표를 뺀 값이 숫자인지, 최소 금액(`최고가 + 5,000`) 이상인지 확인합니다. 통과하면 쉼표 없는 숫자로 바꿔 실제로 제출합니다. 다만 브라우저 검사는 사용자 편의를 위한 것일 뿐이고, 사용자가 JS를 끄거나 요청을 직접 보내면 건너뛸 수 있습니다. 그래서 같은 규칙(본인 상품 금지, 마감 후 금지, 최소 금액)을 **서버에서도 다시 검사하도록 BE 작업이 진행 중**입니다.

## 결과

등록 화면에서 "가격 제안 받기"를 고르고 7일을 선택한 모습입니다. 가격 칸이 사라지고 기간 칩, 예상 마감 시각, 진행 방식 안내가 나타납니다.

![가격 제안 받기를 고른 등록 화면]({{ '/assets/img/auction-new.png' | relative_url }})
*고른 카드는 실선 테두리와 옅은 파란 바탕으로 강조됩니다. 제출 버튼 문구도 "제안 받기 시작"으로 바뀝니다.*

목록에서는 경매 상품마다 남은 시간 태그와 최고 제안가가 보입니다. 제안이 없는 상품은 "첫 제안 대기", 마감된 상품은 "제안 마감"으로 표시됩니다.

![목록의 경매 카드]({{ '/assets/img/auction-cards.png' | relative_url }})
*왼쪽부터 진행 중(제안 7건), 진행 중(제안 12건), 첫 제안 대기, 제안 마감.*

경매 상세에서는 최고 제안가와 남은 시간이 위에, 제안 입력 폼이 아래에 있습니다.

![경매 상세 화면]({{ '/assets/img/auction-detail.png' | relative_url }})
*남은 시간은 1초마다 줄어들고, 입력칸 안내에 최소 제안 금액(440,000원)이 보입니다.*

## 배운 점

- 시간처럼 계속 바뀌는 값은 **변하지 않는 기준값(`end_at`)만 저장하고, 보여 줄 때 계산**하는 편이 정확합니다. 저장 형식을 ISO 8601로 정해 두니 Python, Jinja, JavaScript가 같은 값을 문제없이 다뤘습니다.
- 폼에서 숨긴 칸은 **`disabled`로 바꿔야 전송에서 빠집니다.** `hidden`은 보이지 않게만 할 뿐 값은 그대로 갑니다.
- 공통 카드 매크로에 기능을 더할 때는, 그 필드가 없는 기존 데이터에서도 깨지지 않는지 꼭 확인해야 합니다. 실제로 제안 수 필드가 없는 고정가 상품 때문에 목록 전체가 깨질 뻔했고, `get()`으로 읽어서 해결했습니다.
- 브라우저 검사는 편의, **서버 검사는 규칙**입니다. 같은 규칙을 양쪽에 두어야 합니다.

## 참고 자료

- [MDN: `Date.parse()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/parse)
- [MDN: CSS `:has()`](https://developer.mozilla.org/en-US/docs/Web/CSS/:has)
- [MDN: `<input type="radio">`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/radio)
- [Flask: `url_for`](https://flask.palletsprojects.com/en/stable/api/#flask.url_for)
- [ISO 8601 (Wikipedia)](https://en.wikipedia.org/wiki/ISO_8601)
- 프로젝트 코드: [`new.html`]({{ site.repo_url }}/blob/main/apps/fe/templates/product/new.html), [`_product_card.html`]({{ site.repo_url }}/blob/main/apps/fe/templates/components/_product_card.html), [`common.js`]({{ site.repo_url }}/blob/main/apps/fe/static/js/common.js), [`auction_detail.js`]({{ site.repo_url }}/blob/main/apps/fe/static/js/auction_detail.js), [`schema.dbml`]({{ site.repo_url }}/blob/main/apps/be/schema.dbml)
