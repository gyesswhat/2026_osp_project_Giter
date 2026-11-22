// 공통 동작. 화면 전용 동작은 도메인.js(예: product.js)에 둔다.

// 칩 그룹: components/_form_fields.html 의 chip_group 매크로와 짝을 이룬다.
// <div data-chip-group data-name="status" data-multiple="false"> 안의 .chip 버튼을 누르면
// aria-pressed를 바꾸고, 같은 그룹의 hidden input 값을 선택된 칩 값으로 맞춘다.
// 여러 개 선택(data-multiple="true")이면 선택된 값마다 hidden input을 하나씩 둔다.
document.addEventListener('click', (e) => {
  const chip = e.target.closest('[data-chip-group] .chip');
  if (!chip || chip.disabled) return;
  const group = chip.closest('[data-chip-group]');
  const multiple = group.dataset.multiple === 'true';
  const required = group.dataset.required === 'true';
  const chips = [...group.querySelectorAll('.chip')];
  const wasOn = chip.getAttribute('aria-pressed') === 'true';

  if (multiple) {
    chip.setAttribute('aria-pressed', String(!wasOn));
  } else {
    if (wasOn && required) return; // 하나는 꼭 골라야 하는 그룹은 끄지 않는다
    chips.forEach((c) => c.setAttribute('aria-pressed', String(c === chip && !wasOn)));
  }

  syncChipInputs(group);
  group.dispatchEvent(new CustomEvent('chipchange', { bubbles: true, detail: { values: chipValues(group) } }));
});

function chipValues(group) {
  return [...group.querySelectorAll('.chip[aria-pressed="true"]')].map((c) => c.value);
}

function syncChipInputs(group) {
  const name = group.dataset.name;
  if (!name) return;
  group.querySelectorAll('input[type="hidden"][data-chip-value]').forEach((i) => i.remove());
  chipValues(group).forEach((v) => {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = v;
    input.dataset.chipValue = '';
    group.appendChild(input);
  });
}

// 경매 카드 남은 시간: components/_product_card.html 의 data-end-at(마감 시각 ISO 문자열)을 읽어
// "2일 13시간 남음" / "3시간 20분 남음" / "15분 남음" / "제안 마감"으로 바꾸고 1분마다 갱신한다.
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

if (document.querySelector('[data-end-at]')) {
  renderAuctionLeft();
  setInterval(renderAuctionLeft, 60000);
}
