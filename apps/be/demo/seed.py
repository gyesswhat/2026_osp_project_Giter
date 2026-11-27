"""demo.seed: DB를 demo/data.json의 데모 상태로 초기화한다.

실행: (apps/be에서) python demo/seed.py
순서: 백업, 삭제 확인(yes), 8개 노드 삭제, data.json 저장, 사진 복사
"""

import hashlib
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# 1. 경로 설정
# python demo/seed.py로 실행하면 sys.path[0]이 demo/가 되므로, core와 routes를 import하려면 apps/be를 추가해야 한다.
DEMO_DIR = Path(__file__).resolve().parent
BE_DIR = str(DEMO_DIR.parent)
sys.path.insert(0, BE_DIR)

from core import db  # noqa: E402
from routes.auction import save_bid  # noqa: E402
from routes.auth import insert_user  # noqa: E402
from routes.product import (  # noqa: E402
    UPLOAD_DIR,
    get_auction,
    product_key,
    save_auction,
    save_product,
    start_auction,
)
from routes.review import save_review  # noqa: E402
from routes.wanted import save_offer, save_wanted  # noqa: E402

BACKUP_DIR = DEMO_DIR / "backup"
# routes가 db.child("...")로 읽고 쓰는 노드 전체이다 (grep 'db.child' apps/be/routes, 2026-11-27)
NODES = ("users", "products", "auctions", "bids", "reviews", "likes", "wanted", "offers")


def main():
    if db is None:
        print("Firebase에 연결하지 못했다. 원인은 위 출력을 확인한다.")
        sys.exit(1)

    snapshot = db.get().val() or {}
    backup_path = save_backup(snapshot)
    if not confirm_delete(snapshot, backup_path):
        print("yes가 아니므로 DB를 바꾸지 않고 종료한다.")
        return

    delete_nodes()
    data_text = (DEMO_DIR / "data.json").read_text(encoding="utf-8")
    data = json.loads(data_text)
    seed(data)
    copy_photos()
    print("데모 데이터를 저장했다.")


# 2. 백업과 삭제
def save_backup(snapshot):
    """DB 전체를 backup/<날짜시각>.json으로 저장하고 파일 경로를 반환한다."""
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"{stamp}.json"
    text = json.dumps(snapshot, ensure_ascii=False, indent=2)
    backup_path.write_text(text, encoding="utf-8")
    return backup_path


def confirm_delete(snapshot, backup_path):
    """삭제할 노드와 항목 수를 보여 주고, yes를 입력했는지 반환한다."""
    print(f"백업 파일: {backup_path}")
    print("삭제할 노드와 항목 수:")
    for node in NODES:
        entries = snapshot.get(node, {})
        count = len(entries)
        print(f"  /{node}: {count}개")
    answer = input("삭제하고 데모 데이터를 저장하려면 yes를 입력한다: ")
    return answer.strip() == "yes"


def delete_nodes():
    # pyrebase의 db.child()는 같은 객체에 경로를 누적하므로 노드마다 체인 한 줄로 실행한다
    for node in NODES:
        db.child(node).remove()


# 3. 데이터 저장
def seed(data):
    now = datetime.now().astimezone()
    likes = Counter(like["product"] for like in data["likes"])
    seed_users(data["users"])
    seed_products(data["products"], now, likes)
    seed_auctions(data["auctions"], now, likes)
    seed_likes(data["likes"], now)
    seed_reviews(data, now)
    seed_wanted(data["wanted"], now)


def seed_users(users):
    for user in users:
        pw_hash = get_pw_hash(user["password"])
        insert_user(user["id"], pw_hash, user["email"])


def get_pw_hash(password):
    """routes/auth.py의 로그인과 같은 해시이다 (SHA-256, schema.dbml users.pw_hash)"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def seed_products(items, now, likes):
    for item in items:
        created_at = get_stored_time(now, item["days_ago"])
        product = make_product(item["product"], created_at, likes)
        save_product(product)


def make_product(fields, created_at, likes):
    """products.likes는 likes 행 수와 같아야 하므로 data.json의 likes에서 센다 (schema.dbml products.likes)"""
    return {**fields, "likes": likes[fields["name"]], "created_at": created_at}


def seed_auctions(items, now, likes):
    for item in items:
        fields = item["product"]
        created_at = get_stored_time(now, item["started_days_ago"])
        started_at = datetime.fromisoformat(created_at)
        # product_new와 같은 순서로 경매 정보를 상품보다 먼저 저장한다. 등록 시각이 경매 시작 시각이다
        start_auction(fields["name"], item["duration_days"], started_at)
        product = make_product(fields, created_at, likes)
        save_product(product)
        seed_bids(fields["name"], item["bids"], now)


def seed_bids(name, bids, now):
    """제안을 저장하고 경매 정보의 top_price, bid_count를 auction_bid처럼 갱신한다."""
    for bid in bids:
        created_at = get_stored_time(now, bid["days_ago"])
        stored = {"bidder": bid["bidder"], "price": bid["price"], "created_at": created_at}
        save_bid(name, stored)
    auction = get_auction(name)
    top_price = max(bid["price"] for bid in bids)
    save_auction({**auction, "top_price": top_price, "bid_count": len(bids)})


def seed_likes(likes, now):
    # toggle_like는 flash를 호출하므로 요청 밖에서 쓸 수 없다. 같은 경로와 값으로 직접 저장한다 (/likes/{user_id}/{key})
    for like in likes:
        created_at = get_stored_time(now, like["days_ago"])
        key = product_key(like["product"])
        db.child("likes").child(like["user"]).child(key).set({"created_at": created_at})


def seed_reviews(data, now):
    sellers = get_sellers(data)
    for item in data["reviews"]:
        created_at = get_stored_time(now, item["days_ago"])
        review = make_review(item, sellers[item["product_name"]], created_at)
        save_review(review)


def get_sellers(data):
    """상품명에서 판매자를 찾는 dict. reviews.seller는 products.seller를 복사한다 (schema.dbml reviews)"""
    fields = [item["product"] for item in data["products"] + data["auctions"]]
    return {product["name"]: product["seller"] for product in fields}


def make_review(item, seller, created_at):
    return {
        "product_name": item["product_name"],
        "reviewer": item["reviewer"],
        "seller": seller,
        "rating": item["rating"],
        "title": item["title"],
        "content": item["content"],
        "photo": "",
        "created_at": created_at,
    }


def seed_wanted(items, now):
    for item in items:
        created_at = get_stored_time(now, item["days_ago"])
        due_date = now.date() + timedelta(days=item["due_in_days"])
        post = make_wanted_post(item, created_at, due_date)
        wanted_id = save_wanted(post)
        seed_offers(wanted_id, item["offers"], now)


def make_wanted_post(item, created_at, due_date):
    """wanted_new가 저장하는 필드와 같다. 제안을 고른 글이 없으므로 state는 open이다."""
    fields = item["post"]
    return {
        **fields,
        "places": {place: True for place in fields["places"]},
        "due_date": due_date.isoformat(),
        "img_path": "",
        "state": "open",
        "picked_offer_id": "",
        "offer_count": len(item["offers"]),
        "created_at": created_at,
    }


def seed_offers(wanted_id, offers, now):
    for offer in offers:
        created_at = get_stored_time(now, offer["days_ago"])
        stored = {
            "seller": offer["seller"],
            "price": offer["price"],
            "description": offer["description"],
            "place": offer["place"],
            "img_path": "",
            "created_at": created_at,
        }
        save_offer(wanted_id, stored)


def get_stored_time(now, days_ago):
    """now에서 days_ago일 전의 시각을 DB 저장 형식(ISO 8601, 초 단위)으로 반환한다 (schema.dbml)"""
    moment = now - timedelta(days=days_ago)
    return moment.isoformat(timespec="seconds")


# 4. 사진 복사
def copy_photos():
    """demo/photos/의 파일을 UPLOAD_DIR로 복사한다. [!.]*는 .gitkeep을 제외한다."""
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    photos = sorted((DEMO_DIR / "photos").glob("[!.]*"))
    for photo in photos:
        shutil.copy2(photo, UPLOAD_DIR)


if __name__ == "__main__":
    main()
