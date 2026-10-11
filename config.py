import os
import secrets

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "retailops")
INVOICE_DIR = os.getenv("INVOICE_DIR", "invoices")

# Web dashboard.
# Put SECRET_KEY in .env. If it is missing a random key is used,
# which means everyone is logged out whenever the dashboard restarts.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")  # used for "today" and "this month"

# Business rules
MINIMUM_PROFIT = 1000
LOYALTY_PROFIT_THRESHOLD = 30000
LOYALTY_DISCOUNT_PERCENT = 10
