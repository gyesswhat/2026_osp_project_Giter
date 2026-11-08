// 상품 화면 전용 동작 (product/list.html, detail.html, new.html)

// ---------- 상품 목록: 필터 ----------
// 칩·정렬을 바꾸면 바로 검색하고, 가격 슬라이더는 손을 뗄 때 검색한다.
// 폼에 page 필드가 없으므로 필터를 바꾸면 1페이지로 돌아간다.
(() => {
  const form = document.getElementById('productFilter');
  if (!form) return;

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

  // 가격 슬라이더
  const box = form.querySelector('[data-price-filter]');
  if (!box) return;
  const steps = JSON.parse(box.dataset.steps);
  const last = steps.length; // 마지막 칸 = 상한 없음
  const minIn = box.querySelector('[data-price-min]');
  const maxIn = box.querySelector('[data-price-max]');
  const minVal = box.querySelector('[data-price-min-value]');
  const maxVal = box.querySelector('[data-price-max-value]');
  const fill = box.querySelector('[data-price-fill]');
  const text = box.querySelector('[data-price-text]');
  const quick = [...box.querySelectorAll('.chip[data-pmin]')];

  const won = (n) => n.toLocaleString('ko-KR') + '원';
  const short = (n) => (n >= 10000 ? n / 10000 + '만원' : won(n));

  function render() {
    const a = +minIn.value;
    const b = +maxIn.value;
    // 손잡이 지름(20px)만큼 양끝을 비워 손잡이 가운데에 맞춘다
    fill.style.left = `calc(10px + (100% - 20px) * ${a / last})`;
    fill.style.right = `calc(10px + (100% - 20px) * ${1 - b / last})`;
    text.textContent = a === 0 && b === last ? '전체'
      : a === 0 ? `${short(steps[b])} 이하`
      : b === last ? `${short(steps[a])} 이상`
      : `${short(steps[a])} ~ ${short(steps[b])}`;
    quick.forEach((c) => c.setAttribute('aria-pressed', String(+c.dataset.pmin === a && +c.dataset.pmax === b)));
    minVal.value = a === 0 ? '' : steps[a];
    maxVal.value = b === last ? '' : steps[b];
  }

  // 두 손잡이가 겹치거나 엇갈리지 않게 한 칸 이상 띄운다
  minIn.addEventListener('input', () => { minIn.value = Math.min(+minIn.value, +maxIn.value - 1); render(); });
  maxIn.addEventListener('input', () => { maxIn.value = Math.max(+maxIn.value, +minIn.value + 1); render(); });
  minIn.addEventListener('change', submit);
  maxIn.addEventListener('change', submit);

  quick.forEach((c) => c.addEventListener('click', () => {
    minIn.value = c.dataset.pmin;
    maxIn.value = c.dataset.pmax;
    render();
    submit();
  }));

  render();
})();

// ---------- 상품 상세: 찜 버튼 ----------
// 지금은 화면에서만 바뀐다. BE 연동 시 여기서 찜 API를 부르면 된다.
(() => {
  const btn = document.querySelector('[data-like-button]');
  if (!btn) return;
  const count = document.querySelector('[data-like-count]');
  btn.addEventListener('click', () => {
    const on = btn.getAttribute('aria-pressed') !== 'true';
    btn.setAttribute('aria-pressed', String(on));
    btn.textContent = on ? '♥ 찜한 물건' : '♡ 찜하기';
    if (count) count.textContent = Math.max(0, +count.textContent + (on ? 1 : -1));
  });
})();

// ---------- 상품 상세: 약속 잡기 ----------
// 장소와 시간 칩을 하나씩 고르면 신청 버튼이 켜진다.
(() => {
  const form = document.getElementById('reserveForm');
  if (!form) return;
  const btn = form.querySelector('[data-reserve-button]');
  const msg = form.querySelector('[data-reserve-msg]');
  if (!btn) return; // 장소나 시간이 없어서 채팅 안내만 있는 경우
  const picked = (name) => form.querySelector(`[data-name="${name}"] .chip[aria-pressed="true"]`);
  let sent = false;

  function render() {
    const place = picked('place');
    const slot = picked('slot');
    btn.disabled = sent || !(place && slot);
    btn.textContent = sent ? '약속 신청됨' : '약속 신청';
    msg.textContent = sent ? '약속을 신청했어요. 판매자가 수락하면 마이의 약속 탭에 확정으로 표시돼요.'
      : place && slot ? `${place.dataset.text}, ${slot.dataset.text}에 만나요.`
      : '장소와 시간을 하나씩 골라 주세요.';
  }

  form.addEventListener('chipchange', () => { if (!sent) render(); });
  form.addEventListener('submit', (e) => {
    if (!('demo' in form.dataset)) return; // BE 연동 후에는 그대로 전송
    e.preventDefault();
    sent = true;
    form.querySelectorAll('.chip').forEach((c) => { c.disabled = true; });
    render();
  });
  render();
})();
