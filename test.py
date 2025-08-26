# test_mongo_connection.py
from pymongo import MongoClient

# Test your connection string
mongo_uri = "mongodb+srv://Users:1234@cluster0.smh0yjv.mongodb.net/TCproject?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(mongo_uri)
    # Test the connection
    db = client.TCproject
    print("✅ Successfully connected to MongoDB Atlas!")
    print("Database name:", db.name)
    
    # List collections
    collections = db.list_collection_names()
    print("Available collections:", collections)
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nTroubleshooting steps:")
    print("1. Check if your username 'Users' and password '123' are correct")
    print("2. Make sure your IP is whitelisted in MongoDB Atlas Network Access")
    print("3. Verify your database user has the correct permissions")
    print("4. Check if your cluster is running in MongoDB Atlas")