import psycopg
from psycopg.rows import dict_row

from config import DATABASE_URL


if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is missing from .env"
    )


# ============================================
# CONNECTION
# ============================================

def get_connection():

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


# ============================================
# DATABASE INITIALIZATION
# ============================================

def initialize_database():

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # -------------------------------
            # PRODUCTS
            # -------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (

                    id BIGSERIAL PRIMARY KEY,

                    name VARCHAR(150) NOT NULL,

                    category VARCHAR(100),

                    cost_price NUMERIC(12,2)
                        NOT NULL
                        CHECK (cost_price >= 0),

                    selling_price NUMERIC(12,2)
                        NOT NULL
                        CHECK (selling_price >= 0),

                    quantity INTEGER
                        NOT NULL
                        DEFAULT 0
                        CHECK (quantity >= 0),

                    is_active BOOLEAN
                        DEFAULT TRUE,

                    created_at TIMESTAMP
                        WITH TIME ZONE
                        DEFAULT NOW(),

                    updated_at TIMESTAMP
                        WITH TIME ZONE
                        DEFAULT NOW()
                );
            """)

            # -------------------------------
            # CUSTOMERS
            # -------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (

                    id BIGSERIAL PRIMARY KEY,

                    name VARCHAR(150)
                        NOT NULL,

                    mobile VARCHAR(20)
                        UNIQUE NOT NULL,

                    email VARCHAR(150)
                        NOT NULL,

                    lifetime_profit NUMERIC(14,2)
                        DEFAULT 0
                        CHECK (lifetime_profit >= 0),

                    loyalty_points INTEGER
                        DEFAULT 0
                        CHECK (loyalty_points >= 0),

                    created_at TIMESTAMP
                        WITH TIME ZONE
                        DEFAULT NOW()
                );
            """)

            # -------------------------------
            # OFFERS
            # -------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offers (

                    id BIGSERIAL PRIMARY KEY,

                    code VARCHAR(50)
                        UNIQUE NOT NULL,

                    discount_type VARCHAR(20)
                        NOT NULL
                        CHECK (
                            discount_type
                            IN ('PERCENTAGE', 'FLAT')
                        ),

                    discount_value NUMERIC(12,2)
                        NOT NULL
                        CHECK (discount_value > 0),

                    minimum_amount NUMERIC(12,2)
                        DEFAULT 0
                        CHECK (minimum_amount >= 0),

                    maximum_discount NUMERIC(12,2),

                    expires_at TIMESTAMP
                        WITH TIME ZONE,

                    is_active BOOLEAN
                        DEFAULT TRUE,

                    created_at TIMESTAMP
                        WITH TIME ZONE
                        DEFAULT NOW()
                );
            """)

            # -------------------------------
            # SALES
            # -------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (

                    id BIGSERIAL PRIMARY KEY,

                    customer_id BIGINT
                        REFERENCES customers(id),

                    subtotal NUMERIC(14,2)
                        NOT NULL,

                    discount_type VARCHAR(30),

                    offer_discount NUMERIC(14,2)
                        DEFAULT 0,

                    loyalty_discount NUMERIC(14,2)
                        DEFAULT 0,

                    final_amount NUMERIC(14,2)
                        NOT NULL,

                    total_profit NUMERIC(14,2)
                        NOT NULL,

                    created_at TIMESTAMP
                        WITH TIME ZONE
                        DEFAULT NOW()
                );
            """)


            cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role VARCHAR(20) NOT NULL
            CHECK (role IN ('SALESPERSON', 'MANAGER')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
         )
        """)
            # -------------------------------
            # SALE ITEMS
            # -------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sale_items (

                    id BIGSERIAL PRIMARY KEY,

                    sale_id BIGINT
                        REFERENCES sales(id)
                        ON DELETE CASCADE,

                    product_id BIGINT
                        NOT NULL,

                    product_name VARCHAR(150)
                        NOT NULL,

                    quantity INTEGER
                        NOT NULL,

                    cost_price NUMERIC(12,2)
                        NOT NULL,

                    selling_price NUMERIC(12,2)
                        NOT NULL,

                    discount NUMERIC(12,2)
                        DEFAULT 0,

                    final_unit_price NUMERIC(12,2)
                        NOT NULL,

                    total_price NUMERIC(14,2)
                        NOT NULL,

                    profit NUMERIC(14,2)
                        NOT NULL
                );
            """)

        conn.commit()

        print("Database initialized successfully.")

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ============================================================
# USER AUTHENTICATION
# ============================================================

def get_user_by_username(username):

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT id, username, password_hash, role
                FROM users
                WHERE username = %s
            """, (username,))

            return cur.fetchone()


def create_user(username, password_hash, role):

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO users (
                    username,
                    password_hash,
                    role
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (username)
                DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role
                RETURNING id, username, role
            """, (
                username,
                password_hash,
                role
            ))

            user = cur.fetchone()

        conn.commit()

    return user


# ============================================================
# PRODUCTS
# ============================================================

def search_products(name):

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT *
                FROM products
                WHERE name ILIKE %s
                  AND is_active = TRUE
                ORDER BY name
            """, (f"%{name}%",))

            return cur.fetchall()


def get_product(product_id):

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT *
                FROM products
                WHERE id = %s
                  AND is_active = TRUE
            """, (product_id,))

            return cur.fetchone()


def create_product(
    name,
    category,
    cost_price,
    selling_price,
    quantity
):

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO products (
                    name,
                    category,
                    cost_price,
                    selling_price,
                    quantity
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (
                name,
                category,
                cost_price,
                selling_price,
                quantity
            ))

            product = cur.fetchone()

        conn.commit()

    return product


def increase_product_stock(product_id, quantity):

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                UPDATE products
                SET quantity = quantity + %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND is_active = TRUE
                RETURNING *
            """, (quantity, product_id))

            product = cur.fetchone()

        conn.commit()

    return product


def decrease_product_stock(product_id, quantity):

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                UPDATE products
                SET quantity = quantity - %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND is_active = TRUE
                  AND quantity >= %s
                RETURNING *
            """, (
                quantity,
                product_id,
                quantity
            ))

            product = cur.fetchone()

        conn.commit()

    return product


def deactivate_product(product_id):

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                UPDATE products
                SET is_active = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
            """, (product_id,))

            product = cur.fetchone()

        conn.commit()

    return product
# ============================================
# CUSTOMERS
# ============================================

def get_customer_by_mobile(mobile):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT *
                FROM customers
                WHERE mobile = %s
            """, (mobile,))

            return cursor.fetchone()


def create_customer(
    name,
    mobile,
    email
):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                INSERT INTO customers
                (
                    name,
                    mobile,
                    email
                )
                VALUES (%s, %s, %s)
                RETURNING *
            """, (
                name,
                mobile,
                email
            ))

            result = cursor.fetchone()

        conn.commit()

        return result


def update_customer_profit(
    customer_id,
    profit,
    points
):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                UPDATE customers
                SET
                    lifetime_profit =
                        lifetime_profit + %s,

                    loyalty_points =
                        loyalty_points + %s

                WHERE id = %s

                RETURNING *
            """, (
                profit,
                points,
                customer_id
            ))

            result = cursor.fetchone()

        conn.commit()

        return result


# ============================================
# OFFERS
# ============================================

def get_offer(code):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT *
                FROM offers
                WHERE code = %s
                AND is_active = TRUE
            """, (code.upper(),))

            return cursor.fetchone()


def create_offer(
    code,
    discount_type,
    discount_value,
    minimum_amount=0,
    maximum_discount=None,
    expires_at=None
):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                INSERT INTO offers
                (
                    code,
                    discount_type,
                    discount_value,
                    minimum_amount,
                    maximum_discount,
                    expires_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                code.upper(),
                discount_type.upper(),
                discount_value,
                minimum_amount,
                maximum_discount,
                expires_at
            ))

            result = cursor.fetchone()

        conn.commit()

        return result


def disable_offer(code):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                UPDATE offers
                SET is_active = FALSE
                WHERE code = %s
                RETURNING *
            """, (code.upper(),))

            result = cursor.fetchone()

        conn.commit()

        return result


def list_offers():

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT *
                FROM offers
                WHERE is_active = TRUE
                ORDER BY created_at DESC
            """)

            return cursor.fetchall()


# ============================================
# SALES
# ============================================

def create_sale(data):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                INSERT INTO sales
                (
                    customer_id,
                    subtotal,
                    discount_type,
                    offer_discount,
                    loyalty_discount,
                    final_amount,
                    total_profit
                )
                VALUES
                (
                    %(customer_id)s,
                    %(subtotal)s,
                    %(discount_type)s,
                    %(offer_discount)s,
                    %(loyalty_discount)s,
                    %(final_amount)s,
                    %(total_profit)s
                )
                RETURNING *
            """, data)

            result = cursor.fetchone()

        conn.commit()

        return result


def create_sale_items(items):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            for item in items:

                cursor.execute("""
                    INSERT INTO sale_items
                    (
                        sale_id,
                        product_id,
                        product_name,
                        quantity,
                        cost_price,
                        selling_price,
                        discount,
                        final_unit_price,
                        total_price,
                        profit
                    )
                    VALUES
                    (
                        %(sale_id)s,
                        %(product_id)s,
                        %(product_name)s,
                        %(quantity)s,
                        %(cost_price)s,
                        %(selling_price)s,
                        %(discount)s,
                        %(final_unit_price)s,
                        %(total_price)s,
                        %(profit)s
                    )
                """, item)

        conn.commit()


# ============================================
# SALES REPORTS
# ============================================

def get_monthly_sales(
    month,
    year
):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    COUNT(*) AS orders,
                    COALESCE(
                        SUM(final_amount), 0
                    ) AS revenue,
                    COALESCE(
                        SUM(total_profit), 0
                    ) AS profit
                FROM sales
                WHERE
                    EXTRACT(
                        MONTH FROM created_at
                    ) = %s
                AND
                    EXTRACT(
                        YEAR FROM created_at
                    ) = %s
            """, (
                month,
                year
            ))

            return cursor.fetchone()


def get_sales_by_time(
    start_time,
    end_time
):

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    customer_id,
                    subtotal,
                    offer_discount,
                    loyalty_discount,
                    final_amount,
                    total_profit,
                    created_at
                FROM sales
                WHERE created_at >= %s
                AND created_at <= %s
                ORDER BY created_at DESC
            """, (
                start_time,
                end_time
            ))

            sales = cursor.fetchall()

            return {
                "orders": len(sales),
                "revenue": sum(
                    float(
                        sale["final_amount"]
                    )
                    for sale in sales
                ),
                "profit": sum(
                    float(
                        sale["total_profit"]
                    )
                    for sale in sales
                ),
                "sales": sales
            }