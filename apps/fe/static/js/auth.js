// 회원(auth) 도메인 전용 동작

// 1. 회원가입: 이화인 메일 인증
// auth/signup.html의 '인증 요청', '코드 확인' 버튼을 auth_send_code, auth_verify_code에 연결한다.
// 두 라우트는 안내 문구를 본문으로 응답하므로, 응답 문구를 그대로 화면에 표시한다.
const signupForm = document.querySelector('[data-signup-form]');
if (signupForm) {
  const emailInput = document.getElementById('email');
  const codeInput = document.getElementById('auth_code');
  const sendCodeBtn = document.getElementById('send-code-btn');
  const verifyCodeBtn = document.getElementById('verify-code-btn');
  const verifiedBtn = document.getElementById('verified-btn');
  const emailMsg = document.getElementById('email-msg');
  const codeInfoMsg = document.getElementById('code-info-msg');
  const codeErrorMsg = document.getElementById('code-error-msg');
  const codeSuccessMsg = document.getElementById('code-success-msg');
  const submitHelpMsg = document.getElementById('submit-help-msg');

  const showMessage = (el, text) => {
    el.textContent = text;
    el.hidden = false;
  };

  const postForm = async (url, fields) => {
    try {
      const res = await fetch(url, { method: 'POST', body: new URLSearchParams(fields) });
      const text = await res.text();
      return { ok: res.ok, text };
    } catch (e) {
      return { ok: false, text: '요청을 보내지 못했어요. 다시 시도해 주세요.' };
    }
  };

  // 인증한 메일과 가입하는 메일이 달라지지 않도록 메일과 코드 입력칸을 읽기 전용으로 바꾼다.
  const showVerified = () => {
    emailInput.readOnly = true;
    codeInput.readOnly = true;
    sendCodeBtn.disabled = true;
    verifyCodeBtn.hidden = true;
    verifiedBtn.hidden = false;
    codeInfoMsg.hidden = true;
    codeErrorMsg.hidden = true;
    codeSuccessMsg.hidden = false;
    submitHelpMsg.hidden = true;
  };

  sendCodeBtn.addEventListener('click', async () => {
    const res = await postForm(signupForm.dataset.codeUrl, { email: emailInput.value });
    if (!res.ok) {
      showMessage(emailMsg, res.text);
      return;
    }
    emailMsg.hidden = true;
    codeErrorMsg.hidden = true;
    showMessage(codeInfoMsg, res.text);
  });

  verifyCodeBtn.addEventListener('click', async () => {
    const fields = { email: emailInput.value, auth_code: codeInput.value };
    const res = await postForm(signupForm.dataset.verifyUrl, fields);
    if (!res.ok) {
      showMessage(codeErrorMsg, res.text);
      return;
    }
    showVerified();
  });

  if (signupForm.dataset.verified === 'true') showVerified();
}
