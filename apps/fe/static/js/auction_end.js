document.addEventListener("DOMContentLoaded", () => {
  const stamp = document.getElementById("auctionStamp");
  const pending = document.getElementById("auctionPending");
  const accepted = document.getElementById("auctionAccepted");
  const rejected = document.getElementById("auctionRejected");

  const acceptButton = document.getElementById("acceptAuction");
  const rejectButton = document.getElementById("rejectAuction");
  const resetButton = document.getElementById("resetAuction");

  if (!stamp || !pending || !accepted || !rejected) return;

  function setAuctionStatus(status) {
    pending.hidden = status !== "pending";
    accepted.hidden = status !== "accepted";
    rejected.hidden = status !== "rejected";

    stamp.classList.remove("blue", "in");

    if (status === "accepted") {
      stamp.textContent = "거래 확정";
      stamp.classList.add("blue");
    } else if (status === "rejected") {
      stamp.textContent = "거래 안 함";
    } else {
      stamp.textContent = "마감";
    }

    // 상태가 바뀔 때 도장 애니메이션 실행
    void stamp.offsetWidth;
    stamp.classList.add("in");
  }

  acceptButton?.addEventListener("click", () => {
    setAuctionStatus("accepted");
  });

  rejectButton?.addEventListener("click", () => {
    setAuctionStatus("rejected");
  });

  resetButton?.addEventListener("click", () => {
    setAuctionStatus("pending");
  });
});