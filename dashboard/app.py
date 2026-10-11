import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import SECRET_KEY, TIMEZONE
from database import postgres as db
from services.auth_service import check_password
from services.cart_service import get_cart
from services.escalation_service import bill_request, cancel_request

log = logging.getLogger("uvicorn.error")

BASE_DIR = Path(__file__).parent
SESSION_HOURS = 8
LOW_STOCK = 5  # products with this many units or fewer are flagged

db.initialize_database()

app = FastAPI(title="RetailOps Dashboard")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=SESSION_HOURS * 3600,
    same_site="lax",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.filters["money"] = lambda value: f"₹{float(value or 0):,.2f}"
templates.env.filters["when"] = lambda dt: (
    dt.astimezone(ZoneInfo(TIMEZONE)).strftime("%d %b %Y, %I:%M %p") if dt else ""
)


# ============================================================
# SMALL HELPERS
# ============================================================

def redirect(url):
    return RedirectResponse(url, status_code=303)


def render(request, name, status_code=200, **context):
    """Render a page. Adds the logged-in user and any one-time flash message."""
    context["user"] = request.session.get("user")
    context["flash"] = request.session.pop("flash", None)
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def flash(request, message, kind="ok"):
    request.session["flash"] = {"message": message, "kind": kind}


def attempt(request, success_message, func, *args):
    """Run an action and show the result as a message instead of crashing the page."""
    try:
        func(*args)
        flash(request, success_message)
    except ValueError as error:
        flash(request, str(error), "error")
    except psycopg.errors.UniqueViolation:
        flash(request, "That already exists.", "error")
    except Exception:
        log.exception("Dashboard action failed")
        flash(request, "Something went wrong. Please try again.", "error")


# ============================================================
# LOGIN CHECKS
# ============================================================

def current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require(role):
    """Only let this role in; anyone else is sent back to their own dashboard."""
    def check(user=Depends(current_user)):
        if user["role"] != role:
            raise HTTPException(status_code=303, headers={"Location": "/"})
        return user
    return check


manager_only = require("MANAGER")
salesperson_only = require("SALESPERSON")


# ============================================================
# LOGIN / LOGOUT
# ============================================================

@app.get("/login")
def login_page(request: Request):
    return render(request, "login.html", error=None)


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = check_password(username.strip(), password)
    if not user:
        return render(request, "login.html", status_code=401, error="Invalid username or password")
    request.session["user"] = {"id": user["id"], "username": user["username"], "role": user["role"]}
    return redirect("/")


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")


@app.get("/")
def home(user=Depends(current_user)):
    return redirect("/manager" if user["role"] == "MANAGER" else "/salesperson")


# ============================================================
# MANAGER
# ============================================================

@app.get("/manager")
def manager_dashboard(request: Request, user=Depends(manager_only)):
    products = db.list_products()
    return render(
        request, "manager.html",
        summary=db.get_sales_summary(),
        products=products,
        low_products=[p for p in products if p["quantity"] <= LOW_STOCK],
        low_stock=LOW_STOCK,
        offers=db.list_offers(),
        recent_sales=db.get_recent_sales(10),
        pending_count=db.count_pending_requests(),
    )


@app.post("/manager/products")
def product_add(
    request: Request,
    name: str = Form(...),
    category: str = Form(""),
    cost_price: float = Form(...),
    selling_price: float = Form(...),
    quantity: int = Form(...),
    user=Depends(manager_only),
):
    if min(cost_price, selling_price, quantity) < 0:
        flash(request, "Prices and quantity cannot be negative.", "error")
    elif selling_price < cost_price:
        flash(request, "Selling price cannot be below cost price.", "error")
    else:
        attempt(request, f"Added {name.strip()}", db.create_product,
                name.strip(), category.strip() or None, cost_price, selling_price, quantity)
    return redirect("/manager")


@app.post("/manager/products/{product_id}/stock")
def product_stock(
    request: Request,
    product_id: int,
    quantity: int = Form(...),
    action: str = Form(...),
    user=Depends(manager_only),
):
    if quantity <= 0:
        flash(request, "Quantity must be greater than 0.", "error")
    else:
        change = db.increase_product_stock if action == "add" else db.decrease_product_stock
        if change(product_id, quantity):
            flash(request, "Stock updated.")
        else:
            flash(request, "Product not found or not enough stock.", "error")
    return redirect("/manager")


@app.post("/manager/products/{product_id}/delete")
def product_delete(request: Request, product_id: int, user=Depends(manager_only)):
    attempt(request, "Product deleted.", db.deactivate_product, product_id)
    return redirect("/manager")


@app.post("/manager/offers")
def offer_create(
    request: Request,
    code: str = Form(...),
    discount_type: str = Form(...),
    discount_value: float = Form(...),
    minimum_amount: str = Form(""),
    maximum_discount: str = Form(""),
    expires_at: str = Form(""),
    user=Depends(manager_only),
):
    code = code.strip().upper()
    if discount_type not in ("PERCENTAGE", "FLAT") or discount_value <= 0:
        flash(request, "Choose an offer type and a value above 0.", "error")
    elif discount_type == "PERCENTAGE" and discount_value > 100:
        flash(request, "A percentage offer cannot be more than 100.", "error")
    else:
        expiry = (
            datetime.fromisoformat(expires_at).replace(tzinfo=ZoneInfo(TIMEZONE))
            if expires_at else None
        )
        attempt(
            request, f"Offer {code} created", db.create_offer,
            code, discount_type, discount_value,
            float(minimum_amount or 0),
            float(maximum_discount) if maximum_discount else None,
            expiry,
        )
    return redirect("/manager")


@app.post("/manager/offers/disable")
def offer_disable(request: Request, code: str = Form(...), user=Depends(manager_only)):
    attempt(request, f"Offer {code} disabled", db.disable_offer, code)
    return redirect("/manager")


# ============================================================
# SALESPERSON
# ============================================================

@app.get("/salesperson")
def salesperson_dashboard(request: Request, q: str = "", user=Depends(salesperson_only)):
    q = q.strip()
    return render(
        request, "salesperson.html",
        summary=db.get_sales_summary(user["id"]),
        recent_sales=db.get_recent_sales(10, user["id"]),
        my_requests=db.list_billing_requests(requested_by=user["id"], limit=10),
        pending_count=db.count_pending_requests(),
        q=q,
        results=db.search_products(q) if q else [],
    )


# ============================================================
# BILLING COUNTER (managers and salespersons)
# ============================================================

@app.get("/billing")
def billing_counter(request: Request, user=Depends(current_user)):
    queue = db.list_billing_requests(status="PENDING", oldest_first=True, limit=50)
    for item in queue:
        item["cart"] = get_cart(item["cart_id"])
    handled = [r for r in db.list_billing_requests(limit=30) if r["status"] != "PENDING"][:10]
    return render(request, "billing.html", queue=queue, handled=handled)


@app.post("/billing/{request_id}/bill")
def billing_bill(
    request: Request,
    request_id: int,
    customer_name: str = Form(""),
    mobile: str = Form(""),
    email: str = Form(""),
    offer_code: str = Form(""),
    user=Depends(current_user),
):
    try:
        bill = bill_request(
            request_id, user["id"], customer_name.strip(), mobile.strip(),
            email.strip(), offer_code.strip().upper() or None,
        )
    except ValueError as error:
        flash(request, str(error), "error")
        return redirect("/billing")
    except Exception:
        log.exception("Billing failed")
        flash(request, "Billing failed. Please try again.", "error")
        return redirect("/billing")
    return redirect(f"/receipt/{bill['sale_id']}")


@app.post("/billing/{request_id}/cancel")
def billing_cancel(request: Request, request_id: int, user=Depends(current_user)):
    attempt(request, "Request cancelled.", cancel_request, request_id, user["id"])
    return redirect("/billing")


@app.get("/receipt/{sale_id}")
def receipt(request: Request, sale_id: int, user=Depends(current_user)):
    sale = db.get_sale_bill(sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return render(request, "receipt.html", sale=sale)
