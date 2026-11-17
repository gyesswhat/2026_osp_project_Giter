// 등록 폼 제출 전 간단 확인
document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("item-form");
  if (!form) return;
  form.addEventListener("submit", function (e) {
    if (!confirm("상품을 등록하시겠습니까?")) e.preventDefault();
  });
});

// 좋아요: AJAX로 버튼만 갱신 (페이지 새로고침 없음)
document.addEventListener("DOMContentLoaded", function () {
  var btn = document.getElementById("like-btn");
  if (!btn) return;

  function render(liked, count) {
    btn.classList.toggle("liked", liked);
    btn.setAttribute("aria-pressed", liked ? "true" : "false");
    btn.querySelector(".heart").textContent = liked ? "♥" : "♡";
    btn.querySelector(".like-label").textContent = liked ? "Liked" : "Like";
    btn.querySelector(".like-count").textContent = count;
  }

  btn.addEventListener("click", function () {
    if (btn.dataset.loggedIn !== "true") {
      alert("로그인이 필요합니다.");
      location.href = btn.dataset.loginUrl;
      return;
    }
    var liked = btn.classList.contains("liked");
    // 첫 클릭: 좋아요, 다시 클릭: 좋아요 취소
    var url = liked ? btn.dataset.unlikeUrl : btn.dataset.likeUrl;
    btn.disabled = true;
    fetch(url, { method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (res) {
        return res.json().then(function (body) { return { ok: res.ok, status: res.status, body: body }; });
      })
      .then(function (r) {
        if (r.status === 401) {
          alert(r.body.msg);
          location.href = r.body.login_url;
          return;
        }
        if (!r.ok) throw new Error(r.body.msg || "요청에 실패했습니다.");
        render(r.body.liked, r.body.count);
      })
      .catch(function (err) { alert(err.message); })
      .finally(function () { btn.disabled = false; });
  });
});
