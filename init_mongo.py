import os
from pymongo import MongoClient, TEXT

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://hanzala1000:hanzala1000@cluster0.powru.mongodb.net/"
)

def setup():
    print("[Setup] Connecting to MongoDB Atlas with pymongo...")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client["always_together"]
    print("Database names:", client.list_database_names())

    print("[Setup] Creating indexes...")
    db.users.create_index("tag", unique=True)
    db.users.create_index("email", unique=True)
    db.users.create_index([("tag", TEXT), ("display_name", TEXT)])
    print("  ✓ users")

    db.messages.create_index([("conversation_id", 1), ("created_at", -1)])
    db.messages.create_index("deleted_at")
    db.messages.create_index("sender_id")
    print("  ✓ messages")

    db.conversations.create_index("participants")
    db.conversations.create_index([("participants", 1), ("updated_at", -1)])
    print("  ✓ conversations")

    db.fcm_tokens.create_index("user_id", unique=True)
    print("  ✓ fcm_tokens")

    print("\n✅ All MongoDB Atlas indexes created successfully!")
    client.close()

if __name__ == "__main__":
    setup()
