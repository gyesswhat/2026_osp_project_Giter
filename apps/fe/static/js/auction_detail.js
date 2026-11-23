
document.addEventListener("DOMContentLoaded", () => {
        // 경매 마감까지 남은 시간 계산
    const remainingTime = document.getElementById("remainingTime");

    if (remainingTime) {
        const endAt = new Date(remainingTime.dataset.endAt);

        function updateRemainingTime() {
            const diff = Math.max(0, endAt.getTime() - Date.now());

            if (!Number.isFinite(diff)) {
                remainingTime.textContent = "마감 시간 확인 불가";
                return;
            }

            if (diff === 0) {
                remainingTime.textContent = "마감";
                return;
            }

            const days = Math.floor(diff / 86400000);
            const hours = Math.floor((diff % 86400000) / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);

            const pad = (n) => String(n).padStart(2, "0");

            remainingTime.textContent =
                `${days}일 ${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
        }

        updateRemainingTime();
        setInterval(updateRemainingTime, 1000);
    }
    const form = document.getElementById("bidForm");
    const input = document.getElementById("bidInput");
    const message = document.getElementById("bidMsg");
    const quickButtons = document.querySelectorAll("#bidQuick [data-plus]");

    if (!form || !input || !message) return;

    const highestBid = Number(form.dataset.highestBid);
    const minimumBid = highestBid + 5000;

    if (!Number.isFinite(highestBid)) return;

    // 빠른 제안 버튼
    quickButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const amount = highestBid + Number(button.dataset.plus);
            input.value = amount.toLocaleString("ko-KR");
            message.textContent = `${amount.toLocaleString("ko-KR")}원이 입력되었습니다.`;
            input.focus();
        });
    });

    // 제안 금액 검사
    form.addEventListener("submit", (event) => {
        event.preventDefault();

        const rawValue = input.value.replace(/,/g, "").trim();
        const amount = Number(rawValue);

        if (!/^\d+$/.test(rawValue) || !Number.isSafeInteger(amount)) {
            message.textContent = "제안 금액을 숫자로 입력해 주세요.";
            return;
        }

        if (amount < minimumBid) {
            message.textContent =
                `최소 ${minimumBid.toLocaleString("ko-KR")}원 이상 제안해야 합니다.`;
            return;
        }

        input.value = String(amount);
        form.submit();
    });
});
