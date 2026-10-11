from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from config import DATABASE_URL, TIMEZONE

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from .env")


# ============================================================
# CONNECTION HELPERS
# Every call opens a connection, runs one query and commits
# when the `with` block ends (or rolls back on an error).
# ============================================================

def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _all(sql, params=None):
    """Run a query and return every row."""
    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()


def _one(sql, params=None):
    """Run a query (also INSERT/UPDATE ... RETURNING) and return one row, or None."""
    with get_connection() as conn:
        return conn.execute(sql, params).fetchone()


# ============================================================
# TABLES
# ============================================================

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role VARCHAR(20) NOT NULL CHECK (role IN ('SALESPERSON', 'MANAGER')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS products (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(150) NOT NULL,
        category VARCHAR(100),
        cost_price NUMERIC(12,2) NOT NULL CHECK (cost_price >= 0),
        selling_price NUMERIC(12,2) NOT NULL CHECK (selling_price >= 0),
        quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS customers (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(150) NOT NULL,
        mobile VARCHAR(20) UNIQUE NOT NULL,
        email VARCHAR(150) NOT NULL,
        lifetime_profit NUMERIC(14,2) DEFAULT 0 CHECK (lifetime_profit >= 0),
        loyalty_points INTEGER DEFAULT 0 CHECK (loyalty_points >= 0),
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS offers (
        id BIGSERIAL PRIMARY KEY,
        code VARCHAR(50) UNIQUE NOT NULL,
        discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('PERCENTAGE', 'FLAT')),
        discount_value NUMERIC(12,2) NOT NULL CHECK (discount_value > 0),
        minimum_amount NUMERIC(12,2) DEFAULT 0 CHECK (minimum_amount >= 0),
        maximum_discount NUMERIC(12,2),
        expires_at TIMESTAMPTZ,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    """CREATE TABLE IF NOT EXISTS sales (
        id BIGSERIAL PRIMARY KEY,
        customer_id BIGINT REFERENCES customers(id),
        subtotal NUMERIC(14,2) NOT NULL,
        discount_type VARCHAR(30),
        offer_discount NUMERIC(14,2) DEFAULT 0,
        loyalty_discount NUMERIC(14,2) DEFAULT 0,
        final_amount NUMERIC(14,2) NOT NULL,
        total_profit NUMERIC(14,2) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    # Which salesperson made the sale (added for the dashboards).
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS salesperson_id INTEGER REFERENCES users(id)",
    """CREATE TABLE IF NOT EXISTS sale_items (
        id BIGSERIAL PRIMARY KEY,
        sale_id BIGINT REFERENCES sales(id) ON DELETE CASCADE,
        product_id BIGINT NOT NULL,
        product_name VARCHAR(150) NOT NULL,
        quantity INTEGER NOT NULL,
        cost_price NUMERIC(12,2) NOT NULL,
        selling_price NUMERIC(12,2) NOT NULL,
        discount NUMERIC(12,2) DEFAULT 0,
        final_unit_price NUMERIC(12,2) NOT NULL,
        total_price NUMERIC(14,2) NOT NULL,
        profit NUMERIC(14,2) NOT NULL
    )""",
    # Carts that a salesperson sent to the billing counter.
    """CREATE TABLE IF NOT EXISTS billing_requests (
        id BIGSERIAL PRIMARY KEY,
        cart_id VARCHAR(100) NOT NULL,
        requested_by INTEGER REFERENCES users(id),
        customer_name VARCHAR(150),
        mobile VARCHAR(20),
        email VARCHAR(150),
        offer_code VARCHAR(50),
        note TEXT,
        status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
            CHECK (status IN ('PENDING', 'BILLED', 'CANCELLED')),
        sale_id BIGINT REFERENCES sales(id),
        handled_by INTEGER REFERENCES users(id),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        handled_at TIMESTAMPTZ
    )""",
    # A cart can only be waiting at the counter once.
    """CREATE UNIQUE INDEX IF NOT EXISTS one_pending_request_per_cart
       ON billing_requests (cart_id) WHERE status = 'PENDING'""",
]


def initialize_database():
    with get_connection() as conn:
        for statement in SCHEMA:
            conn.execute(statement)


# ============================================================
# USERS
# ============================================================

def get_user_by_username(username):
    return _one(
        "SELECT id, username, password_hash, role FROM users WHERE username = %s",
        (username,),
    )


def create_user(username, password_hash, role):
    return _one(
        """INSERT INTO users (username, password_hash, role)
           VALUES (%s, %s, %s)
           ON CONFLICT (username)
           DO UPDATE SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role
           RETURNING id, username, role""",
        (username, password_hash, role),
    )


# ============================================================
# PRODUCTS
# ============================================================

def search_products(name):
    """Search for salespersons. Cost price is deliberately NOT included."""
    return _all(
        """SELECT id, name, category, selling_price, quantity
           FROM products
           WHERE name ILIKE %s AND is_active
           ORDER BY name""",
        (f"%{name}%",),
    )


def list_products():
    """Every active product with cost price (manager only)."""
    return _all("SELECT * FROM products WHERE is_active ORDER BY name")


def get_product(product_id):
    return _one("SELECT * FROM products WHERE id = %s AND is_active", (product_id,))


def create_product(name, category, cost_price, selling_price, quantity):
    return _one(
        """INSERT INTO products (name, category, cost_price, selling_price, quantity)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING *""",
        (name, category, cost_price, selling_price, quantity),
    )


def increase_product_stock(product_id, quantity):
    return _one(
        """UPDATE products SET quantity = quantity + %s, updated_at = NOW()
           WHERE id = %s AND is_active
           RETURNING *""",
        (quantity, product_id),
    )


def decrease_product_stock(product_id, quantity):
    """Returns None if the product does not exist or there is not enough stock."""
    return _one(
        """UPDATE products SET quantity = quantity - %s, updated_at = NOW()
           WHERE id = %s AND is_active AND quantity >= %s
           RETURNING *""",
        (quantity, product_id, quantity),
    )


def deactivate_product(product_id):
    return _one(
        "UPDATE products SET is_active = FALSE, updated_at = NOW() WHERE id = %s RETURNING *",
        (product_id,),
    )


# ============================================================
# CUSTOMERS
# ============================================================

def get_customer_by_mobile(mobile):
    return _one("SELECT * FROM customers WHERE mobile = %s", (mobile,))


def create_customer(name, mobile, email):
    return _one(
        "INSERT INTO customers (name, mobile, email) VALUES (%s, %s, %s) RETURNING *",
        (name, mobile, email),
    )


# ============================================================
# OFFERS
# ============================================================

def get_offer(code):
    return _one("SELECT * FROM offers WHERE code = %s AND is_active", (code.upper(),))


def create_offer(code, discount_type, discount_value,
                 minimum_amount=0, maximum_discount=None, expires_at=None):
    return _one(
        """INSERT INTO offers
               (code, discount_type, discount_value, minimum_amount, maximum_discount, expires_at)
           VALUES (%s, %s, %s, %s, %s, %s)
           RETURNING *""",
        (code.upper(), discount_type.upper(), discount_value,
         minimum_amount, maximum_discount, expires_at),
    )


def disable_offer(code):
    return _one(
        "UPDATE offers SET is_active = FALSE WHERE code = %s RETURNING *",
        (code.upper(),),
    )


def list_offers():
    return _all("SELECT * FROM offers WHERE is_active ORDER BY created_at DESC")


# ============================================================
# SALES
# ============================================================

def record_sale(sale, items, loyalty_points):
    """
    Save a whole sale in ONE transaction: the sale, its items, the stock
    reduction and the customer's profit/points. If anything fails
    (for example not enough stock) nothing is saved. Returns the sale id.
    """
    with get_connection() as conn:
        sale_id = conn.execute(
            """INSERT INTO sales
                   (customer_id, salesperson_id, subtotal, discount_type,
                    offer_discount, loyalty_discount, final_amount, total_profit)
               VALUES
                   (%(customer_id)s, %(salesperson_id)s, %(subtotal)s, %(discount_type)s,
                    %(offer_discount)s, %(loyalty_discount)s, %(final_amount)s, %(total_profit)s)
               RETURNING id""",
            sale,
        ).fetchone()["id"]

        for item in items:
            reduced = conn.execute(
                """UPDATE products SET quantity = quantity - %s, updated_at = NOW()
                   WHERE id = %s AND is_active AND quantity >= %s""",
                (item["quantity"], item["product_id"], item["quantity"]),
            )
            if reduced.rowcount == 0:
                raise ValueError(f"Insufficient stock for {item['product_name']}")

            conn.execute(
                """INSERT INTO sale_items
                       (sale_id, product_id, product_name, quantity, cost_price,
                        selling_price, discount, final_unit_price, total_price, profit)
                   VALUES
                       (%(sale_id)s, %(product_id)s, %(product_name)s, %(quantity)s, %(cost_price)s,
                        %(selling_price)s, %(discount)s, %(final_unit_price)s, %(total_price)s, %(profit)s)""",
                {**item, "sale_id": sale_id},
            )

        conn.execute(
            """UPDATE customers
               SET lifetime_profit = lifetime_profit + %s,
                   loyalty_points = loyalty_points + %s
               WHERE id = %s""",
            (sale["total_profit"], loyalty_points, sale["customer_id"]),
        )

    return sale_id


def get_sale_bill(sale_id):
    """A sale with its customer details and its items, or None."""
    sale = _one(
        """SELECT s.*, c.name AS customer_name, c.mobile, c.email
           FROM sales s
           LEFT JOIN customers c ON c.id = s.customer_id
           WHERE s.id = %s""",
        (sale_id,),
    )
    if sale:
        sale["items"] = _all("SELECT * FROM sale_items WHERE sale_id = %s ORDER BY id", (sale_id,))
    return sale


# ============================================================
# SALES REPORTS
# ============================================================

def get_monthly_sales(month=None, year=None):
    """Orders / revenue / profit for a month. Defaults to the current month."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    month, year = month or now.month, year or now.year
    start = datetime(year, month, 1, tzinfo=tz)
    end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=tz)  # first day of next month
    return _one(
        """SELECT COUNT(*) AS orders,
                  COALESCE(SUM(final_amount), 0) AS revenue,
                  COALESCE(SUM(total_profit), 0) AS profit
           FROM sales
           WHERE created_at >= %s AND created_at < %s""",
        (start, end),
    )


def get_sales_by_time(start_time, end_time):
    sales = _all(
        """SELECT id, customer_id, subtotal, offer_discount, loyalty_discount,
                  final_amount, total_profit, created_at
           FROM sales
           WHERE created_at >= %s AND created_at <= %s
           ORDER BY created_at DESC""",
        (start_time, end_time),
    )
    return {
        "orders": len(sales),
        "revenue": sum(float(s["final_amount"]) for s in sales),
        "profit": sum(float(s["total_profit"]) for s in sales),
        "sales": sales,
    }


def get_sales_summary(salesperson_id=None):
    """Orders / revenue / profit for today and this month (optionally for one salesperson)."""
    today = datetime.now(ZoneInfo(TIMEZONE)).replace(hour=0, minute=0, second=0, microsecond=0)
    params = {"today": today, "month": today.replace(day=1), "salesperson_id": salesperson_id}
    who = "AND salesperson_id = %(salesperson_id)s" if salesperson_id else ""
    return _one(
        f"""SELECT
                COUNT(*) FILTER (WHERE created_at >= %(today)s) AS today_orders,
                COALESCE(SUM(final_amount) FILTER (WHERE created_at >= %(today)s), 0) AS today_revenue,
                COALESCE(SUM(total_profit) FILTER (WHERE created_at >= %(today)s), 0) AS today_profit,
                COUNT(*) AS month_orders,
                COALESCE(SUM(final_amount), 0) AS month_revenue,
                COALESCE(SUM(total_profit), 0) AS month_profit
            FROM sales
            WHERE created_at >= %(month)s {who}""",
        params,
    )


def get_recent_sales(limit=10, salesperson_id=None):
    where = "WHERE s.salesperson_id = %s" if salesperson_id else ""
    params = (salesperson_id, limit) if salesperson_id else (limit,)
    return _all(
        f"""SELECT s.id, s.created_at, s.final_amount, s.total_profit, s.discount_type,
                   c.name AS customer_name, u.username AS salesperson
            FROM sales s
            LEFT JOIN customers c ON c.id = s.customer_id
            LEFT JOIN users u ON u.id = s.salesperson_id
            {where}
            ORDER BY s.created_at DESC
            LIMIT %s""",
        params,
    )


# ============================================================
# BILLING COUNTER REQUESTS
# ============================================================

def save_billing_request(cart_id, requested_by, customer_name, mobile, email, offer_code, note):
    """Put a cart in the counter queue. If it is already waiting, refresh its details instead."""
    return _one(
        """INSERT INTO billing_requests
               (cart_id, requested_by, customer_name, mobile, email, offer_code, note)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (cart_id) WHERE status = 'PENDING'
           DO UPDATE SET
               customer_name = COALESCE(EXCLUDED.customer_name, billing_requests.customer_name),
               mobile        = COALESCE(EXCLUDED.mobile, billing_requests.mobile),
               email         = COALESCE(EXCLUDED.email, billing_requests.email),
               offer_code    = COALESCE(EXCLUDED.offer_code, billing_requests.offer_code),
               note          = COALESCE(EXCLUDED.note, billing_requests.note)
           RETURNING *""",
        (cart_id, requested_by, customer_name, mobile, email, offer_code, note),
    )


def get_billing_request(request_id):
    return _one(
        """SELECT r.*, u.username AS requested_by_name
           FROM billing_requests r
           LEFT JOIN users u ON u.id = r.requested_by
           WHERE r.id = %s""",
        (request_id,),
    )


def list_billing_requests(status=None, requested_by=None, limit=20, oldest_first=False):
    conditions, params = [], []
    if status:
        conditions.append("r.status = %s")
        params.append(status)
    if requested_by:
        conditions.append("r.requested_by = %s")
        params.append(requested_by)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    order = "ASC" if oldest_first else "DESC"
    return _all(
        f"""SELECT r.*, u.username AS requested_by_name
            FROM billing_requests r
            LEFT JOIN users u ON u.id = r.requested_by
            {where}
            ORDER BY r.created_at {order}
            LIMIT %s""",
        (*params, limit),
    )


def count_pending_requests():
    return _one("SELECT COUNT(*) AS n FROM billing_requests WHERE status = 'PENDING'")["n"]


def close_billing_request(cart_id, status, handled_by, sale_id=None):
    """Mark the request waiting for this cart as BILLED or CANCELLED. None if nothing was waiting."""
    return _one(
        """UPDATE billing_requests
           SET status = %s, handled_by = %s, sale_id = %s, handled_at = NOW()
           WHERE cart_id = %s AND status = 'PENDING'
           RETURNING *""",
        (status, handled_by, sale_id, cart_id),
    )
