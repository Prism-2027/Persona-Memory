"""MongoDB collections owned by the feedback mechanism.

The learner writes only to FEEDBACK_MODELS; original Persona Memory documents
are not read, replaced, or seeded by this component.
"""
import os
URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
if URI == "mock":
    import mongomock
    _client = mongomock.MongoClient()
else:
    from pymongo import MongoClient
    _client = MongoClient(URI)
DB = _client[os.getenv("MONGO_DB", "twin")]
FEEDBACK_MODELS = DB[os.getenv("FEEDBACK_MODELS_COLLECTION", "feedback_models")]
EVENTS = DB[os.getenv("EVENTS_COLLECTION", "action_feedback")]
EPISODIC_MEMORIES = DB[os.getenv("EPISODIC_COLLECTION", "episodic_memory")]
RELATIONSHIP_MEMORIES = DB[os.getenv("RELATIONSHIP_COLLECTION", "relationship_memory")]
VALUE_MEMORIES = DB[os.getenv("VALUE_COLLECTION", "value_model")]
