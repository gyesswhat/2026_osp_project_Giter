# 0. 문서 목적

최종 발표 라이브 데모 전에 발표자 컴퓨터에서 명령 하나로 DB를 같은 상태로 만드는 방법을 적는다.

# 1. 실행 방법

```bash
cd apps/be
python demo/seed.py
```

실행하면 다음 순서로 진행한다.

1. 현재 DB 전체를 `demo/backup/<날짜시각>.json`으로 저장한다 (`backup/`은 git에 올리지 않는다).
2. 삭제할 노드와 항목 수를 보여 주고 `yes` 입력을 받는다. 다른 입력이면 DB를 바꾸지 않고 종료한다.
3. `users`, `products`, `auctions`, `bids`, `reviews`, `likes`, `wanted`, `offers` 노드를 삭제한다.
4. `data.json`을 저장한다.
5. `demo/photos/`의 파일을 `apps/fe/static/uploads/`로 복사한다.

주의: 실행하면 팀 DB의 위 8개 노드가 삭제된다. 되돌리려면 1번의 백업 파일을 사용한다. 다른 노드는 건드리지 않는다.

`pip install -r requirements.txt`와 `authentication/firebase_auth.json`이 준비되어 있어야 한다. 설정 파일이 없으면 `db`가 `None`이므로 안내만 출력하고 종료한다.

# 2. 데모 데이터

모든 계정의 비밀번호는 `boughtit2026`이다.

| 아이디 | 역할 | 이메일 |
| --- | --- | --- |
| `apple_ewha` | 판매자 | `apple_ewha@ewhain.net` |
| `ewhain_sw` | 판매자 | `ewhain_sw@ewhain.net` |
| `hanwoori_210` | 판매자 | `hanwoori_210@ewhain.net` |
| `kimewha07` | 구매자 | `kimewha07@ewhain.net` |

| 항목 | 내용 |
| --- | --- |
| 고정가 상품 8개 | 판매중 4, 예약중 1, 거래 완료 3 (거래 완료는 목록에 보이지 않고 리뷰 3개가 달려 있다) |
| 경매 진행 중 | `아이패드 에어 5세대 64GB` (제안 3건, 마감까지 약 3.3일) |
| 경매 마감 | `에어팟 2세대` (제안 3건, 마감 후 6시간 경과, 판매자 `ewhain_sw`가 수락과 거절을 아직 하지 않았다) |
| 찜 | 4개 |
| 구해요 | 글 3개, 제안이 있는 글은 `운영체제 공룡책 10판` (제안 2건) |

날짜는 `data.json`에 상대값(`days_ago`, `started_days_ago`, `due_in_days`)으로 적고 실행 시점 기준으로 계산한다. 그래서 언제 실행해도 진행 중인 경매는 진행 중이고, 마감된 경매는 마감 후 48시간 이내(`DECIDE_HOURS`)이다.

# 3. 사진 출처

사진은 아직 없다. `demo/photos/`에 파일을 넣고 `data.json`의 상품에 `img_path`를 적으면 실행할 때 복사한다. 사진마다 아래 표에 출처를 적는다.

| 파일 | 상품 | 출처 URL | 라이선스 |
| --- | --- | --- | --- |
