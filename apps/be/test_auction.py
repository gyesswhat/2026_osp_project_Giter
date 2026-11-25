"""경매 라우트 확인 (더미 데이터 경로)

실행: (apps/be에서) python test_auction.py
Firebase에 쓰지 않도록 db를 None으로 바꾸고, 사진은 임시 폴더에 저장한다.
auction/detail.html 없이도 실행할 수 있도록 render_template을 바꿔 템플릿에 넘기는 값만 확인한다.
"""

import io
import tempfile
from datetime import datetime, timedelta

from core import app
from dummy import PREVIEW_AUCTIONS, PREVIEW_BIDS, PREVIEW_PRODUCTS
# 헤더의 url_for가 찾는 라우트를 모두 등록한다 (app.py와 같은 import)
from routes import auction, auth, chat, my, product, review, wanted  # noqa: F401

product.db = None
auction.db = None
product.UPLOAD_DIR = tempfile.mkdtemp()
client = app.test_client()

NAME = "맥북 에어 M2"
rendered = {}


def fake_render(template, **context):
    rendered.clear()
    rendered.update(context, template=template)
    return "ok"


auction.render_template = fake_render


def login(user_id):
    with client.session_transaction() as sess:
        sess["id"] = user_id


def register(**fields):
    form = {"name": NAME, "kind": "bid", "duration": "3", "address": "ECC", "status": "상", "description": "설명"}
    form.update(fields)
    form.setdefault("picture", (io.BytesIO(b"\x89PNG"), "사진.png"))
    return client.post("/product/new", data=form, content_type="multipart/form-data")


def bid(price, name=NAME):
    return client.post("/auction/bid", data={"name": name, "price": price})


def check_new():
    login("seller")
    count = len(PREVIEW_PRODUCTS)
    # 오류 dict만 확인한다. 목록 화면 확인(check_closed)에서 실제 템플릿을 쓰도록 끝나면 되돌린다
    real_render, product.render_template = product.render_template, fake_render
    for fields, error_field in [
        ({"kind": "auction"}, "kind"),
        ({"duration": "2"}, "duration"),
        ({"duration": ""}, "duration"),
        ({"kind": "fixed"}, "price"),  # fixed이면 duration을 무시하고 가격을 검사한다
    ]:
        assert register(**fields).status_code == 400, fields
        assert list(rendered["errors"]) == [error_field], fields
    product.render_template = real_render
    assert len(PREVIEW_PRODUCTS) == count and NAME not in PREVIEW_AUCTIONS

    # bid이면 price를 보내도 무시한다
    before = datetime.now().astimezone()
    response = register(price="abc")
    assert response.status_code == 302 and response.headers["Location"].startswith("/auction/detail/")
    saved = PREVIEW_PRODUCTS[0]
    assert saved["kind"] == "bid" and saved["seller"] == "seller" and "price" not in saved
    saved_auction = PREVIEW_AUCTIONS[NAME]
    assert saved_auction["top_price"] == 0 and saved_auction["bid_count"] == 0 and saved_auction["duration_days"] == 3
    end_at = datetime.fromisoformat(saved_auction["end_at"])
    assert end_at.tzinfo is not None
    assert timedelta(days=3, seconds=-2) <= end_at - before <= timedelta(days=3, seconds=2)


def check_bid():
    with client.session_transaction() as sess:
        sess.pop("id", None)
    assert bid(5000).headers["Location"] == "/login"

    login("seller")
    bid(5000)
    assert PREVIEW_AUCTIONS[NAME]["bid_count"] == 0  # 본인 상품

    login("buyer_a")
    for price in ("4999", "abc", ""):
        bid(price)
    assert PREVIEW_AUCTIONS[NAME]["bid_count"] == 0  # 첫 제안은 5,000원 이상

    assert bid("5,000").status_code == 302
    login("buyer_b")
    bid(9999)  # 최고가 + 5,000원 미만
    bid(12000)
    assert PREVIEW_AUCTIONS[NAME]["top_price"] == 12000 and PREVIEW_AUCTIONS[NAME]["bid_count"] == 2
    assert [b["price"] for b in PREVIEW_BIDS[NAME]] == [5000, 12000]

    assert bid(5000, name="없는 상품").status_code == 404
    assert bid(50000, name="이화 과잠 M 사이즈").status_code == 404  # 고정가 상품


def check_detail():
    login("buyer_a")
    assert client.get("/auction/detail/" + NAME).status_code == 200
    assert rendered["template"] == "auction/detail.html"
    assert rendered["product"]["name"] == NAME and rendered["product"]["price"] == 12000
    assert rendered["auction"]["closed"] is False and rendered["min_price"] == 17000
    assert [b["price"] for b in rendered["bids"]] == [12000, 5000]
    assert rendered["bids"][0]["bidder"] == "bu***"
    assert rendered["my_bid"]["price"] == 5000

    with client.session_transaction() as sess:
        sess.pop("id", None)
    client.get("/auction/detail/" + NAME)
    assert rendered["my_bid"] is None
    assert client.get("/auction/detail/없는 상품").status_code == 404
    assert client.get("/auction/detail/이화 과잠 M 사이즈").status_code == 404


def check_closed():
    PREVIEW_AUCTIONS[NAME]["end_at"] = (datetime.now().astimezone() - timedelta(seconds=1)).isoformat(timespec="seconds")
    login("buyer_a")
    bid(100000)
    assert PREVIEW_AUCTIONS[NAME]["top_price"] == 12000  # 마감 후에는 제안할 수 없다
    client.get("/auction/detail/" + NAME)
    assert rendered["auction"]["closed"] is True
    assert client.get("/auction/end/" + NAME).status_code == 501  # #40에서 구현한다

    # 목록 카드: 최고 제안가, 제안 수, 마감 시각이 보이고 마감된 경매는 auction_end로 연결된다
    page = client.get("/?q=맥북").get_data(as_text=True)
    assert "/auction/end/" in page and "/auction/detail/" not in page
    assert client.get("/?kind=bid&price_min=12000&price_max=12000").get_data(as_text=True).count("맥북") > 0
    assert "맥북" not in client.get("/?kind=bid&price_min=12001").get_data(as_text=True)


check_new()
check_bid()
check_detail()
check_closed()
print("ok")
