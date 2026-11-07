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
