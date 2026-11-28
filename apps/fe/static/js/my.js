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

  // 약속 탭: 진행 중 / 거래 완료 필터
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

  // 수락·거절은 reservation_decide 폼으로 서버에 보낸다 (templates/my/index.html)
})();
