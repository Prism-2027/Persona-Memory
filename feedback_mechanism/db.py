"""MongoDB connection. Point it at your existing persona-memory DB via env vars."""
import os
URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")     # use MONGO_URI=mock for an in-memory test DB
if URI == "mock":
    import mongomock; _client = mongomock.MongoClient()
else:
    from pymongo import MongoClient; _client = MongoClient(URI)
DB = _client[os.getenv("MONGO_DB", "twin")]
PERSONAS = DB[os.getenv("PERSONA_COLLECTION", "persona_memory")]   # one doc per user (_id = user_id)
EVENTS = DB[os.getenv("EVENTS_COLLECTION", "action_feedback")]     # episodic log (_id = feedback_id)