
document.addEventListener("DOMContentLoaded", () => {
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

        message.textContent =
            `${amount.toLocaleString("ko-KR")}원 제안 금액이 확인되었습니다. (미리보기에서는 저장되지 않습니다.)`;
    });
});
