"""채팅 라우트: chat_room

헤더 탭이 url_for('chat_room')을 호출하므로 501을 반환하는 스텁을 등록한다. 구현할 때 교체한다.
"""

from flask import abort

from core import app


@app.route("/chat")
def chat_room():
    abort(501)
