from database.mongodb import carts

from database.postgres import (
    get_product
)


def create_cart(cart_id):

    existing = carts.find_one({
        "_id": cart_id
    })

    if existing:
        return existing

    cart = {
        "_id": cart_id,
        "items": []
    }

    carts.insert_one(cart)

    return cart


def get_cart(cart_id):

    cart = carts.find_one({
        "_id": cart_id
    })

    if not cart:
        return create_cart(cart_id)

    cart["_id"] = str(cart["_id"])

    subtotal = 0

    for item in cart["items"]:

        subtotal += (
            item["selling_price"]
            * item["quantity"]
        )

    cart["subtotal"] = subtotal

    return cart


def add_to_cart(
    cart_id,
    product_id,
    quantity
):

    if quantity <= 0:
        raise ValueError(
            "Quantity must be greater than zero"
        )

    product = get_product(product_id)

    if not product:
        raise ValueError(
            "Product not found"
        )

    if product["quantity"] < quantity:
        raise ValueError(
            f"Only {product['quantity']} "
            f"units available"
        )

    cart = get_cart(cart_id)

    items = cart["items"]

    for item in items:

        if item["product_id"] == product_id:

            new_quantity = (
                item["quantity"] + quantity
            )

            if new_quantity > product["quantity"]:
                raise ValueError(
                    "Insufficient stock"
                )

            item["quantity"] = new_quantity

            carts.update_one(
                {"_id": cart_id},
                {"$set": {"items": items}}
            )

            return get_cart(cart_id)

    items.append({
        "product_id": product["id"],
        "name": product["name"],
        "selling_price":
            float(product["selling_price"]),
        "quantity": quantity
    })

    carts.update_one(
        {"_id": cart_id},
        {"$set": {"items": items}}
    )

    return get_cart(cart_id)


def remove_from_cart(
    cart_id,
    product_id
):

    result = carts.update_one(
        {"_id": cart_id},
        {
            "$pull": {
                "items": {
                    "product_id": product_id
                }
            }
        }
    )

    if result.modified_count == 0:
        raise ValueError(
            "Product not found in cart"
        )

    return get_cart(cart_id)


def clear_cart(cart_id):

    carts.delete_one({
        "_id": cart_id
    })

    return {
        "success": True,
        "message": "Cart cleared"
    }