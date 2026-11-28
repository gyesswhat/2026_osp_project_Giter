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
- `/product/new` `/product/reserve` `/product/like` `/review/done`처럼 고정 경로가 `/product/<path:name>` `/review/<path:name>`보다 먼저 잡히므로, 상품명 `new` `reserve` `like` `done`은 등록할 수 없게 막습니다.
- 로그인 여부는 `session['id']`로 판단합니다.

## 경로표

상태: **화면** 템플릿까지 있음 · **미리보기** `preview.py`에만 처리가 있음 · **예정** 화면이나 처리가 아직 없음

| 화면 | 메서드 | 경로 | 라우트 함수 | 템플릿 | 상태 |
| --- | --- | --- | --- | --- | --- |
| 상품 목록 (홈) | GET | `/` | `product_list` | `product/list.html` | 화면 |
| 상품 상세 | GET | `/product/<path:name>` | `product_detail` | `product/detail.html` | 화면 |
| 상품 등록 | GET, POST | `/product/new` | `product_new` | `product/new.html` | 화면 |
| 약속 신청 | POST | `/product/reserve` | `product_reserve` | (없음, 상세로 redirect) | 미리보기 |
| 찜 토글 | POST | `/product/like` | `product_like` | (없음, 상세로 redirect) | 화면 (상품 상세 찜 버튼 폼 연결, #28) |
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
| 경매 상세 | GET | `/auction/detail/<path:name>` | `auction_detail` | `auction/detail.html` | 예정 (BE 구현, 화면은 #31) |
| 가격 제안 | POST | `/auction/bid` | `auction_bid` | (redirect) | BE 구현 |
| 경매 마감 | GET | `/auction/end/<path:name>` | `auction_end` | `auction/end.html` | 예정 (BE는 501 스텁, #40에서 구현) |

예정 화면의 경로는 자리만 잡아 둔 것입니다. 상세 화면(구해요·경매)은 화면을 만들 때 위 규칙대로 경로 파라미터를 정해서 이 표를 고칩니다.

## 화면별로 주고받는 값

### `product_list` `/`
- 쿼리: `q` 검색어, `sort` new·like·low·high, `sale_status` all·sale·hold, `kind` all·fixed·bid, `price_min`·`price_max` 원 단위(없으면 제한 없음), `page` 1부터
- 템플릿에 넘길 값: `products`(현재 페이지 상품 dict 목록), `total`, `page`, `total_pages`
- 거래 완료(`sale_status == 'done'`) 상품은 목록에서 뺍니다.
- 경매 상품(`kind == 'bid'`)에는 카드가 쓰는 값을 함께 넣습니다 (schema.dbml `auctions`, 자세한 내용은 `components/_product_card.html` 주석)
  - `price`: 지금 최고 제안가 `top_price` (제안이 없으면 0)
  - `bid_count`: 제안 수
  - `end_at`: 마감 시각 ISO 문자열. 예) `2026-11-25T14:30:00+09:00`. 남은 시간은 화면에서 계산합니다
  - `closed`: 마감 여부 (요청 시점에 `end_at`과 비교)
- 카드 링크: 고정가 → `product_detail(name)`, 진행 중인 경매 → `auction_detail(name)`, 마감된 경매 → `auction_end(name)`

### `product_detail` `/product/<path:name>`
- 템플릿에 넘길 값: `product`(dict), `liked`(선택), `image`(선택)
- 상품이 없으면 404
- `product`의 필드는 `product/detail.html` 맨 위 주석 참고 (`name, seller, price, address, status, description, img_path, sale_status, kind, date, likes, places, slots`)
- 찜 버튼: `product_like`로 POST (`name`). `liked`가 참이면 `♥ 찜한 물건`, 아니면 `♡ 찜하기`로 보입니다
- 리뷰 쓰기 버튼: 판매 상태와 상관없이 판매자가 아닌 사람에게 보입니다 (`url_for('review_new', name=p.name)`). 필수 데모(B가 A의 상품에 리뷰 작성)를 위해 거래 완료 조건을 뺐습니다 (#28)
- 판매자 본인(`session['id'] == product.seller`)에게는 찜·리뷰 쓰기 버튼을 숨깁니다. BE도 본인 상품의 찜·리뷰를 막습니다
- 로그인하지 않았으면 찜·리뷰 쓰기를 누를 때 BE가 `auth_login`으로 보냅니다

### `product_new` `/product/new`
- POST `multipart/form-data`: `seller, name, kind, price, duration, address, status, description, picture`
  - `kind`: 가격 정하는 방식. `fixed`(가격 정해서 올리기, 기본값) | `bid`(가격 제안 받기)
  - `price`: `kind=fixed`일 때만 보냅니다. 숫자만 (쉼표 없음)
  - `duration`: 제안 받는 기간(일) `1` `3` `5` `7`. `kind=bid`일 때만 보냅니다 (schema.dbml `auctions.duration_days`)
  - 방식에 맞지 않는 칸은 화면에서 disabled로 바꿔 보내지 않습니다
- 성공: `product_detail`로 redirect + flash `상품을 등록했어요.` (`bid`이면 `상품을 등록했어요. N일 동안 제안을 받아요.`)
- 실패: 같은 템플릿에 `form`(입력값), `errors`(필드별 메시지 dict)를 넘겨 다시 그림
- 같은 상품명이 이미 있거나 `new` `reserve` `like` `done`이면 `errors['name']`
- 방식·가격·기간 오류는 `errors['kind']`, `errors['price']`, `errors['duration']`

### `product_reserve` `/product/reserve`
- POST: `name`(상품명), `place`(장소 칩 순번), `slot`(시간 칩 순번)
- 처리 후 `product_detail`로 redirect + flash

### `product_like` `/product/like`
- POST: `name`(상품명)
- 로그인 필요. 비로그인이면 flash 후 `auth_login`으로 redirect
- 찜하지 않은 상품이면 찜을 추가하고, 이미 찜했으면 취소합니다. `products.likes`도 함께 1 늘리거나 줄입니다.
- 없는 상품이면 404, 자기 상품이면 flash 후 `product_detail`로 redirect
- 처리 후 `product_detail`로 redirect + flash (`찜했어요.` / `찜을 취소했어요.`)
- 상품 상세의 찜 버튼은 `<form method="post" action="{{ url_for('product_like') }}">` 안에 `<input type="hidden" name="name" value="{{ p.name }}">`를 넣어 보냅니다.

### `auction_detail` `/auction/detail/<path:name>`
- 경매 상품이 아니거나 없는 상품이면 404
- 템플릿에 넘길 값
  - `product`(dict): 상품. `price`는 지금 최고 제안가입니다
  - `auction`(dict): `end_at`(마감 시각 ISO 문자열), `top_price`(최고 제안가, 없으면 0), `bid_count`(제안 수), `duration_days`, `closed`(마감 여부)
  - `bids`(목록, 금액이 높은 순): `bidder`(앞 두 글자만 남긴 아이디. 예: `po***`), `price`, `date`(예: `11.20 14:30`)
  - `my_bid`: 로그인한 사용자의 가장 높은 제안(`bids`의 항목과 같은 모양). 없으면 `None`
  - `min_price`: 지금 제안할 수 있는 최소 금액 (`top_price` + 5,000)
- 남은 시간은 목록 카드처럼 `auction.end_at`으로 화면에서 계산합니다

### `auction_bid` `/auction/bid`
- POST: `name`(상품명), `price`(제안 금액. 쉼표가 있어도 됩니다)
- 로그인하지 않았으면 `auth_login`으로 redirect. 경매 상품이 아니거나 없는 상품이면 404
- 그 외에는 `auction_detail`로 redirect + flash. 실패한 경우(본인 상품, 마감 후, `min_price` 미만)는 flash 분류가 `error`입니다

### `review_list` `/review`
- 쿼리: `seller` 판매자 ID(있으면 그 판매자가 받은 리뷰만, 판매자 바 표시), `page` 페이지 번호
- 상품 상세의 '판매자 리뷰 보기'가 `url_for('review_list', seller=p.seller)`로 들어옵니다.
- BE PR #60에서 전달하는 값:
  - `reviews`: 현재 페이지의 리뷰 목록 (페이지당 최대 10개)
  - `total`: 전체 검색 결과의 리뷰 수
  - `page`: 현재 페이지 번호
  - `total_pages`: 전체 페이지 수
  - `seller`: 선택된 판매자 ID
  - `seller_info`: 판매자 필터 적용 시 `id`, `avg_rating`, `count` 포함
- FE는 `reviews`를 반복하여 카드를 표시하고, `review_detail`로 연결합니다.
- 리뷰가 없으면 빈 화면 안내를 표시하고, `page`와 `total_pages`로 페이지네이션을 구성합니다.

### `review_detail` `/review/<path:name>`
- `name`은 리뷰를 쓴 상품의 상품명입니다. (리뷰는 상품명 키로 저장합니다. 상품 하나에 리뷰 하나)
- BE PR #60에서 전달하는 값:
  - `review`: `product_name`, `reviewer`, `seller`, `rating`, `title`, `content`, `photo`, `created_at`, `date`
  - `product`: 해당 리뷰와 연결된 상품 정보
- FE는 `review`를 사용해 별점, 제목, 작성자, 날짜, 본문을 표시합니다.
- `product`를 사용해 거래 상품 정보를 표시합니다.
- 해당 상품의 리뷰가 없으면 BE에서 404를 반환합니다.

### `review_new` `/review/new`
- GET 쿼리: `name` 리뷰를 쓸 상품명
- POST `multipart/form-data`: `product_name, reviewer, rating, title, photo, content`
- 폼 `action`은 `url_for('review_new')`입니다.
- 성공: `review_done`으로 redirect. 실패: 같은 템플릿에 `form`, `errors`를 넘겨 400으로 다시 그림
- 로그인 상태면 `reviewer`는 `session['id']`를 씁니다.

### `review_done` `/review/done`
- 방금 등록한 리뷰 요약. BE는 `session['last_review']`에 상품명을 저장하고, 그 상품명으로 DB에서 리뷰를 읽어 `review`로 넘깁니다.
- BE에서 리뷰 상세가 실제 데이터를 보여 주게 되면 `review_detail`로 바로 보내도 됩니다.

### `auth_login` `/login`
- POST: `user_id, password` → 성공하면 `session['id']`를 넣고 `product_list`로 redirect
- 실패하면 flash 후 같은 화면

### `auth_signup` `/signup`
- POST: `user_id, password, password_confirm, email, auth_code, phone`(선택)
- 성공하면 `auth_login`으로 redirect
- 실패: 같은 템플릿에 `form`(`user_id, email, phone`), `errors`(`user_id, password, password_confirm, email, auth_code, general`)를 넘겨 400으로 다시 표시
- 메일 인증: `static/js/auth.js`가 '인증 요청'은 `auth_send_code`(`POST /signup/code`, 필드 `email`), '코드 확인'은 `auth_verify_code`(`POST /signup/verify`, 필드 `email, auth_code`)로 보내고, 응답 본문(안내 문구)을 그대로 표시합니다. 응답이 200이 아니면 오류로 표시합니다
- 인증을 끝낸 뒤 다른 오류로 다시 표시할 때는 템플릿이 `session['email_verification']`의 `verified, email`을 읽어 인증 완료 상태를 유지합니다
- 아이디 중복 확인 버튼은 없습니다. 가입하기를 누르면 `errors.user_id`로 표시합니다

### `auth_logout` `/logout`
- `session`에서 `id`를 지우고 `product_list`로 redirect

## FE와 BE 필드 이름 대응 (#24, #28)

BE(`apps/be`)는 이 문서의 라우트 함수 이름과 경로를 그대로 쓰므로, 예전 실습용 루트 `app.py`와의 라우트 대응표는 지웠습니다.
예전에 이름이 달랐던 필드는 아래처럼 정리됐습니다.

| 화면 | FE 필드 | BE | 상태 |
| --- | --- | --- | --- |
| 로그인·회원가입 | `user_id`, `password` | 같은 이름으로 받음 (예전 `id`, `pw`) | 맞춤 |
| 회원가입 | `nickname` 없음 | `nickname`을 받지 않음 | 맞춤 |
| 회원가입 | `email`, `phone` | 저장함 | 맞춤 |
| 회원가입 | `auth_code` | 아직 확인하지 않음 (BE TODO) | BE 작업 남음 |
| 상품 등록 | `description` | 저장함 | 맞춤 |
| 상품 등록 | `email` 없음 | `email`을 받지 않음 | 맞춤 |
| 상품 등록 | `seller` | 받지 않고 `session['id']`를 씀. 로그인해야 등록 화면에 들어갈 수 있어 FE 칸은 읽기 전용으로 보임 | 맞춤 |
| 상품 | `sale_status`, `kind` | 저장함 | 맞춤 |
| 상품 상세 | 찜 버튼 | `product_like` (POST `name`) | 맞춤 (#28) |
| 상품 상세 | 리뷰 쓰기 버튼 조건 | BE는 거래 완료를 확인하지 않고 본인 상품·중복 리뷰만 막음 | 맞춤 (#28) |
| 리뷰 작성 | `product_name, rating, title, content, photo` | 같은 이름으로 받음. `reviewer`는 보내도 BE가 `session['id']`를 씀 | 맞춤 |
| 리뷰 등록 완료 | `review`의 `reviewer, product_name, rating, title, content, photo` | 같은 이름으로 저장함 | 맞춤 |

## 링크 연결 현황

| 출발 | 링크 | 라우트 |
| --- | --- | --- |
| 헤더 | 로고, 상품·구해요·리뷰·채팅·마이 탭, 상품 등록, 로그인, 로그아웃 | `product_list` `wanted_list` `review_list` `chat_room` `my_index` `product_new` `auth_login` `auth_logout` |
| 상품 목록 | 상품 카드(고정가·경매·마감된 경매), 필터 폼, 페이지 번호 | `product_detail(name)` `auction_detail(name)` `auction_end(name)` `product_list` |
| 상품 상세 | 판매자와 채팅, 찜(폼), 판매자 리뷰 보기, 리뷰 쓰기(판매자 본인 제외), 약속 신청 폼 | `chat_room` `product_like` `review_list(seller)` `review_new(name)` `product_reserve` |
| 상품 등록 | 폼, 취소 | `product_new` `product_list` |
| 리뷰 목록 | 리뷰 쓰기, 리뷰 카드 | `review_new` `review_detail(name)` |
| 리뷰 상세 | 리뷰 목록으로 | `review_list` |
| 리뷰 작성 | 폼, 취소 | `review_new` `review_list` |
| 리뷰 등록 완료 | 상품 둘러보기, 리뷰 목록으로 | `product_list` `review_list` |
| 로그인 | 폼, 회원가입 | `auth_login` `auth_signup` |
| 회원가입 | 폼, 로그인 | `auth_signup` `auth_login` |

리뷰 상세의 상품 카드 → 상품 상세 링크는 허제인 담당 작업으로 남겨 두었습니다. (`url_for('product_detail', name=상품명)`)
