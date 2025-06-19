import datetime
import uuid
import os
import time
import logging

from flask import Flask, request, render_template, make_response, redirect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from peewee import *

# --------------------- LOGGING SETUP ---------------------

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),              # tampilkan di terminal
        logging.FileHandler("race_shop.log")  # simpan ke file
    ]
)

# --------------------- DATABASE SETUP ---------------------

db = SqliteDatabase("b.db")


class User(Model):
    id = AutoField()
    username = CharField(unique=True)
    password = CharField()
    token = CharField()
    balance = IntegerField()

    class Meta:
        database = db


class PurchaseLog(Model):
    id = AutoField()
    user_id = IntegerField()
    product_id = IntegerField()
    paid_amount = IntegerField()
    v_date = DateField(default=datetime.datetime.now)

    class Meta:
        database = db


class Product(Model):
    id = AutoField()
    name = CharField(unique=True)
    price = IntegerField()

    class Meta:
        database = db


@db.connection_context()
def initialize():
    db.create_tables([User, PurchaseLog, Product])
    for i in [
        {"name": "Galois Salad", "price": 5},
        {"name": "Alpaca Salad", "price": 20},
        {"name": "Fancy Flag", "price": 21},
    ]:
        try:
            Product.create(name=i["name"], price=i["price"])
        except:
            pass


initialize()

# --------------------- FLASK APP ---------------------

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

# --------------------- API CLASS ---------------------

class API:
    @staticmethod
    @db.connection_context()
    def login(username, password) -> str:
        user_objs = User.select().where(User.username == username)
        if len(user_objs) == 0:
            token = str(uuid.uuid4())
            try:
                User.create(
                    username=username,
                    password=password,
                    token=token,
                    balance=20,
                )
                logging.info(f"[LOGIN] ✅ New user created: {username}")
            except IntegrityError as e:
                logging.error(f"[LOGIN] ❌ DB error on create user: {e}")
                return ""
            return token
        user_obj = user_objs[0]
        if user_obj.password != password:
            logging.warning(f"[LOGIN] ❌ Failed login for {username}")
            return ""
        logging.info(f"[LOGIN] ✅ Successful login for {username}")
        return user_obj.token

    @staticmethod
    @db.connection_context()
    def get_user_detail_by_token(token: str) -> (bool, int, [PurchaseLog]):
        user_objs = User.select().where(User.token == token)
        if len(user_objs) == 0:
            return False, 0, None
        user_obj = user_objs[0]
        purchase_log = PurchaseLog.select().where(PurchaseLog.user_id == user_obj.id)
        return True, user_obj.balance, [x for x in purchase_log]

    @staticmethod
    @db.connection_context()
    def get_user_by_token(token: str):
        try:
            return User.get(User.token == token)
        except User.DoesNotExist:
            return None

    @staticmethod
    @db.connection_context()
    def buy(product_id: int, token: str) -> (bool, str):
        user_obj = API.get_user_by_token(token)
        if not user_obj:
            logging.warning(f"[BUY] ❌ Unauthorized attempt.")
            return False, "Unauthorized"

        product_objs = Product.select().where(Product.id == product_id)
        if len(product_objs) == 0:
            return False, "No such product"
        product_obj = product_objs[0]

        if product_obj.price > user_obj.balance:
            logging.info(f"[BUY] ❌ User {user_obj.username} insufficient funds for {product_obj.name}")
            return False, "No money you have bro..."

        try:
            with db.atomic():
                PurchaseLog.create(
                    user_id=user_obj.id,
                    product_id=product_obj.id,
                    paid_amount=product_obj.price
                )
                User.update(balance=user_obj.balance - product_obj.price).where(User.id == user_obj.id).execute()
                logging.info(f"[BUY] 🛒 {user_obj.username} bought {product_obj.name} for ${product_obj.price}")
        except IntegrityError as e:
            logging.error(f"[BUY] ❌ DB error: {e}")
            return False, "System error"

        return True, ""

    @staticmethod
    @db.connection_context()
    def sell(purchase_id: int, token: str) -> (bool, str):
        user_obj = API.get_user_by_token(token)
        if not user_obj:
            return False, "Invalid token"

        with db.atomic() as txn:
            try:
                purchase_history_obj = PurchaseLog.get(PurchaseLog.id == purchase_id)
            except PurchaseLog.DoesNotExist:
                return False, "No such purchase"

            if purchase_history_obj.user_id != user_obj.id:
                logging.warning(f"[SELL] ❌ {user_obj.username} tried to sell purchase not theirs")
                return False, "You don't own this item"

            time.sleep(0.1)  # slow down attackers

            rows_deleted = PurchaseLog.delete().where(PurchaseLog.id == purchase_id).execute()
            if rows_deleted == 0:
                txn.rollback()
                return False, "Already sold"

            User.update(balance=user_obj.balance + purchase_history_obj.paid_amount) \
                .where(User.id == user_obj.id).execute()

            logging.info(f"[SELL] ✅ {user_obj.username} sold item {purchase_id} for ${purchase_history_obj.paid_amount}, new balance={user_obj.balance + purchase_history_obj.paid_amount}")

            if purchase_history_obj.paid_amount == 21:
                logging.warning(f"[SELL] 🏁 FLAG ACCESS ATTEMPT by {user_obj.username}")
                return False, f"Well, flag is {os.getenv('FLAG')}"

            return True, ""

# --------------------- ROUTES ---------------------

@app.route('/', methods=["GET", "POST"])
def default():
    if request.method == 'POST':
        token = API.login(request.form["username"], request.form["password"])
        if token:
            resp = make_response(redirect("/"))
            resp.set_cookie("token", token)
            return resp
        else:
            return render_template('login.html', error_msg="Wrong credential")
    else:
        token = request.cookies.get("token")

        def go_login():
            return render_template('login.html')

        if token and len(token) > 5:
            is_login, balance, purchase_log = API.get_user_detail_by_token(token)
            if not is_login:
                resp = make_response(redirect("/"))
                resp.set_cookie("token", "")
                return resp
            return render_template('home.html', balance=balance, purchase_log=purchase_log)
        return go_login()

@app.route('/buy/<product_id>', methods=["GET"])
@limiter.limit("5 per second")
def buy(product_id):
    token = request.cookies.get("token")
    if not token:
        return "Unauthorized"
    is_success, err_message = API.buy(int(product_id), token)
    if is_success:
        return make_response(redirect("/"))
    else:
        return err_message

@app.route('/sell/<purchase_id>', methods=["GET"])
@limiter.limit("5 per second")
def sell(purchase_id):
    token = request.cookies.get("token")
    if not token:
        return "Unauthorized"
    is_success, err_message = API.sell(int(purchase_id), token)
    if is_success:
        return make_response(redirect("/"))
    else:
        return err_message

# --------------------- RUN ---------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1002, debug=True)
