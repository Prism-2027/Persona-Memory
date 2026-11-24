"""Load persona-memory docs from dataset.json into MongoDB.  python seed.py [--reset]"""
import json, sys
from db import PERSONAS, EVENTS

def seed(path="dataset.json", reset=False):
    if reset: PERSONAS.delete_many({}); EVENTS.delete_many({})
    n = 0
    for p in json.load(open(path))["personas"]:
        doc = p["persona_memory"]                                   # ground_truth is NOT loaded
        if PERSONAS.find_one({"_id": doc["_id"]}) is None: PERSONAS.insert_one(doc); n += 1
    return n

if __name__ == "__main__":
    print("seeded personas:", seed(reset="--reset" in sys.argv))