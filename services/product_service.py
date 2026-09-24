from database.postgres import (
    search_products,
    get_product
)


def search_product_by_name(name):

    products = search_products(name)

    return products


def get_product_by_id(product_id):

    return get_product(product_id)