import os

from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017"
)

MONGO_DB = os.getenv(
    "MONGO_DB",
    "retailops"
)

INVOICE_DIR = os.getenv(
    "INVOICE_DIR",
    "invoices"
)


# Business rules

MINIMUM_PROFIT = 1000

LOYALTY_PROFIT_THRESHOLD = 30000

LOYALTY_DISCOUNT_PERCENT = 10