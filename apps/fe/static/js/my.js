// 마이페이지(templates/my/index.html) 전용 화면 동작

(() => {
  const tabList = document.getElementById('myTabs');
  const tabs = [...document.querySelectorAll('[data-mytab]')];
  const panels = tabs.map((btn) => document.getElementById(`tab-${btn.dataset.mytab}`));

  function activateTab(key, moveFocus = false) {
    tabs.forEach((btn) => {
      const on = btn.dataset.mytab === key;
      btn.setAttribute('aria-selected', String(on));
      btn.classList.toggle('border-brand', on);
      btn.classList.toggle('text-brandink', on);
      btn.classList.toggle('border-transparent', !on);
      btn.classList.toggle('text-muted', !on);
      btn.classList.toggle('hover:text-ink', !on);
      if (on && moveFocus) btn.focus();
    });

    panels.forEach((panel) => {
      if (panel) panel.hidden = panel.id !== `tab-${key}`;
    });
  }

  if (tabList) {
    tabList.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-mytab]');
      if (btn) activateTab(btn.dataset.mytab);
    });

    tabList.addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      const currentIdx = tabs.findIndex((b) => b.getAttribute('aria-selected') === 'true');
      if (currentIdx === -1) return;
      const dir = e.key === 'ArrowRight' ? 1 : -1;
      const nextIdx = (currentIdx + dir + tabs.length) % tabs.length;
      activateTab(tabs[nextIdx].dataset.mytab, true);
    });
  }

  // 약속 탭: 진행 중 / 거래 완료 필터 및 수락·거절 상태 전환
  const dealGrid = document.getElementById('dealGrid');
  const dealEmpty = document.getElementById('dealEmpty');
  const dealFilter = document.getElementById('dealFilter');
  let dealView = 'active';

  function renderDealsView() {
    if (!dealGrid || !dealEmpty) return;
    const cards = [...dealGrid.querySelectorAll('[data-deal-card]')];
    let visibleCount = 0;

    cards.forEach((card) => {
      const isDone = card.dataset.dealState === 'done';
      const show = (dealView === 'done') === isDone;
      card.hidden = !show;
      if (show) visibleCount += 1;
    });

    dealGrid.hidden = visibleCount === 0;
    dealEmpty.hidden = visibleCount > 0;
    dealEmpty.textContent = dealView === 'done'
      ? '아직 끝난 거래가 없어요.'
      : '진행 중인 약속이 없어요. 상품 상세에서 약속을 신청해 보세요.';
  }

  if (dealFilter) {
    dealFilter.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-dealview]');
      if (!btn) return;
      dealView = btn.dataset.dealview;
      dealFilter.querySelectorAll('[data-dealview]').forEach((b) => {
        b.setAttribute('aria-pressed', String(b === btn));
      });
      renderDealsView();
    });
  }

  if (dealGrid) {
    const chatUrl = dealGrid.dataset.chatUrl || '/chat';

    dealGrid.addEventListener('click', (e) => {
      const acceptBtn = e.target.closest('[data-accept]');
      const rejectBtn = e.target.closest('[data-reject]');
      const card = e.target.closest('[data-deal-card]');
      if (!card || (!acceptBtn && !rejectBtn)) return;

      const stateTextEl = card.querySelector('[data-deal-state-text]');
      const footEl = card.querySelector('[data-deal-foot]');

      if (acceptBtn) {
        card.dataset.dealState = 'confirmed';
        if (stateTextEl) stateTextEl.textContent = '약속 확정';
        if (footEl) {
          footEl.innerHTML =
            `<div class="flex items-center justify-between gap-3">` +
              `<a href="${chatUrl}" class="btn-outline">채팅 열기</a>` +
              `<span class="stamp solid in mr-2">약속 확정</span>` +
            `</div>`;
        }
      } else if (rejectBtn) {
        card.dataset.dealState = 'rejected';
        if (stateTextEl) stateTextEl.textContent = '거절함';
        if (footEl) {
          footEl.innerHTML = `<p class="text-sm text-muted">신청을 거절했어요.</p>`;
        }
      }
    });
  }

  // 내 찜 탭: 찜 해제 시 카드 제거 및 카운트 갱신
  const likeGrid = document.getElementById('likeGrid');
  const likeEmpty = document.getElementById('likeEmpty');
  const likeCountEl = document.getElementById('count-likes');

  if (likeGrid) {
    likeGrid.addEventListener('submit', (e) => {
      const form = e.target.closest('[data-unlike-form]');
      if (!form) return;
      e.preventDefault();

      const card = form.closest('.slip');
      if (card) card.remove();

      const remaining = likeGrid.querySelectorAll('.slip').length;
      if (likeCountEl) likeCountEl.textContent = String(remaining);
      if (remaining === 0) {
        likeGrid.hidden = true;
        if (likeEmpty) likeEmpty.hidden = false;
      }
    });
  }
})();