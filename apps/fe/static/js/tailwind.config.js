// Tailwind CDN 설정. 색상 값은 common.css의 :root 토큰을 그대로 가리킨다.
// 색을 바꿀 때는 이 파일이 아니라 common.css의 변수만 고친다.
tailwind.config = {
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        paper: 'var(--paper)',
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        line: 'var(--line)',
        brand: 'var(--brand)',
        brandink: 'var(--brand-ink)',
        onbrand: 'var(--on-brand)',
        tint: 'var(--tint)',
        stamp: 'var(--stamp)',
        stamptint: 'var(--stamp-tint)',
        hl: 'var(--hl)',
        onhl: 'var(--on-hl)',
      },
      fontFamily: {
        sans: ['Pretendard', '"Apple SD Gothic Neo"', '"Malgun Gothic"', 'sans-serif'],
        mono: ['Pretendard', '"Apple SD Gothic Neo"', '"Malgun Gothic"', 'sans-serif'],
        stamp: ['"Black Han Sans"', 'Pretendard', '"Apple SD Gothic Neo"', 'sans-serif'],
      },
    },
  },
};
