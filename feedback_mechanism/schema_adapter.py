"""Adapters from Action Feedback v1 into the Persona Memory schemas.

Writes schema-shaped episodic, relationship, and value records to dedicated
collections. Existing records are updated field-by-field; seed/sample files and
unrelated fields are never replaced.
"""
from datetime import datetime, timezone
import hashlib

from db import EPISODIC_MEMORIES, RELATIONSHIP_MEMORIES, VALUE_MEMORIES

def _iso(ts):
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()

def _key(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:20].upper()

def _clamp(value):
    return max(0.0, min(1.0, float(value)))

def _episode_id(fb):
    return "EP_" + str(fb["feedback_id"])

def _write_episode(fb):
    eid = _episode_id(fb)
    ctx, executed, response = fb["context"], fb["executed"], fb["response"]
    prediction = fb.get("prediction") or {}
    counterpart = fb.get("counterpart")
    doc = {
        "_id": eid,
        "user_id": fb["user_id"],
        "situation_id": fb["snapshot_id"],
        "timestamp": _iso(fb["ts"]),
        "entities_involved": [counterpart] if counterpart else [],
        "context_summary": {
            "situation_type": ctx.get("situation_type", "action_feedback"),
            "situation_subtype": ctx.get("situation_subtype", executed.get("action_type")),
            "user_activity": ctx.get("user_activity", ctx.get("calendar")),
            "stress_level": ctx.get("stress_level", ctx.get("stress")),
            "trigger_summary": ctx.get("trigger_summary", "Feedback received for an executed action")
        },
        "outcome": {
            "predicted_action": prediction.get("top"),
            "action_score": round(float(prediction.get("confidence", 0.0)) * 100),
            "actual_user_action": response.get("user_action"),
            "prediction_matched": (
                prediction.get("top") == response.get("user_action")
                if prediction.get("top") is not None and response.get("user_action") is not None
                else None
            ),
            "user_rationale": None,
            "emotional_valence": None
        },
        "follow_up": {
            "required": False,
            "promised_action": None,
            "deadline": None,
            "status": "not_required",
            "completed_at": None
        },
        "memory_impact": {
            "updated_collections": ["relationships", "value_model"] if counterpart else ["value_model"],
            "learning_note": "Action feedback recorded; inferred preferences and relationship signals updated where available."
        },
        "tags": ["action_feedback", response.get("outcome", "unknown")]
    }
    # Append-only: retries with the same feedback ID cannot rewrite an episode.
    EPISODIC_MEMORIES.update_one({"_id": eid}, {"$setOnInsert": doc}, upsert=True)
    return eid

def _score_entry(value, source, confidence, timestamp, evidence):
    return {
        "value": _clamp(value), "source": source, "confidence": _clamp(confidence),
        "updated_at": timestamp, "evidence_ids": [evidence]
    }

def _write_relationship(fb, reward, episode_id):
    person = fb.get("counterpart")
    if not person:
        return
    uid, ts = fb["user_id"], _iso(fb["ts"])
    rid = "REL_" + _key(uid, person)
    outcome = fb["response"]["outcome"]
    stakes = {"low": 0.35, "medium": 0.65, "high": 0.9}.get(fb.get("stakes", "low"), 0.35)
    old = RELATIONSHIP_MEMORIES.find_one({"_id": rid}) or {}
    scores = old.get("scores", {})
    old_trust = scores.get("trust", {}).get("value", 0.5)
    old_importance = scores.get("importance", {}).get("value", stakes)
    trust = _clamp(0.85 * old_trust + 0.15 * ((float(reward) + 1.0) / 2.0))
    importance = _clamp(0.9 * old_importance + 0.1 * stakes)
    confidence = min(0.95, 0.5 + 0.05 * (len(scores.get("trust", {}).get("evidence_ids", [])) + 1))
    trust_evidence = list(dict.fromkeys(scores.get("trust", {}).get("evidence_ids", []) + [episode_id]))
    importance_evidence = list(dict.fromkeys(scores.get("importance", {}).get("evidence_ids", []) + [episode_id]))
    tense = outcome in ("dismissed", "overridden")
    base = {
        "_id": rid, "user_id": uid, "person_id": str(person),
        "identity": {"name": str(person), "aliases": [], "role": "unknown", "contact_identifiers": []},
        "scores": {
            "closeness": _score_entry(0.5, "inferred", 0.3, ts, episode_id),
            "trust": _score_entry(trust, "inferred", confidence, ts, episode_id),
            "importance": _score_entry(importance, "inferred", confidence, ts, episode_id)
        },
        "tie_state": {
            "current_status": "needs_attention" if tense else "active",
            "recent_tension": tense, "relationship_trend": "needs_review" if tense else "stable",
            "support_balance": "unknown", "interaction_reciprocity": 0.5,
            "last_interaction_at": ts, "source": "inferred", "confidence": confidence,
            "evidence_ids": [episode_id]
        },
        "interaction_stats": {
            "total_interactions": 0, "calls_count": 0, "messages_count": 0, "meetings_count": 0,
            "average_interactions_per_week": 0, "average_response_time_minutes": None,
            "user_initiation_ratio": None, "other_person_initiation_ratio": None,
            "calculation_period_days": 90, "updated_at": ts
        },
        "communication_preferences": {
            "preferred_channels": [], "preferred_contact_times": [],
            "source": "inferred", "confidence": confidence, "evidence_ids": [episode_id]
        },
        "behavioral_patterns": {
            "user_behavior": [], "other_person_behavior": [],
            "observed_since": ts[:10], "updated_at": ts
        },
        "relationship_boundaries": {
            "known_boundaries": [], "sensitive_topics": [], "interaction_restrictions": [],
            "source": "unknown", "confidence": 0.0, "evidence_ids": []
        },
        "shared_context": {
            "known_connections": [], "shared_activities": [], "common_interests": [],
            "significant_shared_events": []
        },
        "score_history": [],
        "metadata": {"created_at": ts, "updated_at": ts, "last_verified_at": None, "schema_version": "2.0"}
    }
    # Insert the schema-shaped base only when absent, then patch only learned fields.
    RELATIONSHIP_MEMORIES.update_one({"_id": rid}, {"$setOnInsert": base}, upsert=True)
    RELATIONSHIP_MEMORIES.update_one(
        {"_id": rid},
        {
            "$set": {
                "scores.trust": {**_score_entry(trust, "inferred", confidence, ts, episode_id), "evidence_ids": trust_evidence},
                "scores.importance": {**_score_entry(importance, "inferred", confidence, ts, episode_id), "evidence_ids": importance_evidence},
                "tie_state.current_status": "needs_attention" if tense else "active",
                "tie_state.recent_tension": tense,
                "tie_state.relationship_trend": "needs_review" if tense else "stable",
                "tie_state.last_interaction_at": ts,
                "tie_state.source": "inferred",
                "tie_state.confidence": confidence,
                "interaction_stats.updated_at": ts,
                "metadata.updated_at": ts
            },
            "$inc": {"interaction_stats.total_interactions": 1},
            "$addToSet": {
                "tie_state.evidence_ids": episode_id
            },
            "$push": {
                "score_history": {"$each": [
                    {"metric": "trust", "old_value": old_trust, "new_value": trust,
                     "reason": "Action feedback signal", "evidence_ids": [episode_id], "timestamp": ts},
                    {"metric": "importance", "old_value": old_importance, "new_value": importance,
                     "reason": "Situation stakes signal", "evidence_ids": [episode_id], "timestamp": ts}
                ], "$slice": -100}
            }
        }
    )

def _write_values(fb, persona, episode_id):
    uid, ts = fb["user_id"], _iso(fb["ts"])
    learned = persona.get("values", {})
    labels = {
        "channel": ("Preferred communication channel", "communication"),
        "tone": ("Preferred communication tone", "communication"),
        "timing": ("Preferred contact timing", "communication"),
        "action_type": ("Preferred action type", "actions")
    }
    for dimension, (label, domain) in labels.items():
        options = learned.get(dimension, {})
        if not options:
            continue
        preferred, details = max(options.items(), key=lambda item: item[1].get("score", 0.0))
        vid = "VAL_" + _key(uid, dimension)
        old = VALUE_MEMORIES.find_one({"_id": vid})
        # Never downgrade or rewrite an explicitly stated value or hard rule.
        if old and (old.get("category") == "hard_rule" or old.get("provenance", {}).get("source") == "stated"):
            continue
        count = int(details.get("n", 1))
        confidence = min(0.95, 0.5 + 0.05 * count)
        score = _clamp(details.get("score", 0.5))
        value_doc = {
            "_id": vid, "user_id": uid, "value_name": label,
            "category": "preference", "domain": domain,
            "statement": f"The user tends to prefer {preferred} for {dimension.replace('_', ' ')}.",
            "behavioral_preference": {
                "preferred_action": str(preferred), "avoid_actions": [], "tone_guidance": None
            },
            "priority_weight": score, "conditions": {}, "exceptions": [],
            "provenance": {
                "source": "inferred", "confidence": confidence, "created_at": ts,
                "last_validated_at": ts, "supporting_episodes": [episode_id],
                "contradicting_episodes": []
            },
            "validation": {
                "status": "provisional", "needs_user_confirmation": True,
                "contradiction_count": 0
            },
            "active": True
        }
        VALUE_MEMORIES.update_one({"_id": vid}, {"$setOnInsert": value_doc}, upsert=True)
        VALUE_MEMORIES.update_one(
            {"_id": vid},
            {
                "$set": {
                    "statement": value_doc["statement"],
                    "behavioral_preference": value_doc["behavioral_preference"],
                    "priority_weight": score,
                    "provenance.source": "inferred",
                    "provenance.confidence": confidence,
                    "provenance.last_validated_at": ts,
                    "validation.status": "provisional",
                    "validation.needs_user_confirmation": True,
                    "active": True
                },
                "$addToSet": {"provenance.supporting_episodes": episode_id}
            },
            upsert=True
        )

def sync_persona_schemas(fb, reward, persona):
    """Persist one feedback event into the three Persona Memory schema collections."""
    episode_id = _write_episode(fb)
    _write_relationship(fb, reward, episode_id)
    _write_values(fb, persona, episode_id)
    return episode_id
