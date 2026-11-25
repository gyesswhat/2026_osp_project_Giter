"""경매 라우트: auction_detail, auction_bid, auction_end

경매 정보(/auctions)는 routes/product.py의 저장소 함수로 읽고 쓴다. 이 파일은 제안(/bids)을 저장한다.
db가 None이면(Firebase 설정 파일 없음) dummy.PREVIEW_BIDS를 제안 저장소로 사용한다.
"""

from datetime import datetime

from flask import abort, flash, redirect, render_template, request, session, url_for

from core import app, db, to_int
from dummy import PREVIEW_BIDS
from routes.product import get_auction, get_stored_product, is_closed, product_key, save_auction, with_auction

# 새 제안은 최고 제안가보다 이 금액 이상 높아야 한다. 첫 제안의 최소 금액이기도 하다 (schema.dbml bids)
BID_STEP = 5000


@app.route("/auction/detail/<path:name>")
def auction_detail(name):
    """경매 상세. 경매 상품이 아니거나 없으면 404"""
    product, auction = get_bid_product(name)
    bids = load_bids(name)
    user_id = session.get("id")
    # bids는 금액이 높은 순이므로 첫 번째가 이 사용자의 가장 높은 제안이다
    my_bids = [bid for bid in bids if bid["bidder"] == user_id]
    return render_template(
        "auction/detail.html",
        product=product,
        auction={**auction, "closed": is_closed(auction)},
        bids=[public_bid(bid) for bid in bids],
        my_bid=public_bid(my_bids[0]) if len(my_bids) > 0 else None,
        min_price=auction["top_price"] + BID_STEP,
    )


@app.route("/auction/bid", methods=["POST"])
def auction_bid():
    """가격 제안 등록. 폼: name, price → 경매 상세로 redirect"""
    user_id = session.get("id")
    if user_id is None:
        flash("가격을 제안하려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))

    name = request.form.get("name", "")
    product, auction = get_bid_product(name)
    price = to_int(request.form.get("price"))
    min_price = auction["top_price"] + BID_STEP

    if product["seller"] == user_id:
        flash("내가 올린 상품에는 제안할 수 없어요.", "error")
    elif is_closed(auction):
        flash("마감된 경매에는 제안할 수 없어요.", "error")
    elif price is None or price < min_price:
        flash(f"{min_price:,}원 이상으로 제안해 주세요.", "error")
    else:
        # ponytail: 읽은 뒤 쓰는 구조라 두 사람이 동시에 제안하면 낮은 금액이 최고가로 남을 수 있다. 문제가 되면 트랜잭션으로 바꾼다
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        save_bid(name, {"bidder": user_id, "price": price, "created_at": created_at})
        save_auction({**auction, "top_price": price, "bid_count": auction["bid_count"] + 1})
        flash(f"{price:,}원을 제안했어요.")
    return redirect(url_for("auction_detail", name=name))


@app.route("/auction/end/<path:name>")
def auction_end(name):
    # 마감 판정과 수락/거절은 #40에서 구현한다
    abort(501)


# 1. 조회
def get_bid_product(name):
    """(상품, 경매 정보)를 반환한다. 상품이 없거나 경매 상품이 아니면 404"""
    product = get_stored_product(name)
    if product is None or product["kind"] != "bid":
        abort(404)
    auction = get_auction(name)
    return with_auction(product, auction), auction


def public_bid(bid):
    """화면에 넘기는 제안. 제안자 아이디는 앞 두 글자만 남긴다 (schema.dbml bids.bidder). date 예: 11.20 14:30"""
    created = datetime.fromisoformat(bid["created_at"])
    return {"bidder": bid["bidder"][:2] + "***", "price": bid["price"], "date": created.strftime("%m.%d %H:%M")}


# 2. 제안 저장소 (Firebase /bids/{key}/{push 키} 또는 더미)
def load_bids(name):
    """금액이 높은 순으로 정렬한 제안 목록"""
    if db is None:
        bids = PREVIEW_BIDS.get(name, [])
    else:
        stored = db.child("bids").child(product_key(name)).get().val() or {}
        bids = stored.values()
    return sorted(bids, key=lambda bid: bid["price"], reverse=True)


def save_bid(name, bid):
    if db is None:
        PREVIEW_BIDS.setdefault(name, []).append(bid)
        return
    db.child("bids").child(product_key(name)).push(bid)
