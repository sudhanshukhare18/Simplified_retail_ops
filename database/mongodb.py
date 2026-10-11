from pymongo import MongoClient

from config import MONGO_URI, MONGO_DB

db = MongoClient(MONGO_URI)[MONGO_DB]

# Open shopping carts: {"_id": cart_id, "items": [...]}
carts = db["carts"]
