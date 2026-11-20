"""마이 라우트: my_index, my_manage

헤더 탭이 url_for('my_index')을 호출하므로 501을 반환하는 스텁을 등록한다. 구현할 때 교체한다.
"""

from flask import abort

from core import app


@app.route("/my")
def my_index():
    abort(501)
