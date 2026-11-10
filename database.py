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
