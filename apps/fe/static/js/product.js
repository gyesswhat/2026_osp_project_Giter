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

// ---------- 상품 등록: 대표 사진 미리보기 ----------
// 파일 칸은 숨겨 두고, 고르거나 끌어다 놓은 사진을 바로 보여 준다.
const PHOTO_TYPES = ['image/jpeg', 'image/png'];
const PHOTO_MAX = 5 * 1024 * 1024;

(() => {
  const box = document.querySelector('[data-photo]');
  if (!box) return;
  const input = box.querySelector('[data-photo-input]');
  const drop = box.querySelector('[data-photo-drop]');
  const preview = box.querySelector('[data-photo-preview]');
  const img = box.querySelector('[data-photo-img]');
  const nameEl = box.querySelector('[data-photo-name]');
  const msg = document.getElementById('picture-msg');
  let url = null;

  const setError = (text) => {
    msg.textContent = text || '';
    msg.hidden = !text;
    msg.setAttribute('role', text ? 'alert' : '');
  };

  function show(file) {
    if (url) URL.revokeObjectURL(url);
    url = file ? URL.createObjectURL(file) : null;
    img.src = url || '';
    const size = !file ? '' : file.size < 1024 * 1024 ? `${Math.max(1, Math.round(file.size / 1024))}KB`
      : `${(file.size / 1024 / 1024).toFixed(1)}MB`;
    nameEl.textContent = file ? `${file.name} · ${size}` : '';
    preview.hidden = !file;
    drop.hidden = !!file;
  }

  // 형식·크기를 확인하고 틀리면 고른 파일을 비운다
  function check() {
    const file = input.files[0];
    if (file && !PHOTO_TYPES.includes(file.type)) {
      input.value = ''; show(null); setError('JPG나 PNG 사진만 올릴 수 있어요.'); return;
    }
    if (file && file.size > PHOTO_MAX) {
      input.value = ''; show(null); setError('5MB 이하 사진을 골라 주세요.'); return;
    }
    setError('');
    show(file || null);
  }

  input.addEventListener('change', check);
  box.querySelector('[data-photo-clear]').addEventListener('click', () => {
    input.value = ''; show(null); drop.focus?.();
  });

  // 끌어다 놓기
  ['dragenter', 'dragover'].forEach((t) => drop.addEventListener(t, (e) => {
    e.preventDefault(); drop.classList.add('is-over');
  }));
  ['dragleave', 'drop'].forEach((t) => drop.addEventListener(t, () => drop.classList.remove('is-over')));
  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    check();
  });
})();

// ---------- 상품 등록: 가격 쉼표 + 제출 전 확인 ----------
(() => {
  const form = document.getElementById('productNewForm');
  if (!form) return;

  // 가격: 입력하는 동안 18,000 처럼 쉼표를 넣고, 보낼 때는 숫자만 보낸다
  const price = form.querySelector('[data-price-input]');
  price.addEventListener('input', () => {
    const digits = price.value.replace(/\D/g, '').replace(/^0+(?=\d)/, '');
    price.value = digits ? Number(digits).toLocaleString('ko-KR') : '';
  });

  const setError = (field, text) => {
    const msg = document.getElementById(`${field}-msg`);
    const el = form.querySelector(`#${field}`);
    if (el) el.setAttribute('aria-invalid', text ? 'true' : 'false');
    if (!msg) return;
    // 안내 문구(help) 자리는 오류가 없을 때 원래 문구로 돌려놓는다
    if (msg.dataset.help === undefined && msg.classList.contains('help')) msg.dataset.help = msg.textContent;
    if (text) {
      msg.textContent = text; msg.className = 'error'; msg.hidden = false;
    } else if (msg.dataset.help !== undefined) {
      msg.textContent = msg.dataset.help; msg.className = 'help'; msg.hidden = false;
    } else {
      msg.textContent = ''; msg.hidden = true;
    }
  };

  const rules = {
    picture: () => (form.picture.files.length ? '' : '대표 사진을 올려 주세요.'),
    seller: () => (form.seller.value.trim() ? '' : '판매자 ID를 입력해 주세요.'),
    name: () => (form.name.value.trim() ? '' : '상품명을 입력해 주세요.'),
    price: () => (/^\d+$/.test(price.value.replace(/,/g, '')) ? '' : '가격을 숫자로 입력해 주세요.'),
    address: () => (form.address.value.trim() ? '' : '거래할 주소를 입력해 주세요.'),
    status: () => (form.querySelector('input[name="status"]') ? '' : '상품 상태를 골라 주세요.'),
    description: () => (form.description.value.trim() ? '' : '상세 설명을 입력해 주세요.'),
  };

  // 오류가 난 칸은 고치는 즉시 메시지를 지운다
  Object.keys(rules).forEach((field) => {
    const el = field === 'status' ? form.querySelector('[data-name="status"]') : form.querySelector(`#${field}`);
    if (!el) return;
    const ev = field === 'status' ? 'chipchange' : (field === 'picture' ? 'change' : 'input');
    el.addEventListener(ev, () => {
      if (el.getAttribute('aria-invalid') === 'true' || field === 'status') setError(field, rules[field]());
    });
  });

  form.addEventListener('submit', (e) => {
    let first = null;
    Object.entries(rules).forEach(([field, rule]) => {
      const text = rule();
      if (field !== 'picture') setError(field, text); // 사진 오류는 위 사진 칸 코드와 같은 자리를 쓴다
      else if (text) { const m = document.getElementById('picture-msg'); m.textContent = text; m.hidden = false; }
      if (text && !first) first = field;
    });
    if (first) {
      e.preventDefault();
      const target = first === 'picture' ? form.querySelector('[data-photo-drop]')
        : first === 'status' ? form.querySelector('[data-name="status"] .chip') : form.querySelector(`#${first}`);
      target?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      target?.focus({ preventScroll: true });
      return;
    }
    price.value = price.value.replace(/,/g, '');
  });
})();
