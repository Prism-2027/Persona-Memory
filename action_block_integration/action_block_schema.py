"""Action Block feedback payload contract (v1). Keep aligned with Action Block output."""
from typing import Literal
from pydantic import BaseModel, Field

class Executed(BaseModel):
    action_type: str
    channel: str
    tone: str | None = None
    timing: str | None = None

class Response(BaseModel):
    outcome: Literal["accepted", "modified", "ignored", "dismissed", "overridden"]
    latency_ms: int | None = None
    user_action: str | None = None

class Prediction(BaseModel):
    top: str
    confidence: float = Field(ge=0, le=1)
    probs: dict[str, float] = {}

class Feedback(BaseModel):
    feedback_id: str
    user_id: str
    snapshot_id: str
    ts: float
    context: dict[str, str]
    executed: Executed
    response: Response
    prediction: Prediction | None = None
    counterpart: str | None = None
    rating: Literal[-1, 0, 1] | None = None
    stakes: Literal["low", "medium", "high"] = "low"
