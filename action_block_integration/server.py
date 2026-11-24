"""Action Block feedback API -> Persona Memory schema collections.

This service contains no synthetic persona bank or separate learned persona database.
Each accepted Action Block feedback event is recorded and mapped into the canonical
episodic, relationship, and value memory collections.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from db import EVENTS, URI
from action_block_schema import Feedback
from schema_adapter import sync_persona_schemas

OUTCOME_REWARD = {
    "accepted": 1.0,
    "modified": 0.4,
    "ignored": -0.3,
    "dismissed": -0.7,
    "overridden": -1.0,
}

def calculate_reward(fb: dict) -> float:
    response = fb["response"]
    value = OUTCOME_REWARD[response["outcome"]]
    rating = fb.get("rating")
    if rating is not None:
        value = 0.3 * value + 0.7 * float(rating)
    latency = response.get("latency_ms")
    if value > 0 and latency and latency > 60_000:
        value *= 0.7
    return max(-1.0, min(1.0, value))

def _value_signals(fb: dict, reward: float) -> dict:
    """Translate this Action Block choice into schema-shaped preference evidence."""
    score = max(0.0, min(1.0, (reward + 1.0) / 2.0))
    executed = fb["executed"]
    return {
        dimension: {
            str(option): {"score": score, "weight": reward, "n": 1}
        }
        for dimension, option in {
            "action_type": executed.get("action_type"),
            "channel": executed.get("channel"),
            "tone": executed.get("tone"),
            "timing": executed.get("timing"),
        }.items()
        if option is not None
    }

def ingest_feedback(fb: dict) -> dict:
    feedback_id = fb["feedback_id"]
    try:
        EVENTS.insert_one({"_id": feedback_id, **fb, "applied": False})
    except DuplicateKeyError:
        previous = EVENTS.find_one({"_id": feedback_id}, {"applied": 1})
        if previous and previous.get("applied"):
            return {"feedback_id": feedback_id, "status": "duplicate"}

    reward = calculate_reward(fb)
    signals = {"values": _value_signals(fb, reward)}
    episode_id = sync_persona_schemas(fb, reward, signals)
    EVENTS.update_one(
        {"_id": feedback_id},
        {"$set": {"applied": True, "reward": reward, "episode_id": episode_id}},
    )
    return {
        "feedback_id": feedback_id,
        "episode_id": episode_id,
        "status": "ok",
        "reward": round(reward, 3),
    }

@asynccontextmanager
async def lifespan(app):
    EVENTS.create_index([("user_id", 1), ("ts", 1)])
    yield

app = FastAPI(title="Action Block → Persona Memory Feedback API", lifespan=lifespan)

@app.post("/feedback")
def post_feedback(feedback: Feedback):
    return ingest_feedback(feedback.model_dump())

@app.post("/feedback/batch")
def post_feedback_batch(feedback_items: list[Feedback]):
    result = {"ok": 0, "duplicate": 0}
    for item in feedback_items:
        status = ingest_feedback(item.model_dump())["status"]
        result[status] = result.get(status, 0) + 1
    return result

@app.get("/health")
def health():
    return {"status": "ok", "processed_feedback_events": EVENTS.count_documents({"applied": True})}

@app.websocket("/ws/feedback")
async def websocket_feedback(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            message = await ws.receive_json()
            items = message if isinstance(message, list) else [message]
            acknowledgements = []
            for item in items:
                try:
                    parsed = Feedback.model_validate(item)
                    ack = await run_in_threadpool(ingest_feedback, parsed.model_dump())
                except ValidationError as error:
                    ack = {"status": "invalid", "detail": str(error)[:300]}
                acknowledgements.append(ack)
            await ws.send_json(acknowledgements if isinstance(message, list) else acknowledgements[0])
    except WebSocketDisconnect:
        pass
