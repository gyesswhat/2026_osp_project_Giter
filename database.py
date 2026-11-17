import json

import pyrebase

AUTH_FILE = "./authentication/firebase_auth.json"


class DBhandler:
    def __init__(self):
        with open(AUTH_FILE) as f:
            config = json.load(f)
        firebase = pyrebase.initialize_app(config)
        self.db = firebase.database()

    def insert_item(self, name, data, img_path):
        item_info = {
            "seller": data["seller"],
            "price": data["price"],
            "address": data["address"],
            "status": data["status"],
            "email": data["email"],
            "img_path": img_path,
        }
        self.db.child("item").child(name).set(item_info)
        return True

    def insert_user(self, data, pw_hash):
        if not self.user_duplicate_check(data["id"]):
            return False
        user_info = {"id": data["id"], "pw": pw_hash, "nickname": data["nickname"]}
        self.db.child("user").push(user_info)
        return True

    def user_duplicate_check(self, id_string):
        users = self.db.child("user").get()
        for res in users.each() or []:
            if res.val().get("id") == id_string:
                return False
        return True

    def find_user(self, id_, pw_hash):
        users = self.db.child("user").get()
        for res in users.each() or []:
            value = res.val()
            if value.get("id") == id_ and value.get("pw") == pw_hash:
                return True
        return False

    def get_items(self):
        return self.db.child("item").get().val() or {}

    def get_item_byname(self, name):
        return self.db.child("item").child(name).get().val()

    # ---------- review ----------
    def insert_review(self, data, img_path):
        review_info = {
            "title": data["title"],
            "item_name": data["item_name"],
            "content": data["content"],
            "rating": data["rating"],
            "reviewer": data.get("reviewer", ""),
            "img_path": img_path,
        }
        # push()로 저장하면 Firebase가 고유 키를 자동 생성한다
        result = self.db.child("review").push(review_info)
        return result["name"]

    def get_reviews(self):
        return self.db.child("review").get().val() or {}

    def get_review_byid(self, review_id):
        return self.db.child("review").child(review_id).get().val()

    # ---------- like (heart) ----------
    def get_heart_byname(self, user_id, name):
        heart = self.db.child("heart").child(user_id).child(name).get().val()
        return heart or {"interested": "N"}

    def update_heart(self, user_id, is_heart, name):
        self.db.child("heart").child(user_id).child(name).set({"interested": is_heart})
        return True

    def count_hearts(self, name):
        hearts = self.db.child("heart").get().val() or {}
        return sum(
            1 for items in hearts.values()
            if isinstance(items, dict) and (items.get(name) or {}).get("interested") == "Y"
        )
