document.addEventListener("DOMContentLoaded", () => {
  const stamp = document.getElementById("auctionStamp");

  if (!stamp) return;

  // 화면이 로드될 때 도장 애니메이션 실행
  stamp.classList.add("in");
});