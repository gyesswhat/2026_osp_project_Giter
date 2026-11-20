"""구해요 라우트: wanted_list, wanted_detail, wanted_new

헤더 탭이 url_for('wanted_list')을 호출하므로 501을 반환하는 스텁을 등록한다. 구현할 때 교체한다.
"""

from flask import abort

from core import app


@app.route("/wanted")
def wanted_list():
    abort(501)
