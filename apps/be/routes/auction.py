"""경매 라우트: auction_detail, auction_bid, auction_end, auction_decide, auction_reopen

경매 정보(/auctions)는 routes/product.py의 저장소 함수로 읽고 쓴다. 이 파일은 제안(/bids)을 저장한다.
db가 None이면(Firebase 설정 파일 없음) dummy.PREVIEW_BIDS를 제안 저장소로 사용한다.
"""

from datetime import datetime, timedelta

from flask import abort, flash, redirect, render_template, request, session, url_for

from core import app, db, to_int
from dummy import PREVIEW_BIDS
from routes.product import (
    get_auction,
    get_stored_product,
    is_closed,
    product_key,
    save_auction,
    start_auction,
    update_product,
    validate_duration,
    validate_price,
    with_auction,
)

# 새 제안은 최고 제안가보다 이 금액 이상 높아야 한다. 첫 제안의 최소 금액이기도 하다 (schema.dbml bids)
BID_STEP = 5000
# 마감 후 판매자가 결정할 수 있는 시간. 지나면 rejected로 처리한다 (schema.dbml auctions)
DECIDE_HOURS = 48
# 판매자가 고를 수 있는 결정 (schema.dbml auction_decision에서 pending을 뺀 값)
DECISIONS = ("accepted", "rejected")


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
    """경매 마감 화면. 로그인 필요. 마감 전이면 경매 상세로 redirect"""
    user_id = session.get("id")
    if user_id is None:
        flash("경매 결과를 보려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))

    product, auction = get_bid_product(name)
    if not is_closed(auction):
        return redirect(url_for("auction_detail", name=name))

    bids = load_bids(name)
    public_bids = [public_bid(bid) for bid in bids]
    # 최고 제안자의 아이디 전체는 판매자에게만 공개한다 (schema.dbml bids)
    if product["seller"] == user_id and len(bids) > 0:
        public_bids[0]["bidder"] = bids[0]["bidder"]
    deadline = decide_deadline(auction)
    auction = reject_if_overdue(auction)
    return render_template(
        "auction/end.html",
        product=product,
        auction={**auction, "closed": True},
        bids=public_bids,
        deadline=deadline.isoformat(timespec="seconds"),
    )


@app.route("/auction/decide", methods=["POST"])
def auction_decide():
    """판매자의 수락, 거절. 폼: name, decision. auction_end로 redirect"""
    user_id = session.get("id")
    if user_id is None:
        flash("경매를 결정하려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))

    name = request.form.get("name", "")
    product, auction = get_bid_product(name)
    decision = request.form.get("decision")

    if product["seller"] != user_id:
        flash("판매자만 결정할 수 있어요.", "error")
    elif not is_closed(auction):
        flash("마감 전에는 결정할 수 없어요.", "error")
    elif reject_if_overdue(auction)["decision"] != "pending":
        flash("이미 결정한 경매예요.", "error")
    elif decision not in DECISIONS:
        flash("수락과 거절 중에서 골라 주세요.", "error")
    elif decision == "accepted" and auction["bid_count"] == 0:
        # accepted는 최고 제안자와 거래하는 결정이다 (schema.dbml auctions)
        flash("제안이 없는 경매는 수락할 수 없어요.", "error")
    elif decision == "accepted":
        save_decision(auction, "accepted")
        # 약속이 잡힌 상품의 판매 상태는 hold이다 (schema.dbml reservations). 약속 저장은 약속 신청(#41)에서 추가한다
        update_product(name, {"sale_status": "hold"})
        flash("거래를 확정했어요.")
    else:
        save_decision(auction, "rejected")
        flash("제안을 거절했어요. 다시 제안을 받거나 가격을 정해서 올릴 수 있어요.")
    return redirect(url_for("auction_end", name=name))


@app.route("/auction/reopen", methods=["POST"])
def auction_reopen():
    """거절한 경매를 다시 올린다. 폼: name, mode(bid | fixed), duration_days(bid), price(fixed)"""
    user_id = session.get("id")
    if user_id is None:
        flash("상품을 다시 올리려면 로그인해 주세요.", "error")
        return redirect(url_for("auth_login"))

    name = request.form.get("name", "")
    product, auction = get_bid_product(name)
    # mode는 products.kind와 같은 값을 쓴다 (schema.dbml product_kind)
    mode = request.form.get("mode")
    duration_days = to_int(request.form.get("duration_days"))
    price = to_int(request.form.get("price"))

    if product["seller"] != user_id:
        flash("판매자만 다시 올릴 수 있어요.", "error")
    elif reject_if_overdue(auction)["decision"] != "rejected":
        flash("거절한 경매만 다시 올릴 수 있어요.", "error")
    elif mode == "bid":
        return reopen_as_bid(name, duration_days)
    elif mode == "fixed":
        return reopen_as_fixed(name, price)
    else:
        flash("다시 올리는 방식을 골라 주세요.", "error")
    return redirect(url_for("auction_end", name=name))


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


def clear_bids(name):
    if db is None:
        PREVIEW_BIDS.pop(name, None)
        return
    db.child("bids").child(product_key(name)).remove()


# 3. 마감 후 처리 (schema.dbml auctions)
def reopen_as_bid(name, duration_days):
    """다시 제안 받기. 제안을 비우고 마감 시각을 다시 정한다"""
    duration_error = validate_duration(duration_days)
    if duration_error is not None:
        flash(duration_error, "error")
        return redirect(url_for("auction_end", name=name))
    clear_bids(name)
    start_auction(name, duration_days, datetime.now().astimezone())
    flash(f"다시 올렸어요. {duration_days}일 동안 제안을 받아요.")
    return redirect(url_for("auction_detail", name=name))


def reopen_as_fixed(name, price):
    """가격 정해서 다시 올리기. 상품을 고정가 상품으로 바꾼다"""
    price_error = validate_price(price)
    if price_error is not None:
        flash(price_error, "error")
        return redirect(url_for("auction_end", name=name))
    update_product(name, {"kind": "fixed", "price": price})
    flash("가격을 정해서 다시 올렸어요.")
    return redirect(url_for("product_detail", name=name))


def reject_if_overdue(auction):
    """결정 기한이 지난 pending 경매를 rejected로 저장해 반환한다. 그 외에는 그대로 반환한다.

    스케줄러 없이 요청 시점의 현재 시각과 결정 기한을 비교한다.
    """
    if auction["decision"] != "pending" or datetime.now().astimezone() <= decide_deadline(auction):
        return auction
    return save_decision(auction, "rejected")


def decide_deadline(auction):
    """판매자가 결정할 수 있는 마지막 시각"""
    return datetime.fromisoformat(auction["end_at"]) + timedelta(hours=DECIDE_HOURS)


def save_decision(auction, decision):
    decided_at = datetime.now().astimezone().isoformat(timespec="seconds")
    decided = {**auction, "decision": decision, "decided_at": decided_at}
    save_auction(decided)
    return decided
