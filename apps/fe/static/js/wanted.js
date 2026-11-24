// 구해요(wanted) 도메인 전용 동작

// 1. 구해요 목록: 분류 칩 변경 시 카드 필터링
const categoryGroup = document.getElementById('wantedCategoryChips');
if (categoryGroup) {
  const cards = [...document.querySelectorAll('[data-wanted-card]')];
  const emptyBox = document.getElementById('wantedEmpty');

  const filterWantedCards = (selectedCategory) => {
    let visibleCount = 0;
    cards.forEach((card) => {
      const match = selectedCategory === 'all' || card.dataset.category === selectedCategory;
      card.hidden = !match;
      if (match) visibleCount += 1;
    });
    if (emptyBox) {
      emptyBox.hidden = visibleCount > 0;
    }
  };

  categoryGroup.addEventListener('chipchange', (e) => {
    const selected = e.detail.values[0] || 'all';
    filterWantedCards(selected);
  });
}

// 2. 구해요 글쓰기: 사진 업로드 및 폼 검증
const wantedNewForm = document.getElementById('wantedNewForm');
if (wantedNewForm) {
  const picInput = document.getElementById('picture');
  const picDropzone = document.getElementById('picDropzone');
  const picPreviewBox = document.getElementById('picPreviewBox');
  const picPreviewImg = document.getElementById('picPreviewImg');
  const picFileName = document.getElementById('picFileName');
  const picFileSize = document.getElementById('picFileSize');
  const picChangeBtn = document.getElementById('picChangeBtn');
  const picClearBtn = document.getElementById('picClearBtn');
  const picMsg = document.getElementById('picture-msg');

  const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
  const ALLOWED_TYPES = ['image/jpeg', 'image/png'];

  const showPicError = (msg) => {
    if (!picMsg) return;
    if (msg) {
      picMsg.textContent = msg;
      picMsg.setAttribute('role', 'alert');
      picMsg.hidden = false;
    } else {
      picMsg.textContent = '';
      picMsg.removeAttribute('role');
      picMsg.hidden = true;
    }
  };

  const resetPicture = () => {
    if (picInput) picInput.value = '';
    if (picPreviewImg) picPreviewImg.src = '';
    if (picPreviewBox) picPreviewBox.hidden = true;
    if (picDropzone) picDropzone.hidden = false;
    showPicError('');
  };

  const formatBytes = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handlePictureFile = (file) => {
    if (!file) return;
    const extOk = /\.(jpe?g|png)$/i.test(file.name);
    if (!ALLOWED_TYPES.includes(file.type) && !extOk) {
      resetPicture();
      showPicError('JPG 또는 PNG 파일만 올릴 수 있어요.');
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      resetPicture();
      showPicError('5MB 이하의 이미지만 올릴 수 있어요.');
      return;
    }

    showPicError('');
    const reader = new FileReader();
    reader.onload = (ev) => {
      if (picPreviewImg) picPreviewImg.src = ev.target.result;
      if (picFileName) picFileName.textContent = file.name;
      if (picFileSize) picFileSize.textContent = formatBytes(file.size);
      if (picDropzone) picDropzone.hidden = true;
      if (picPreviewBox) picPreviewBox.hidden = false;
    };
    reader.readAsDataURL(file);
  };

  if (picDropzone && picInput) {
    picDropzone.addEventListener('click', () => picInput.click());
    picDropzone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        picInput.click();
      }
    });

    ['dragenter', 'dragover'].forEach((evt) => {
      picDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        picDropzone.classList.add('border-brandink', 'bg-tint');
      });
    });

    ['dragleave', 'drop'].forEach((evt) => {
      picDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        picDropzone.classList.remove('border-brandink', 'bg-tint');
      });
    });

    picDropzone.addEventListener('drop', (e) => {
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (!file) return;
      const dt = new DataTransfer();
      dt.items.add(file);
      picInput.files = dt.files;
      handlePictureFile(file);
    });

    picInput.addEventListener('change', () => {
      const file = picInput.files && picInput.files[0];
      if (file) handlePictureFile(file);
    });
  }

  if (picChangeBtn && picInput) {
    picChangeBtn.addEventListener('click', () => picInput.click());
  }

  if (picClearBtn) {
    picClearBtn.addEventListener('click', () => resetPicture());
  }

  // 입력 필드 검증
  const nameInput = document.getElementById('name');
  const budgetInput = document.getElementById('budget');
  const dateInput = document.getElementById('due_date');
  const placeGroup = document.getElementById('cg-places');

  // 로컬 기준 오늘 날짜 (YYYY-MM-DD)
  const getTodayStr = () => {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  };

  if (dateInput) {
    dateInput.min = getTodayStr();
    dateInput.addEventListener('change', () => {
      if (dateInput.value && dateInput.value < getTodayStr()) {
        setFieldError(dateInput, '오늘 이후 날짜로 선택해 주세요.');
      } else if (dateInput.value) {
        setFieldError(dateInput, '');
      }
    });
  }

  const setFieldError = (inputEl, message) => {
    if (!inputEl) return;
    const msgEl = document.getElementById(`${inputEl.id}-msg`);
    if (message) {
      inputEl.setAttribute('aria-invalid', 'true');
      if (msgEl) {
        msgEl.textContent = message;
        msgEl.className = 'error';
        msgEl.hidden = false;
      }
    } else {
      inputEl.removeAttribute('aria-invalid');
      if (msgEl) {
        msgEl.textContent = '';
        msgEl.hidden = true;
      }
    }
  };

  if (budgetInput) {
    budgetInput.addEventListener('input', () => {
      const rawDigits = budgetInput.value.replace(/[^0-9]/g, '');
      if (!rawDigits) {
        budgetInput.value = '';
        return;
      }
      // 0 또는 00001처럼 0으로 시작하는 입력 방지
      if (/^0/.test(rawDigits)) {
        budgetInput.value = '';
        setFieldError(budgetInput, '예산은 0으로 시작할 수 없어요. 다시 입력해 주세요.');
        return;
      }
      budgetInput.value = Number(rawDigits).toLocaleString('ko-KR');
      setFieldError(budgetInput, '');
    });
  }

  if (nameInput) {
    nameInput.addEventListener('input', () => {
      if (nameInput.value.trim()) setFieldError(nameInput, '');
    });
  }

  wantedNewForm.addEventListener('submit', (e) => {
    let firstInvalid = null;

    if (nameInput && !nameInput.value.trim()) {
      setFieldError(nameInput, '찾는 물건 이름을 입력해 주세요.');
      firstInvalid = firstInvalid || nameInput;
    } else {
      setFieldError(nameInput, '');
    }

    const rawBudget = budgetInput ? budgetInput.value.replace(/[^0-9]/g, '') : '';
    const budgetValue = rawBudget ? Number(rawBudget) : 0;
    if (budgetInput && (/^0/.test(rawBudget) || budgetValue <= 0)) {
      setFieldError(budgetInput, '예산은 1원 이상 올바른 금액으로 입력해 주세요.');
      firstInvalid = firstInvalid || budgetInput;
    } else {
      setFieldError(budgetInput, '');
    }

    const today = getTodayStr();
    if (dateInput && !dateInput.value) {
      setFieldError(dateInput, '필요한 날을 선택해 주세요.');
      firstInvalid = firstInvalid || dateInput;
    } else if (dateInput && dateInput.value < today) {
      setFieldError(dateInput, '오늘 이후 날짜로 선택해 주세요.');
      firstInvalid = firstInvalid || dateInput;
    } else {
      setFieldError(dateInput, '');
    }

    if (placeGroup) {
      const selectedPlaces = placeGroup.querySelectorAll('.chip[aria-pressed="true"]');
      let placeErr = placeGroup.parentElement.querySelector('.error');
      if (selectedPlaces.length === 0) {
        if (!placeErr) {
          placeErr = document.createElement('p');
          placeErr.className = 'error';
          placeErr.setAttribute('role', 'alert');
          placeGroup.parentElement.appendChild(placeErr);
        }
        placeErr.textContent = '거래 장소를 하나 이상 골라 주세요.';
        placeErr.hidden = false;
        firstInvalid = firstInvalid || placeGroup.querySelector('.chip');
      } else if (placeErr) {
        placeErr.hidden = true;
      }
    }

    if (firstInvalid) {
      e.preventDefault();
      firstInvalid.focus();
      return;
    }

    if (budgetInput) {
      budgetInput.value = String(budgetValue);
    }
  });
}

// 3. 구해요 상세: 제안 사진 업로드, 제안 정렬, 제안 선택/해제, 새 제안 보내기
const wantedDetailRoot = document.getElementById('wantedDetailRoot');
if (wantedDetailRoot) {
  const budgetLimit = Number(wantedDetailRoot.dataset.budget) || 0;
  const chatUrl = wantedDetailRoot.dataset.chatUrl || '/chat';

  const offerSortChips = document.getElementById('offerSortChips');
  const offerList = document.getElementById('offerList');
  const offerCountEl = document.getElementById('offerCount');
  const offerEmptyEl = document.getElementById('offerEmpty');
  const offerForm = document.getElementById('offerForm');
  const oPriceInput = document.getElementById('oPrice');
  const oDescInput = document.getElementById('oDesc');
  const offerMsgEl = document.getElementById('offerMsg');

  // 제안 사진 업로드 요소
  const offerPicInput = document.getElementById('offerPicture');
  const offerPicDropzone = document.getElementById('offerPicDropzone');
  const offerPicPreviewBox = document.getElementById('offerPicPreviewBox');
  const offerPicPreviewImg = document.getElementById('offerPicPreviewImg');
  const offerPicFileName = document.getElementById('offerPicFileName');
  const offerPicFileSize = document.getElementById('offerPicFileSize');
  const offerPicChangeBtn = document.getElementById('offerPicChangeBtn');
  const offerPicClearBtn = document.getElementById('offerPicClearBtn');
  const offerPicMsg = document.getElementById('offerPicture-msg');

  const MAX_OFFER_FILE_SIZE = 5 * 1024 * 1024; // 5MB
  const ALLOWED_OFFER_TYPES = ['image/jpeg', 'image/png'];
  let offerImageData = '';

  const showOfferPicError = (msg) => {
    if (!offerPicMsg) return;
    if (msg) {
      offerPicMsg.textContent = msg;
      offerPicMsg.setAttribute('role', 'alert');
      offerPicMsg.hidden = false;
    } else {
      offerPicMsg.textContent = '';
      offerPicMsg.removeAttribute('role');
      offerPicMsg.hidden = true;
    }
  };

  const resetOfferPicture = () => {
    offerImageData = '';
    if (offerPicInput) offerPicInput.value = '';
    if (offerPicPreviewImg) offerPicPreviewImg.src = '';
    if (offerPicPreviewBox) offerPicPreviewBox.hidden = true;
    if (offerPicDropzone) offerPicDropzone.hidden = false;
    showOfferPicError('');
  };

  const formatOfferBytes = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleOfferPictureFile = (file) => {
    if (!file) return;
    const extOk = /\.(jpe?g|png)$/i.test(file.name);
    if (!ALLOWED_OFFER_TYPES.includes(file.type) && !extOk) {
      resetOfferPicture();
      showOfferPicError('JPG 또는 PNG 파일만 올릴 수 있어요.');
      return;
    }
    if (file.size > MAX_OFFER_FILE_SIZE) {
      resetOfferPicture();
      showOfferPicError('5MB 이하의 이미지만 올릴 수 있어요.');
      return;
    }

    showOfferPicError('');
    const reader = new FileReader();
    reader.onload = (ev) => {
      offerImageData = typeof ev.target.result === 'string' ? ev.target.result : '';
      if (offerPicPreviewImg) offerPicPreviewImg.src = offerImageData;
      if (offerPicFileName) offerPicFileName.textContent = file.name;
      if (offerPicFileSize) offerPicFileSize.textContent = formatOfferBytes(file.size);
      if (offerPicDropzone) offerPicDropzone.hidden = true;
      if (offerPicPreviewBox) offerPicPreviewBox.hidden = false;
    };
    reader.readAsDataURL(file);
  };

  if (offerPicDropzone && offerPicInput) {
    offerPicDropzone.addEventListener('click', () => offerPicInput.click());
    offerPicDropzone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        offerPicInput.click();
      }
    });

    ['dragenter', 'dragover'].forEach((evt) => {
      offerPicDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        offerPicDropzone.classList.add('border-brandink', 'bg-tint');
      });
    });

    ['dragleave', 'drop'].forEach((evt) => {
      offerPicDropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        offerPicDropzone.classList.remove('border-brandink', 'bg-tint');
      });
    });

    offerPicDropzone.addEventListener('drop', (e) => {
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (!file) return;
      const dt = new DataTransfer();
      dt.items.add(file);
      offerPicInput.files = dt.files;
      handleOfferPictureFile(file);
    });

    offerPicInput.addEventListener('change', () => {
      const file = offerPicInput.files && offerPicInput.files[0];
      if (file) handleOfferPictureFile(file);
    });
  }

  if (offerPicChangeBtn && offerPicInput) {
    offerPicChangeBtn.addEventListener('click', () => offerPicInput.click());
  }

  if (offerPicClearBtn) {
    offerPicClearBtn.addEventListener('click', () => resetOfferPicture());
  }

  let currentSort = 'low';
  let pickedOfferId = null;

  const formatWon = (n) => `${Number(n).toLocaleString('ko-KR')}원`;

  const nowStamp = () => {
    const n = new Date();
    const pad = (v) => String(v).padStart(2, '0');
    return `${pad(n.getMonth() + 1)}.${pad(n.getDate())} ${pad(n.getHours())}:${pad(n.getMinutes())}`;
  };

  const setOfferInputError = (inputEl, message) => {
    if (!inputEl) return;
    const msgEl = document.getElementById(`${inputEl.id}-msg`);
    if (message) {
      inputEl.setAttribute('aria-invalid', 'true');
      if (msgEl) {
        msgEl.textContent = message;
        msgEl.className = 'error';
        msgEl.hidden = false;
      }
    } else {
      inputEl.removeAttribute('aria-invalid');
      if (msgEl) {
        msgEl.textContent = '';
        msgEl.hidden = true;
      }
    }
  };

  const syncOfferStates = () => {
    if (!offerList) return;
    const cards = [...offerList.querySelectorAll('[data-offer-card]')];

    cards.sort((a, b) => {
      if (currentSort === 'low') {
        return Number(a.dataset.price) - Number(b.dataset.price);
      }
      return String(b.dataset.time).localeCompare(String(a.dataset.time));
    });

    cards.forEach((card) => {
      offerList.appendChild(card);
      const id = card.dataset.offerId;
      const isChosen = pickedOfferId !== null && pickedOfferId === id;
      const isDimmed = pickedOfferId !== null && !isChosen;

      card.classList.toggle('opacity-50', isDimmed);

      const idleBox = card.querySelector('[data-offer-idle]');
      const chosenBox = card.querySelector('[data-offer-chosen]');
      if (idleBox) idleBox.hidden = pickedOfferId !== null;
      if (chosenBox) chosenBox.hidden = !isChosen;
    });

    if (offerCountEl) offerCountEl.textContent = String(cards.length);
    if (offerEmptyEl) offerEmptyEl.hidden = cards.length > 0;
  };

  if (offerSortChips) {
    offerSortChips.addEventListener('chipchange', (e) => {
      currentSort = e.detail.values[0] || 'low';
      syncOfferStates();
    });
  }

  if (offerList) {
    offerList.addEventListener('click', (e) => {
      const pickBtn = e.target.closest('[data-pick]');
      if (pickBtn) {
        const card = pickBtn.closest('[data-offer-card]');
        if (card) {
          pickedOfferId = card.dataset.offerId;
          syncOfferStates();
        }
        return;
      }

      if (e.target.closest('[data-unpick]')) {
        pickedOfferId = null;
        syncOfferStates();
      }
    });
  }

  if (oPriceInput) {
    oPriceInput.addEventListener('input', () => {
      const rawDigits = oPriceInput.value.replace(/[^0-9]/g, '');
      if (!rawDigits) {
        oPriceInput.value = '';
        return;
      }
      if (/^0/.test(rawDigits)) {
        oPriceInput.value = '';
        setOfferInputError(oPriceInput, '제안 금액은 0으로 시작할 수 없어요.');
        return;
      }
      oPriceInput.value = Number(rawDigits).toLocaleString('ko-KR');
      setOfferInputError(oPriceInput, '');
    });
  }

  const createOfferCard = ({ id, who, star, price, desc, place, time, imageData }) => {
    const li = document.createElement('li');
    li.className = 'slip wanted-offer-card p-4';
    li.dataset.offerCard = '';
    li.dataset.offerId = String(id);
    li.dataset.price = String(price);
    li.dataset.time = time;

    const thumbHtml = imageData
      ? `<img src="${imageData}" alt="" loading="lazy" class="h-full w-full object-cover">`
      : '<span class="center text-[11px] text-muted">이미지 없음</span>';

    li.innerHTML = `
      <div class="flex gap-4">
        <span class="ph relative h-16 w-16 shrink-0 overflow-hidden rounded-sm">
          ${thumbHtml}
        </span>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
            <span class="break-all font-semibold"></span>
            <span class="shrink-0 whitespace-nowrap text-xs text-muted">★ ${Number(star).toFixed(1)}</span>
          </div>
          <div class="row mt-1">
            <span class="text-xs text-muted">제안가</span>
            <span class="leader"></span>
            <span class="num shrink-0 whitespace-nowrap text-[17px] text-brandink">${formatWon(price)}</span>
          </div>
          <p class="mt-1.5 text-sm" data-offer-desc></p>
          <p class="mt-1 flex flex-wrap justify-between gap-2 text-xs text-muted">
            <span data-offer-place></span>
            <span class="font-mono">${time}</span>
          </p>
        </div>
      </div>
      <div class="mt-3 flex justify-end border-t border-dashed border-line pt-3" data-offer-idle>
        <button type="button" class="btn-outline py-1.5" data-pick="">이 제안 고르기</button>
      </div>
      <div class="mt-3 flex flex-wrap items-center justify-end gap-2 border-t border-dashed border-line pt-3" data-offer-chosen hidden>
        <span class="stamp solid blue in mr-auto">이걸로 할게요</span>
        <button type="button" class="btn-quiet py-1.5 text-xs" data-unpick="">다시 고르기</button>
        <a href="${chatUrl}" class="btn-primary py-1.5">채팅 열기</a>
      </div>
    `;

    li.querySelector('.font-semibold').textContent = who;
    li.querySelector('[data-offer-desc]').textContent = desc;
    li.querySelector('[data-offer-place]').textContent = place;
    return li;
  };

  if (offerForm) {
    offerForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const rawPrice = oPriceInput ? oPriceInput.value.replace(/[^0-9]/g, '') : '';
      const priceVal = rawPrice ? Number(rawPrice) : 0;

      if (/^0/.test(rawPrice) || priceVal <= 0 || (budgetLimit > 0 && priceVal > budgetLimit)) {
        const limitMsg = budgetLimit > 0
          ? `예산(${formatWon(budgetLimit)}) 이하로 제안해 주세요.`
          : '1원 이상 올바른 금액으로 제안해 주세요.';
        setOfferInputError(oPriceInput, limitMsg);
        if (offerMsgEl) {
          offerMsgEl.className = 'text-sm text-stamp';
          offerMsgEl.textContent = limitMsg;
        }
        if (oPriceInput) oPriceInput.focus();
        return;
      }

      setOfferInputError(oPriceInput, '');

      const descText = (oDescInput && oDescInput.value.trim()) || '상태 설명 없음';
      const newCard = createOfferCard({
        id: `offer-${Date.now()}`,
        who: '나',
        star: 4.8,
        price: priceVal,
        desc: descText,
        place: 'ECC',
        time: nowStamp(),
        imageData: offerImageData
      });

      if (offerList) {
        offerList.appendChild(newCard);
      }

      if (oPriceInput) oPriceInput.value = '';
      if (oDescInput) oDescInput.value = '';
      resetOfferPicture();
      if (offerMsgEl) {
        offerMsgEl.className = 'text-sm font-semibold text-brandink';
        offerMsgEl.textContent = `${formatWon(priceVal)}으로 제안을 보냈어요. 글쓴이가 고르면 알림이 와요.`;
      }

      syncOfferStates();
    });
  }
}