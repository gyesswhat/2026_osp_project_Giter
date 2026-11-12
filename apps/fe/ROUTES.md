# 라우트 경로표

FE 템플릿이 `url_for`로 부르는 라우트 목록입니다. BE는 이 표의 **라우트 함수 이름**과 **경로**대로 라우트를 만들면 템플릿을 고치지 않고 연결할 수 있습니다.
미리보기 서버(`preview.py`)도 같은 경로로 맞춰 두었습니다.

## 규칙

- 라우트 함수 이름은 `도메인_동작`이고, 템플릿 경로와 짝을 이룹니다. 예) `product_detail` → `product/detail.html`
- 동작 이름은 목록 `list`, 상세 `detail`, 작성·등록 `new`, 관리 `manage`로 통일합니다.
- 템플릿에서는 경로를 직접 쓰지 않고 항상 `url_for('라우트 함수 이름', ...)`로 링크합니다. 경로를 바꿔도 템플릿은 그대로 둡니다.
- **상세 화면은 경로 파라미터**로 받습니다. 상품과 리뷰는 Firebase에서 상품명이 키라서 상품명을 그대로 씁니다.
  - 상품명에 `/`가 들어갈 수 있으므로 `<name>`이 아니라 `<path:name>`을 씁니다. (`<name>`이면 `아이패드 1/2` 같은 이름이 404가 납니다)
  - `url_for('product_detail', name=p.name)`처럼 이름만 넘기면 한글·공백은 Flask가 알아서 인코딩합니다.
- 화면이 아닌 처리(약속 신청 등)는 상품명을 경로에 넣지 않고 **폼 값**으로 보냅니다.
- `/product/new` `/product/reserve` `/review/done`처럼 고정 경로가 `/product/<path:name>` `/review/<path:name>`보다 먼저 잡히므로, 상품명 `new` `reserve` `done`은 등록할 수 없게 막습니다.
- 로그인 여부는 `session['id']`로 판단합니다.

## 경로표

상태: **화면** 템플릿까지 있음 · **미리보기** `preview.py`에만 처리가 있음 · **예정** 화면이나 처리가 아직 없음

| 화면 | 메서드 | 경로 | 라우트 함수 | 템플릿 | 상태 |
| --- | --- | --- | --- | --- | --- |
| 상품 목록 (홈) | GET | `/` | `product_list` | `product/list.html` | 화면 |
| 상품 상세 | GET | `/product/<path:name>` | `product_detail` | `product/detail.html` | 화면 |
| 상품 등록 | GET, POST | `/product/new` | `product_new` | `product/new.html` | 화면 |
| 약속 신청 | POST | `/product/reserve` | `product_reserve` | (없음, 상세로 redirect) | 미리보기 |
| 리뷰 목록 | GET | `/review` | `review_list` | `review/list.html` | 화면 |
| 리뷰 상세 | GET | `/review/<path:name>` | `review_detail` | `review/detail.html` | 화면 |
| 리뷰 작성 | GET, POST | `/review/new` | `review_new` | `review/new.html` | 화면 |
| 리뷰 등록 완료 | GET | `/review/done` | `review_done` | `review/done.html` | 화면 |
| 로그인 | GET, POST | `/login` | `auth_login` | `auth/login.html` | 화면 |
| 회원가입 | GET, POST | `/signup` | `auth_signup` | `auth/signup.html` | 화면 |
| 로그아웃 | GET | `/logout` | `auth_logout` | (없음, 목록으로 redirect) | 미리보기 |
| 채팅 | GET | `/chat` | `chat_room` | `chat/room.html` | 예정 |
| 구해요 목록 | GET | `/wanted` | `wanted_list` | `wanted/list.html` | 예정 |
| 구해요 상세 | GET | `/wanted/detail` | `wanted_detail` | `wanted/detail.html` | 예정 |
| 구해요 글쓰기 | GET, POST | `/wanted/new` | `wanted_new` | `wanted/new.html` | 예정 |
| 마이페이지 | GET | `/my` | `my_index` | `my/index.html` | 예정 |
| 내 상품 관리 | GET | `/my/manage` | `my_manage` | `my/manage.html` | 예정 |
| 경매 상세 | GET | `/auction/detail` | `auction_detail` | `auction/detail.html` | 예정 |
| 경매 마감 | GET | `/auction/end` | `auction_end` | `auction/end.html` | 예정 |

예정 화면의 경로는 자리만 잡아 둔 것입니다. 상세 화면(구해요·경매)은 화면을 만들 때 위 규칙대로 경로 파라미터를 정해서 이 표를 고칩니다.

## 화면별로 주고받는 값

### `product_list` `/`
- 쿼리: `q` 검색어, `sort` new·like·low·high, `sale_status` all·sale·hold, `kind` all·fixed·bid, `price_min`·`price_max` 원 단위(없으면 제한 없음), `page` 1부터
- 템플릿에 넘길 값: `products`(현재 페이지 상품 dict 목록), `total`, `page`, `total_pages`
- 거래 완료(`sale_status == 'done'`) 상품은 목록에서 뺍니다.

### `product_detail` `/product/<path:name>`
- 템플릿에 넘길 값: `product`(dict), `liked`(선택), `image`(선택)
- 상품이 없으면 404
- `product`의 필드는 `product/detail.html` 맨 위 주석 참고 (`name, seller, price, address, status, description, img_path, sale_status, kind, date, likes, places, slots`)

### `product_new` `/product/new`
- POST `multipart/form-data`: `seller, name, price, address, status, description, picture`
- 성공: `product_detail`로 redirect + flash `상품을 등록했어요.`
- 실패: 같은 템플릿에 `form`(입력값), `errors`(필드별 메시지 dict)를 넘겨 다시 그림
- 같은 상품명이 이미 있거나 `new` `reserve` `done`이면 `errors['name']`

### `product_reserve` `/product/reserve`
- POST: `name`(상품명), `place`(장소 칩 순번), `slot`(시간 칩 순번)
- 처리 후 `product_detail`로 redirect + flash

### `review_list` `/review`
- 쿼리: `seller` 판매자 ID(있으면 그 판매자가 받은 리뷰만, 판매자 바 표시), `page`
- 상품 상세의 '판매자 리뷰 보기'가 `url_for('review_list', seller=p.seller)`로 들어옵니다.

### `review_detail` `/review/<path:name>`
- `name`은 리뷰를 쓴 상품의 상품명입니다. (리뷰를 상품명 키로 저장한다는 전제, BE와 합의 필요)

### `review_new` `/review/new`
- GET 쿼리: `name` 리뷰를 쓸 상품명
- POST `multipart/form-data`: `product_name, reviewer, rating, title, photo, content`
- 폼 `action`은 `url_for('review_new')`입니다.
- 성공: `review_done`으로 redirect. 실패: 같은 템플릿에 `form`, `errors`를 넘겨 400으로 다시 그림
- 로그인 상태면 `reviewer`는 `session['id']`를 씁니다.

### `review_done` `/review/done`
- 방금 등록한 리뷰 요약. 미리보기는 `session['last_review']`에서 꺼냅니다.
- BE에서 리뷰 상세가 실제 데이터를 보여 주게 되면 `review_detail`로 바로 보내도 됩니다.

### `auth_login` `/login`
- POST: `user_id, password` → 성공하면 `session['id']`를 넣고 `product_list`로 redirect
- 실패하면 flash 후 같은 화면

### `auth_signup` `/signup`
- POST: `user_id, password, password_confirm, email, auth_code, phone`(선택)
- 성공하면 `auth_login`으로 redirect

### `auth_logout` `/logout`
- `session`에서 `id`를 지우고 `product_list`로 redirect

## 현재 BE(`app.py`)와의 대응

BE 라우트를 아래처럼 바꾸면 FE 템플릿과 그대로 연결됩니다.

| 지금 BE 라우트 | 지금 경로 | → FE 라우트 | 경로 |
| --- | --- | --- | --- |
| `index` + `item_list` | `/`, `/list` | `product_list` | `/` |
| `view_item_detail` | `/view_detail/<name>/` | `product_detail` | `/product/<path:name>` |
| `reg_items` + `submit_item` | `/reg_items`, `/submit_item` (POST) | `product_new` | `/product/new` (GET, POST) |
| `review_list` | `/review` | `review_list` | `/review` |
| `reg_reviews` | `/reg_reviews` | `review_new` | `/review/new` (GET, POST) |
| `login` + `login_user` | `/login`, `/login_confirm` (POST) | `auth_login` | `/login` (GET, POST) |
| `signup` + `register_user` | `/signup`, `/signup_post` (POST) | `auth_signup` | `/signup` (GET, POST) |
| `logout_user` | `/logout` | `auth_logout` | `/logout` |

필드 이름이 서로 다른 곳 (BE 연동 때 한쪽으로 맞춰야 함)

| 화면 | FE 필드 | 지금 BE 필드 |
| --- | --- | --- |
| 로그인·회원가입 | `user_id`, `password` | `id`, `pw` |
| 회원가입 | (없음) | `nickname` 필수 |
| 회원가입 | `email`, `phone`, `auth_code` | (저장 안 함) |
| 상품 등록 | `description` | (저장 안 함) |
| 상품 등록 | (없음) | `email` |
| 상품 | `sale_status`, `kind` | (없음) |

## 링크 연결 현황

| 출발 | 링크 | 라우트 |
| --- | --- | --- |
| 헤더 | 로고, 상품·구해요·리뷰·채팅·마이 탭, 상품 등록, 로그인, 로그아웃 | `product_list` `wanted_list` `review_list` `chat_room` `my_index` `product_new` `auth_login` `auth_logout` |
| 상품 목록 | 상품 카드, 필터 폼, 페이지 번호 | `product_detail(name)` `product_list` |
| 상품 상세 | 판매자와 채팅, 판매자 리뷰 보기, 리뷰 쓰기(거래 완료), 약속 신청 폼 | `chat_room` `review_list(seller)` `review_new(name)` `product_reserve` |
| 상품 등록 | 폼, 취소 | `product_new` `product_list` |
| 리뷰 목록 | 리뷰 쓰기, 리뷰 카드 | `review_new` `review_detail(name)` |
| 리뷰 상세 | 리뷰 목록으로 | `review_list` |
| 리뷰 작성 | 폼, 취소 | `review_new` `review_list` |
| 리뷰 등록 완료 | 상품 둘러보기, 리뷰 목록으로 | `product_list` `review_list` |
| 로그인 | 폼, 회원가입 | `auth_login` `auth_signup` |
| 회원가입 | 폼, 로그인 | `auth_signup` `auth_login` |

리뷰 상세의 상품 카드 → 상품 상세 링크는 허제인 담당 작업으로 남겨 두었습니다. (`url_for('product_detail', name=상품명)`)
