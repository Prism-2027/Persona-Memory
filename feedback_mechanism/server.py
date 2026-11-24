"""Persona Memory service.  Action Block -> (REST | WebSocket) -> learning -> MongoDB.
Run:  uvicorn server:app --port 8000          (MONGO_URI=mock for a test run without MongoDB)"""
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, ValidationError
from pymongo.errors import DuplicateKeyError
from db import FEEDBACK_MODELS, EVENTS, URI
from learning import reward, learn, blank_persona, ensure_schema, action_prior, calibration_summary\nfrom schema_adapter import sync_persona_schemas

# ---------- contract v1 ----------
class Executed(BaseModel):
    action_type: str; channel: str; tone: str | None = None; timing: str | None = None
class Response(BaseModel):
    outcome: Literal["accepted", "modified", "ignored", "dismissed", "overridden"]
    latency_ms: int | None = None; user_action: str | None = None
class Prediction(BaseModel):
    top: str; confidence: float = Field(ge=0, le=1); probs: dict[str, float] = {}
class Feedback(BaseModel):
    feedback_id: str; user_id: str; snapshot_id: str; ts: float
    context: dict[str, str]; executed: Executed; response: Response
    prediction: Prediction | None = None; counterpart: str | None = None
    rating: Literal[-1, 0, 1] | None = None; stakes: Literal["low", "medium", "high"] = "low"

# ---------- core: one feedback event -> memory ----------
def ingest(fb: dict) -> dict:
    fid = fb["feedback_id"]
    try:
        EVENTS.insert_one({"_id": fid, **fb, "applied": False})   # episodic log; _id gives idempotency
    except DuplicateKeyError:
        old = EVENTS.find_one({"_id": fid}, {"applied": 1})
        if old and old.get("applied"):
            return {"feedback_id": fid, "status": "duplicate"}
    r = reward(fb)
    # Feedback model state is isolated from Persona Memory's original persona documents.
    for _ in range(8):
        doc = FEEDBACK_MODELS.find_one({"_id": fb["user_id"]})
        new = doc is None
        p = doc or blank_persona(fb["user_id"])
        flt = {"_id": p["_id"], "_v": p["_v"]} if "_v" in p else {"_id": p["_id"], "_v": {"$exists": False}}
        learn(p, fb, r)
        p["_v"] = p.get("_v", 0) + 1
        try:
            res = FEEDBACK_MODELS.replace_one(flt, p, upsert=new)
        except DuplicateKeyError:
            continue
        if new or res.matched_count:
            break
    else:
        return {"feedback_id": fid, "status": "conflict"}
    sync_persona_schemas(fb, r, p)
    EVENTS.update_one({"_id": fid}, {"$set": {"applied": True, "reward": r}})
    return {"feedback_id": fid, "status": "ok", "reward": round(r, 3)}

@asynccontextmanager
async def lifespan(app):
    EVENTS.create_index([("user_id", 1), ("ts", 1)])
    if URI == "mock":
        from seed import seed; print("mock DB seeded:", seed())
    yield

app = FastAPI(title="Persona Memory API v1", lifespan=lifespan)

# ---------- REST ----------
@app.post("/feedback")
def post_feedback(f: Feedback): return ingest(f.model_dump())

@app.post("/feedback/batch")
def post_batch(fs: list[Feedback]):
    out = {"ok": 0, "duplicate": 0, "conflict": 0}
    for f in fs: out[ingest(f.model_dump())["status"]] += 1
    return out

@app.get("/persona/{uid}/context")
def persona_context(uid: str, counterpart: str | None = None, calendar: str = "free", stress: str = "low"):
    p = FEEDBACK_MODELS.find_one({"_id": uid})
    if p is None: raise HTTPException(404, "unknown user")
    ensure_schema(p)
    return {"user_id": uid, "version": p.get("_v"), "tie": p["ties"].get(counterpart), "values": p["values"],
            "hard_rules": p["hard_rules"], "proposals": p["proposals"],
            "action_prior": action_prior(p, {"calendar": calendar, "stress": stress}), "calibration": calibration_summary(p)}

@app.get("/health")
def health(): return {"personas": FEEDBACK_MODELS.count_documents({}), "events": EVENTS.count_documents({})}

# ---------- WebSocket: send one event (object) or many (array); get acks back in the same order ----------
@app.websocket("/ws/feedback")
async def ws_feedback(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json(); acks = []
            for item in (msg if isinstance(msg, list) else [msg]):
                try: acks.append(await run_in_threadpool(ingest, Feedback.model_validate(item).model_dump()))
                except ValidationError as e: acks.append({"status": "invalid", "detail": str(e)[:300]})
            await ws.send_json(acks if isinstance(msg, list) else acks[0])
    except WebSocketDisconnect: pass