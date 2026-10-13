// 등록 폼 제출 전 간단 확인
document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("item-form");
  if (!form) return;
  form.addEventListener("submit", function (e) {
    if (!confirm("상품을 등록하시겠습니까?")) e.preventDefault();
  });
});
