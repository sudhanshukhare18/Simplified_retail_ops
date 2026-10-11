from database.mongodb import carts
from database.postgres import get_product


def create_cart(cart_id):
    """Create an empty cart if it does not exist yet, and return it."""
    carts.update_one({"_id": cart_id}, {"$setOnInsert": {"items": []}}, upsert=True)
    return get_cart(cart_id)


def get_cart(cart_id):
    """Return the cart with its subtotal, or None if there is no such cart."""
    cart = carts.find_one({"_id": cart_id})
    if cart:
        cart["subtotal"] = sum(i["selling_price"] * i["quantity"] for i in cart["items"])
    return cart


def add_to_cart(cart_id, product_id, quantity):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")

    product = get_product(product_id)
    if not product:
        raise ValueError("Product not found")

    cart = create_cart(cart_id)
    line = next((i for i in cart["items"] if i["product_id"] == product_id), None)

    new_quantity = quantity + (line["quantity"] if line else 0)
    if new_quantity > product["quantity"]:
        raise ValueError(f"Only {product['quantity']} units available")

    if line:
        line["quantity"] = new_quantity
    else:
        cart["items"].append({
            "product_id": product["id"],
            "name": product["name"],
            "selling_price": float(product["selling_price"]),
            "quantity": quantity,
        })

    carts.update_one({"_id": cart_id}, {"$set": {"items": cart["items"]}})
    return get_cart(cart_id)


def remove_from_cart(cart_id, product_id):
    result = carts.update_one({"_id": cart_id}, {"$pull": {"items": {"product_id": product_id}}})
    if result.modified_count == 0:
        raise ValueError("Product not found in cart")
    return get_cart(cart_id)


def clear_cart(cart_id):
    carts.delete_one({"_id": cart_id})
    return {"success": True, "message": "Cart cleared"}
