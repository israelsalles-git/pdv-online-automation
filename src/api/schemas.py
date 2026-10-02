"""JSON Schemas do contrato da API (estrutura, campos obrigatórios e tipos)."""

ERROR = {
    "type": "object",
    "required": ["error"],
    "properties": {"error": {"type": "string", "minLength": 1}},
}

LOGIN = {
    "type": "object",
    "required": ["token", "user"],
    "properties": {
        "token": {"type": "string", "minLength": 1},
        "user": {
            "type": "object",
            "required": ["username"],
            "properties": {"username": {"type": "string"}},
        },
    },
}

PRODUCT = {
    "type": "object",
    "required": ["id", "code", "name", "price", "ncm"],
    "properties": {
        "id": {"type": "integer"},
        "code": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "price": {"type": "number", "exclusiveMinimum": 0},
        "ncm": {"type": "string"},
    },
}

CUSTOMER = {
    "type": "object",
    "required": ["id", "name", "document", "email"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string", "minLength": 1},
        "document": {"type": "string"},
        "email": {"type": "string"},
    },
}

SALE_ITEM = {
    "type": "object",
    "required": ["product_id", "code", "name", "quantity", "unit_price", "subtotal"],
    "properties": {
        "product_id": {"type": "integer"},
        "code": {"type": "string"},
        "name": {"type": "string"},
        "quantity": {"type": "integer", "minimum": 1},
        "unit_price": {"type": "number"},
        "subtotal": {"type": "number"},
    },
}

SALE = {
    "type": "object",
    "required": ["id", "status", "customer_id", "items", "total", "created_at"],
    "properties": {
        "id": {"type": "integer"},
        "status": {"enum": ["completed"]},
        "customer_id": {"type": ["integer", "null"]},
        "items": {"type": "array", "minItems": 1, "items": SALE_ITEM},
        "total": {"type": "number", "exclusiveMinimum": 0},
        "created_at": {"type": "string"},
    },
}


def list_of(item_schema: dict) -> dict:
    return {"type": "array", "items": item_schema}
