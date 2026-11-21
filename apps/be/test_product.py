"""상품 라우트 확인 (더미 데이터 경로)

실행: (apps/be에서) python test_product.py
Firebase에 쓰지 않도록 db를 None으로 바꾸고, 사진은 임시 폴더에 저장한다.
"""

import io
import tempfile

from core import app
from dummy import PREVIEW_PRODUCTS
# 헤더의 url_for가 찾는 라우트를 모두 등록한다 (app.py와 같은 import)
from routes import auction, auth, chat, my, product, review, wanted  # noqa: F401

product.db = None
product.UPLOAD_DIR = tempfile.mkdtemp()
client = app.test_client()


def check_list():
    # 더미 6개 중 done 1개를 제외한다
    assert 'num text-ink">5<' in client.get("/").get_data(as_text=True)
    page = client.get("/?sale_status=hold").get_data(as_text=True)
    assert "이화 과잠" in page and "로지텍" not in page
    page = client.get("/?kind=fixed&price_min=20000&price_max=30000&sort=low").get_data(as_text=True)
    assert page.index("로지텍") < page.index("이화 과잠") and "냉장고" not in page
    assert "전기 주전자" not in client.get("/?q=주전자").get_data(as_text=True)

    # 한 페이지 2개로 줄여 5개를 3페이지로 나눈다. 범위를 벗어난 page는 마지막 페이지를 보여 준다
    product.PAGE_SIZE = 2
    page = client.get("/?page=2").get_data(as_text=True)
    assert "이화 과잠" in page and "로지텍" in page and "냉장고" not in page
    page = client.get("/?page=99").get_data(as_text=True)
    assert "냉장고" in page and "이화 과잠" not in page
    assert "컴퓨터구조" in client.get("/?page=abc").get_data(as_text=True)
    product.PAGE_SIZE = 8


def register(**fields):
    form = {"name": "아이패드 1/2", "price": "10,000", "address": "ECC", "status": "상", "description": "설명"}
    form.update(fields)
    form.setdefault("picture", (io.BytesIO(b"\x89PNG"), "사진.png"))
    return client.post("/product/new", data=form, content_type="multipart/form-data")


def check_new():
    with client.session_transaction() as sess:
        sess.pop("id", None)
    assert register().headers["Location"] == "/login"

    with client.session_transaction() as sess:
        sess["id"] = "tester"
    for fields, error_field in [
        ({"name": "new"}, "name"),
        ({"name": "a.b"}, "name"),
        ({"name": "컴퓨터구조 및 설계 5판"}, "name"),
        ({"price": "0"}, "price"),
        ({"status": "새것"}, "status"),
        ({"picture": (io.BytesIO(b"GIF"), "a.gif")}, "picture"),
        ({"picture": (io.BytesIO(b"0" * (5 * 1024 * 1024 + 1)), "big.jpg")}, "picture"),
    ]:
        response = register(**fields)
        assert response.status_code == 400, fields
        assert 'id="' + error_field + '-msg" class="error" role="alert"' in response.get_data(as_text=True), fields

    response = register(seller="someone_else")
    assert response.status_code == 302
    saved = PREVIEW_PRODUCTS[0]
    assert saved["seller"] == "tester" and saved["price"] == 10000
    assert saved["img_path"].endswith(".png") and len(saved["img_path"]) == 32 + len(".png")
    assert register().status_code == 400  # 같은 이름으로 다시 등록


def check_detail():
    assert client.get("/product/" + "아이패드 1/2").status_code == 200
    assert client.get("/product/없는 상품").status_code == 404


check_list()
check_new()
check_detail()
print("ok")
