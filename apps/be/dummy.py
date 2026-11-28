"""더미 데이터. DB 로직으로 교체한 뒤 이 파일을 삭제한다."""

from datetime import datetime, timedelta

# kind: fixed(가격 고정) | bid(가격 제안). sale_status: sale/hold/done
PREVIEW_PRODUCTS = [
    {
        "name": "컴퓨터구조 및 설계 5판",
        "seller": "baekkot21",
        "price": "18000",
        "address": "ECC 앞",
        "status": "상",
        "likes": 12,
        "sale_status": "sale",
        "kind": "fixed",
        "date": "2026.10.06",
        "description": "지난 학기 컴퓨터구조 수업에서 쓴 교재입니다.",
        "places": [
            {"building": "ECC", "detail": "8번 출구 앞"},
            {"building": "중앙도서관", "detail": "1층 로비"},
        ],
        "slots": ["10.12 (월) 13:00", "10.12 (월) 15:00", "10.13 (화) 12:00"],
    },
    {
        "name": "아이패드 에어 5세대 64GB",
        "seller": "apple_ewha",
        "price": 435000,
        "address": "포스코관",
        "status": "최상",
        "likes": 31,
        "sale_status": "sale",
        "kind": "bid",
        "date": "2026.10.06",
    },
    {
        "name": "이화 과잠 M 사이즈",
        "seller": "gwajam_22",
        "price": 25000,
        "address": "학생문화관",
        "status": "상",
        "likes": 18,
        "sale_status": "hold",
        "kind": "fixed",
        "date": "2026.10.05",
    },
    {
        "name": "로지텍 K380 무선 키보드",
        "seller": "ewhain_sw",
        "price": 22000,
        "address": "아산공학관",
        "status": "중",
        "likes": 9,
        "sale_status": "sale",
        "kind": "fixed",
        "date": "2026.10.05",
        "description": "1년 정도 쓴 무선 키보드입니다.",
    },
    {
        "name": "기숙사용 미니 냉장고",
        "seller": "hanwoori_210",
        "price": 40000,
        "address": "한우리집",
        "status": "상",
        "likes": 24,
        "sale_status": "sale",
        "kind": "fixed",
        "date": "2026.10.04",
    },
    {
        "name": "전기 주전자 1L",
        "seller": "ehouse_tea",
        "price": 8000,
        "address": "이하우스",
        "status": "하",
        "likes": 7,
        "sale_status": "done",
        "kind": "fixed",
        "date": "2026.10.02",
    },
]

# 경매 정보와 제안. 키는 상품명이다. 마감 시각은 서버를 시작한 시각 + 3일로 계산한다
PREVIEW_AUCTIONS = {
    "아이패드 에어 5세대 64GB": {
        "product_name": "아이패드 에어 5세대 64GB",
        "duration_days": 3,
        "end_at": (datetime.now().astimezone() + timedelta(days=3)).isoformat(timespec="seconds"),
        "top_price": 435000,
        "bid_count": 2,
        "decision": "pending",
    },
}
PREVIEW_BIDS = {
    "아이패드 에어 5세대 64GB": [
        {"bidder": "kimewha07", "price": 430000, "created_at": "2026-11-20T12:15:00+09:00"},
        {"bidder": "abcd12", "price": 435000, "created_at": "2026-11-20T14:30:00+09:00"},
    ],
}


def find_product(name):
    return next((p for p in PREVIEW_PRODUCTS if p["name"] == name), None)
