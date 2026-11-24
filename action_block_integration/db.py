"""MongoDB connections for Action Block -> Persona Memory synchronization."""
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
if MONGO_URI == "mock":
    import mongomock
    _client = mongomock.MongoClient()
else:
    from pymongo import MongoClient
    _client = MongoClient(MONGO_URI)

DB = _client[os.getenv("MONGO_DB", "persona_memory")]

# Idempotency/audit log for Action Block feedback, not a separate persona database.
EVENTS = DB[os.getenv("ACTION_FEEDBACK_COLLECTION", "action_block_feedback")]

# Canonical Persona Memory collections.
EPISODIC_MEMORIES = DB[os.getenv("EPISODIC_COLLECTION", "episodic_memory")]
RELATIONSHIP_MEMORIES = DB[os.getenv("RELATIONSHIP_COLLECTION", "relationship_memory")]
VALUE_MEMORIES = DB[os.getenv("VALUE_COLLECTION", "value_model")]
