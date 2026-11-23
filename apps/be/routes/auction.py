"""경매 라우트: auction_detail, auction_end, 제안 등록

상품 목록의 경매 카드가 url_for('auction_detail'), url_for('auction_end')를 호출하므로
501을 반환하는 스텁을 등록한다. 경매 화면과 함께 구현할 때 교체한다.
카드는 상품명을 name으로 넘긴다. 지금 경로에서는 ?name=으로 붙고, 경로를 /auction/<path:name>으로 바꿔도 템플릿은 그대로 동작한다.
"""

from flask import abort

from core import app


@app.route("/auction/detail")
def auction_detail():
    abort(501)


@app.route("/auction/end")
def auction_end():
    abort(501)
