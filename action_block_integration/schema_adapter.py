"""Map Action Block feedback into Persona Memory's three canonical schemas.

No synthetic dataset, separate learned persona document, or training loop is used.
Feedback produces evidence-backed episodic records and conservative inferred
relationship/value updates. Existing stated hard rules are never overwritten.
"""
from datetime import datetime, timezone
import hashlib

from db import EPISODIC_MEMORIES, RELATIONSHIP_MEMORIES, VALUE_MEMORIES

def _timestamp(value):
    return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()

def _stable_id(prefix, *parts):
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return prefix + hashlib.sha256(raw).hexdigest()[:20].upper()

def _unit(value):
    return max(0.0, min(1.0, float(value)))

def _episode_id(feedback):
    return "EP_" + str(feedback["feedback_id"])

def _write_episode(feedback, reward):
    episode_id = _episode_id(feedback)
    context = feedback["context"]
    executed = feedback["executed"]
    response = feedback["response"]
    prediction = feedback.get("prediction") or {}
    counterpart = feedback.get("counterpart")
    document = {
        "_id": episode_id,
        "user_id": feedback["user_id"],
        "situation_id": feedback["snapshot_id"],
        "timestamp": _timestamp(feedback["ts"]),
        "entities_involved": [counterpart] if counterpart else [],
        "context_summary": {
            "situation_type": context.get("situation_type", "action_block"),
            "situation_subtype": context.get("situation_subtype", executed.get("action_type")),
            "user_activity": context.get("user_activity", context.get("calendar")),
            "stress_level": context.get("stress_level", context.get("stress")),
            "trigger_summary": context.get("trigger_summary", "Action Block feedback")
        },
        "outcome": {
            "predicted_action": prediction.get("top"),
            "action_score": round(float(prediction.get("confidence", 0.0)) * 100),
            "actual_user_action": response.get("user_action", response["outcome"]),
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
            "learning_note": "Action Block outcome recorded as evidence for future personalization."
        },
        "tags": ["action_block", response["outcome"]]
    }
    EPISODIC_MEMORIES.update_one(
        {"_id": episode_id},
        {"$setOnInsert": document},
        upsert=True
    )
    return episode_id

def _write_relationship(feedback, reward, episode_id):
    person_id = feedback.get("counterpart")
    if not person_id:
        return
    user_id = feedback["user_id"]
    timestamp = _timestamp(feedback["ts"])
    relationship_id = "REL_" + _stable_id("", user_id, person_id)
    old = RELATIONSHIP_MEMORIES.find_one({"_id": relationship_id}) or {}
    old_scores = old.get("scores", {})
    old_trust = float(old_scores.get("trust", {}).get("value", 0.5))
    old_importance = float(old_scores.get("importance", {}).get("value", feedback.get("stakes") == "high"))
    target_trust = (reward + 1.0) / 2.0
    trust = _unit(0.85 * old_trust + 0.15 * target_trust)
    stakes = {"low": 0.35, "medium": 0.65, "high": 0.9}.get(feedback.get("stakes", "low"), 0.35)
    importance = _unit(0.9 * old_importance + 0.1 * stakes)
    if episode_id in old.get("tie_state", {}).get("evidence_ids", []):
        return
    trust_evidence = list(dict.fromkeys(old_scores.get("trust", {}).get("evidence_ids", []) + [episode_id]))
    importance_evidence = list(dict.fromkeys(old_scores.get("importance", {}).get("evidence_ids", []) + [episode_id]))
    confidence = min(0.95, 0.5 + 0.05 * len(trust_evidence))
    tense = feedback["response"]["outcome"] in ("dismissed", "overridden")

    base = {
        "_id": relationship_id,
        "user_id": user_id,
        "person_id": str(person_id),
        "identity": {"name": str(person_id), "aliases": [], "role": "unknown", "contact_identifiers": []},
        "scores": {
            "closeness": {"value": 0.5, "source": "inferred", "confidence": 0.3, "updated_at": timestamp, "evidence_ids": []},
            "trust": {"value": 0.5, "source": "inferred", "confidence": 0.3, "updated_at": timestamp, "evidence_ids": []},
            "importance": {"value": stakes, "source": "inferred", "confidence": 0.3, "updated_at": timestamp, "evidence_ids": []}
        },
        "tie_state": {
            "current_status": "active", "recent_tension": False, "relationship_trend": "stable",
            "support_balance": "unknown", "interaction_reciprocity": 0.5,
            "last_interaction_at": timestamp, "source": "inferred", "confidence": 0.3, "evidence_ids": []
        },
        "interaction_stats": {
            "total_interactions": 0, "calls_count": 0, "messages_count": 0, "meetings_count": 0,
            "average_interactions_per_week": 0, "average_response_time_minutes": None,
            "user_initiation_ratio": None, "other_person_initiation_ratio": None,
            "calculation_period_days": 90, "updated_at": timestamp
        },
        "communication_preferences": {
            "preferred_channels": [], "preferred_contact_times": [],
            "source": "inferred", "confidence": 0.0, "evidence_ids": []
        },
        "behavioral_patterns": {
            "user_behavior": [], "other_person_behavior": [],
            "observed_since": timestamp[:10], "updated_at": timestamp
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
        "metadata": {"created_at": timestamp, "updated_at": timestamp, "last_verified_at": None, "schema_version": "2.0"}
    }
    RELATIONSHIP_MEMORIES.update_one(
        {"_id": relationship_id},
        {"$setOnInsert": base},
        upsert=True
    )
    RELATIONSHIP_MEMORIES.update_one(
        {"_id": relationship_id},
        {
            "$set": {
                "scores.trust": {
                    "value": trust, "source": "inferred", "confidence": confidence,
                    "updated_at": timestamp, "evidence_ids": trust_evidence
                },
                "scores.importance": {
                    "value": importance, "source": "inferred", "confidence": confidence,
                    "updated_at": timestamp, "evidence_ids": importance_evidence
                },
                "tie_state.current_status": "needs_attention" if tense else "active",
                "tie_state.recent_tension": tense,
                "tie_state.relationship_trend": "needs_review" if tense else "stable",
                "tie_state.last_interaction_at": timestamp,
                "tie_state.source": "inferred",
                "tie_state.confidence": confidence,
                "interaction_stats.updated_at": timestamp,
                "metadata.updated_at": timestamp
            },
            "$inc": {"interaction_stats.total_interactions": 1},
            "$addToSet": {"tie_state.evidence_ids": episode_id},
            "$push": {
                "score_history": {
                    "$each": [
                        {"metric": "trust", "old_value": old_trust, "new_value": trust,
                         "reason": "Action Block feedback", "evidence_ids": [episode_id], "timestamp": timestamp},
                        {"metric": "importance", "old_value": old_importance, "new_value": importance,
                         "reason": "Action Block situation stakes", "evidence_ids": [episode_id], "timestamp": timestamp}
                    ],
                    "$slice": -100
                }
            }
        }
    )

def _write_values(feedback, signals, episode_id):
    user_id = feedback["user_id"]
    timestamp = _timestamp(feedback["ts"])
    for dimension, options in signals.get("values", {}).items():
        if not options:
            continue
        preferred, evidence = max(options.items(), key=lambda item: item[1].get("score", 0.0))
        value_id = "VAL_" + _stable_id("", user_id, dimension)
        old = VALUE_MEMORIES.find_one({"_id": value_id})
        if old and (
            old.get("category") == "hard_rule"
            or old.get("provenance", {}).get("source") == "stated"
        ):
            continue

        count = int(evidence.get("n", 1))
        confidence = min(0.95, 0.5 + 0.05 * count)
        score = _unit(evidence.get("score", 0.5))
        if score <= 0.5:
            continue
        label = dimension.replace("_", " ")
        value_document = {
            "_id": value_id,
            "user_id": user_id,
            "value_name": "Action Block " + label.title() + " Preference",
            "category": "preference",
            "domain": "communication" if dimension in ("channel", "tone", "timing") else "actions",
            "statement": f"The user tends to prefer {preferred} for {label}.",
            "behavioral_preference": {
                "preferred_action": str(preferred), "avoid_actions": [], "tone_guidance": None
            },
            "priority_weight": score,
            "conditions": {},
            "exceptions": [],
            "provenance": {
                "source": "inferred", "confidence": confidence, "created_at": timestamp,
                "last_validated_at": timestamp, "supporting_episodes": [episode_id],
                "contradicting_episodes": []
            },
            "validation": {
                "status": "provisional", "needs_user_confirmation": True, "contradiction_count": 0
            },
            "active": True
        }
        VALUE_MEMORIES.update_one(
            {"_id": value_id},
            {"$setOnInsert": value_document},
            upsert=True
        )
        VALUE_MEMORIES.update_one(
            {"_id": value_id},
            {
                "$set": {
                    "statement": value_document["statement"],
                    "behavioral_preference": value_document["behavioral_preference"],
                    "priority_weight": score,
                    "provenance.confidence": confidence,
                    "provenance.last_validated_at": timestamp,
                    "validation.status": "provisional",
                    "validation.needs_user_confirmation": True
                },
                "$addToSet": {"provenance.supporting_episodes": episode_id}
            }
        )

def sync_persona_schemas(feedback, reward, signals):
    """Persist one Action Block feedback event into Persona Memory's three schemas."""
    episode_id = _write_episode(feedback, reward)
    _write_relationship(feedback, reward, episode_id)
    _write_values(feedback, signals, episode_id)
    return episode_id
