"""PDV de demonstração (Flask, dados em memória).

AMBIENTE DE DEMONSTRAÇÃO: existe apenas para o framework de testes poder ser executado
localmente. Não é um PDV real e não possui persistência nem regras fiscais.
"""
from __future__ import annotations

import hmac
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps
from itertools import count
from typing import Any

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

MAX_PRICE = Decimal("1000000")
CENTS = Decimal("0.01")
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------- dados

class Store:
    def __init__(self) -> None:
        self.products: dict[int, dict] = {}
        self.customers: dict[int, dict] = {}
        self.sales: dict[int, dict] = {}
        self._ids = {kind: count(1) for kind in ("product", "customer", "sale")}
        self._seed()

    def next_id(self, kind: str) -> int:
        return next(self._ids[kind])

    def product_by_code(self, code: str, exclude_id: int | None = None) -> dict | None:
        return next((p for p in self.products.values() if p["code"] == code and p["id"] != exclude_id), None)

    def add_product(self, data: dict) -> dict:
        product = {"id": self.next_id("product"), **data}
        self.products[product["id"]] = product
        return product

    def add_customer(self, data: dict) -> dict:
        customer = {"id": self.next_id("customer"), **data}
        self.customers[customer["id"]] = customer
        return customer

    def _seed(self) -> None:
        # NCMs fictícios, apenas demonstrativos.
        for code, name, price, ncm in [
            ("1001", "Arroz 5kg", "25.90", "10063021"),
            ("1002", "Feijão Carioca 1kg", "8.49", "07133319"),
            ("1003", "Açúcar Refinado 1kg", "4.99", "17019900"),
            ("1004", "Óleo de Soja 900ml", "7.99", "15079011"),
            ("1005", "Café Torrado 500g", "15.90", "09012100"),
        ]:
            self.add_product({"code": code, "name": name, "price": Decimal(price), "ncm": ncm})
        self.add_customer({"name": "Maria Silva", "document": "111.111.111-11", "email": "maria@example.com"})
        self.add_customer({"name": "João Souza", "document": "222.222.222-22", "email": "joao@example.com"})


# --------------------------------------------------------------------------- validação

def _text(data: dict, field: str) -> str:
    value = data.get(field)
    return "" if value is None else str(value).strip()


def _lookup(table: dict[int, dict], key: Any) -> dict | None:
    return table.get(key) if isinstance(key, int) and not isinstance(key, bool) else None


def parse_price(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        raise ApiError("Preço inválido")
    try:
        price = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation:
        raise ApiError("Preço inválido") from None
    if not price.is_finite() or price <= 0 or price > MAX_PRICE:
        raise ApiError("Preço inválido")
    return price.quantize(CENTS, rounding=ROUND_HALF_UP)


def parse_product(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ApiError("Corpo da requisição inválido")
    code, name = _text(data, "code"), _text(data, "name")
    if not code:
        raise ApiError("Código é obrigatório")
    if not name:
        raise ApiError("Nome é obrigatório")
    return {"code": code, "name": name, "price": parse_price(data.get("price")), "ncm": _text(data, "ncm")}


def parse_customer(data: Any) -> dict:
    if not isinstance(data, dict):
        raise ApiError("Corpo da requisição inválido")
    name, email = _text(data, "name"), _text(data, "email")
    if not name:
        raise ApiError("Nome é obrigatório")
    if email and not EMAIL_PATTERN.fullmatch(email):
        raise ApiError("E-mail inválido")
    return {"name": name, "document": _text(data, "document"), "email": email}


def build_sale(store: Store, data: Any) -> dict:
    if not isinstance(data, dict):
        raise ApiError("Corpo da requisição inválido")
    raw_items = data.get("items")
    if raw_items is None or raw_items == []:
        raise ApiError("Carrinho vazio")
    if not isinstance(raw_items, list):
        raise ApiError("Itens inválidos")

    customer_id = data.get("customer_id")
    if customer_id is not None and not _lookup(store.customers, customer_id):
        raise ApiError("Cliente não encontrado", 404)

    items = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ApiError("Itens inválidos")
        quantity = raw.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ApiError("Quantidade inválida")
        product = _lookup(store.products, raw.get("product_id"))
        if product is None:
            raise ApiError(f"Produto não encontrado: {raw.get('product_id')}", 404)
        items.append({
            "product_id": product["id"], "code": product["code"], "name": product["name"],
            "quantity": quantity, "unit_price": product["price"], "subtotal": product["price"] * quantity,
        })

    sale = {
        "id": store.next_id("sale"), "status": "completed", "customer_id": customer_id, "items": items,
        "total": sum((i["subtotal"] for i in items), Decimal("0")),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    store.sales[sale["id"]] = sale
    return sale


# --------------------------------------------------------------------------- serialização

def product_json(p: dict) -> dict:
    return {**p, "price": float(p["price"])}


def sale_json(s: dict) -> dict:
    items = [{**i, "unit_price": float(i["unit_price"]), "subtotal": float(i["subtotal"])} for i in s["items"]]
    return {**s, "items": items, "total": float(s["total"])}


def brl(value: Decimal) -> str:
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def matches(term: str, *fields: str) -> bool:
    return not term or any(term.casefold() in f.casefold() for f in fields)


# --------------------------------------------------------------------------- app

def create_app(username: str, password: str) -> Flask:
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(16)
    app.jinja_env.filters["brl"] = brl
    store = Store()
    tokens: dict[str, str] = {}

    def credentials_ok(user: str, pwd: str) -> bool:
        # compare_digest exige bytes para aceitar caracteres não-ASCII.
        return (hmac.compare_digest(user.encode(), username.encode())
                and hmac.compare_digest(pwd.encode(), password.encode()))

    def current_user() -> str | None:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            return tokens.get(header[7:])
        return session.get("user")

    def login_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user():
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapper

    @app.before_request
    def require_api_auth():
        if request.path.startswith("/api/") and request.path != "/api/login" and not current_user():
            raise ApiError("Não autenticado", 401)

    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        return jsonify(error=err.message), err.status

    @app.errorhandler(404)
    @app.errorhandler(405)
    def handle_http_error(err):
        if request.path.startswith("/api/"):
            return jsonify(error=err.name), err.code
        return err

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    # ------------------------------------------------------------------ API REST

    @app.post("/api/login")
    def api_login():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not data.get("username") or not data.get("password"):
            raise ApiError("Informe usuário e senha")
        if not credentials_ok(str(data["username"]), str(data["password"])):
            raise ApiError("Usuário ou senha inválidos", 401)
        token = secrets.token_urlsafe(24)
        tokens[token] = str(data["username"])
        return jsonify(token=token, user={"username": str(data["username"])})

    @app.get("/api/products")
    def api_products_list():
        term = request.args.get("search", "")
        return jsonify([product_json(p) for p in store.products.values() if matches(term, p["code"], p["name"])])

    @app.post("/api/products")
    def api_products_create():
        data = parse_product(request.get_json(silent=True))
        if store.product_by_code(data["code"]):
            raise ApiError("Código já cadastrado", 409)
        return jsonify(product_json(store.add_product(data))), 201

    def get_product(product_id: int) -> dict:
        product = store.products.get(product_id)
        if product is None:
            raise ApiError("Produto não encontrado", 404)
        return product

    @app.get("/api/products/<int:product_id>")
    def api_products_get(product_id: int):
        return jsonify(product_json(get_product(product_id)))

    @app.put("/api/products/<int:product_id>")
    def api_products_update(product_id: int):
        product = get_product(product_id)
        data = parse_product(request.get_json(silent=True))
        if store.product_by_code(data["code"], exclude_id=product_id):
            raise ApiError("Código já cadastrado", 409)
        product.update(data)
        return jsonify(product_json(product))

    @app.delete("/api/products/<int:product_id>")
    def api_products_delete(product_id: int):
        get_product(product_id)
        del store.products[product_id]
        return "", 204

    @app.get("/api/customers")
    def api_customers_list():
        term = request.args.get("search", "")
        return jsonify([c for c in store.customers.values() if matches(term, c["name"], c["document"])])

    @app.post("/api/customers")
    def api_customers_create():
        return jsonify(store.add_customer(parse_customer(request.get_json(silent=True)))), 201

    @app.get("/api/customers/<int:customer_id>")
    def api_customers_get(customer_id: int):
        customer = store.customers.get(customer_id)
        if customer is None:
            raise ApiError("Cliente não encontrado", 404)
        return jsonify(customer)

    @app.post("/api/sales")
    def api_sales_create():
        return jsonify(sale_json(build_sale(store, request.get_json(silent=True)))), 201

    @app.get("/api/sales/<int:sale_id>")
    def api_sales_get(sale_id: int):
        sale = store.sales.get(sale_id)
        if sale is None:
            raise ApiError("Venda não encontrada", 404)
        return jsonify(sale_json(sale))

    # ------------------------------------------------------------------ UI

    @app.get("/")
    def index():
        return redirect(url_for("dashboard" if current_user() else "login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            user, pwd = request.form.get("username", ""), request.form.get("password", "")
            if not user or not pwd:
                error = "Informe usuário e senha"
            elif not credentials_ok(user, pwd):
                error = "Usuário ou senha inválidos"
            else:
                session["user"] = user
                return redirect(url_for("dashboard"))
        return render_template("login.html", error=error), (401 if error else 200)

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/dashboard")
    @login_required
    def dashboard():
        return render_template(
            "dashboard.html", user=current_user(), products=len(store.products),
            customers=len(store.customers), sales=len(store.sales),
        )

    @app.get("/products")
    @login_required
    def products_page():
        term = request.args.get("q", "").strip()
        editing = store.products.get(request.args.get("edit", type=int))
        rows = [p for p in store.products.values() if matches(term, p["code"], p["name"])]
        return render_template("products.html", products=rows, q=term, editing=editing)

    @app.post("/products/save")
    @login_required
    def products_save():
        product_id = request.form.get("id", type=int)
        try:
            data = parse_product(request.form.to_dict())
            if store.product_by_code(data["code"], exclude_id=product_id):
                raise ApiError("Código já cadastrado", 409)
        except ApiError as err:
            flash(err.message, "error")
            return redirect(url_for("products_page", edit=product_id))
        if product_id in store.products:
            store.products[product_id].update(data)
            flash("Produto atualizado com sucesso", "success")
        else:
            store.add_product(data)
            flash("Produto cadastrado com sucesso", "success")
        return redirect(url_for("products_page"))

    @app.post("/products/<int:product_id>/delete")
    @login_required
    def products_delete(product_id: int):
        if store.products.pop(product_id, None):
            flash("Produto excluído com sucesso", "success")
        else:
            flash("Produto não encontrado", "error")
        return redirect(url_for("products_page"))

    @app.get("/customers")
    @login_required
    def customers_page():
        term = request.args.get("q", "").strip()
        rows = [c for c in store.customers.values() if matches(term, c["name"], c["document"])]
        return render_template("customers.html", customers=rows, q=term)

    @app.post("/customers/save")
    @login_required
    def customers_save():
        try:
            store.add_customer(parse_customer(request.form.to_dict()))
        except ApiError as err:
            flash(err.message, "error")
        else:
            flash("Cliente cadastrado com sucesso", "success")
        return redirect(url_for("customers_page"))

    @app.get("/sales")
    @login_required
    def sales_page():
        return render_template("sales.html", products=list(store.products.values()))

    return app
