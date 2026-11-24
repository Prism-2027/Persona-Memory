"""Generate dataset.json: seeded Persona Memory docs + a large Action Block feedback stream
Usage: python make_dataset.py [events_per_persona=700]
Each persona has HIDDEN true preferences (saved under ground_truth, never sent to the memory)
so you can later check that the learning loop recovers them."""
import json, math, random, sys
from datetime import datetime, timezone

N = int(sys.argv[1]) if len(sys.argv) > 1 else 700
rnd = random.Random(42)
clip = lambda x, lo=0.0, hi=1.0: max(lo, min(hi, x))

CAL = {"free": 0.0, "commute": 0.3, "busy": 0.6, "sleep": 0.8, "critical": 1.0}
CHANNELS, TONES, TIMINGS = ["haptic", "screen", "audio"], ["warm", "neutral", "formal", "brief"], ["now", "in_15m", "after_block"]
ACTIONS = ["text_reassure", "auto_call_back", "hold_and_summarize", "schedule_callback", "escalate_notify", "silent_log"]
USER_ACTIONS = ["ignore", "send_text", "pick_up", "call_back_later", "reply_later"]
REL = {  # relationship: (importance, urgency tendency, how often they contact)
    "partner": (.95, .5, 3), "parent": (.9, .6, 2.5), "close_friend": (.85, .4, 2.5), "sibling": (.8, .5, 1.5),
    "boss": (.7, .7, 2), "colleague": (.5, .5, 2.5), "client": (.6, .6, 1.5), "unknown": (.1, .3, 1)}
NAMES = ["Riya", "Aman", "Neha", "Vikram", "Pooja", "Karan", "Isha", "Rahul", "Sneha", "Dev", "Tanya", "Nikhil", "Divya", "Arnav",
         "Kavya", "Yash", "Ritu", "Manish", "Aarti", "Sahil", "Preeti", "Gaurav", "Shruti", "Varun", "Anjali", "Mohit", "Nisha",
         "Harsh", "Komal", "Rohit", "Mansi", "Tarun", "Payal", "Ishaan", "Bhavna", "Sumit", "Lata", "Kunal", "Zoya", "Naveen",
         "Ojas", "Rhea", "Veer", "Alka", "Jatin", "Mira", "Param", "Sana", "Tushar", "Uma"]
P = [  # persona bank: hidden true preferences + hard rules
 dict(id="u_arjun", name="Arjun", role="CS student", stress=.65, cal=[3,1,3,2,3], pickup=-.2,
      chan=dict(haptic=.9, screen=.55, audio=.15), tone=dict(warm=.8, neutral=.6, formal=.3, brief=.7), timing={"now":.5,"in_15m":.6,"after_block":.85},
      rule=("no_audio_in_critical", {"calendar": "critical"}, {"channel": "audio"})),
 dict(id="u_meera", name="Meera", role="Doctor", stress=.7, cal=[1,1,5,1,4], pickup=-.5,
      chan=dict(screen=.85, haptic=.6, audio=.2), tone=dict(formal=.7, neutral=.8, warm=.5, brief=.75), timing={"now":.45,"in_15m":.6,"after_block":.8},
      rule=("no_audio_at_office", {"location": "office"}, {"channel": "audio"})),
 dict(id="u_kabir", name="Kabir", role="Startup founder", stress=.8, cal=[1,2,4,1,3], pickup=.4,
      chan=dict(audio=.8, screen=.6, haptic=.5), tone=dict(brief=.9, neutral=.6, formal=.5, warm=.4), timing={"now":.9,"in_15m":.5,"after_block":.3},
      rule=("no_autocall_in_critical", {"calendar": "critical"}, {"action_type": "auto_call_back"})),
 dict(id="u_simran", name="Simran", role="Teacher", stress=.45, cal=[3,2,4,2,1], pickup=0,
      chan=dict(haptic=.8, screen=.7, audio=.35), tone=dict(warm=.9, neutral=.5, formal=.4, brief=.4), timing={"now":.6,"in_15m":.75,"after_block":.6},
      rule=("no_audio_while_teaching", {"calendar": "busy"}, {"channel": "audio"})),
 dict(id="u_rohan", name="Rohan", role="Night-shift nurse", stress=.6, cal=[2,2,2,4,2], pickup=.1,
      chan=dict(haptic=.75, screen=.6, audio=.5), tone=dict(neutral=.8, brief=.7, warm=.6, formal=.4), timing={"now":.7,"in_15m":.6,"after_block":.5},
      rule=("no_audio_in_sleep", {"calendar": "sleep"}, {"channel": "audio"})),
 dict(id="u_ananya", name="Ananya", role="Researcher", stress=.4, cal=[3,1,3,1,4], pickup=-.6,
      chan=dict(screen=.8, haptic=.55, audio=.1), tone=dict(formal=.8, neutral=.7, brief=.6, warm=.35), timing={"now":.25,"in_15m":.6,"after_block":.9},
      rule=("no_escalate_in_critical", {"calendar": "critical"}, {"action_type": "escalate_notify"})),
]

def softmax(d, T=1.0):
    m = max(d.values()); e = {k: math.exp((v - m) / T) for k, v in d.items()}; s = sum(e.values())
    return {k: v / s for k, v in e.items()}

def fit(a, imp, urg, crit):   # how well an action type suits the situation (hidden)
    return clip({"text_reassure": .4 + .5 * imp * (.3 + crit), "auto_call_back": .7 - .6 * crit,
                 "hold_and_summarize": .3 + .5 * crit, "schedule_callback": .5 + .2 * imp,
                 "escalate_notify": .2 + .7 * urg, "silent_log": .7 - .6 * imp}[a])

def make_persona(p):
    contacts = []
    for name, rel in zip(rnd.sample(NAMES, 8), REL):
        imp, urg, freq = REL[rel]
        contacts.append(dict(name=name, rel=rel, imp=clip(imp + rnd.uniform(-.05, .05)), urg=urg, freq=freq))
    rid, when, forbid = p["rule"]
    memory = {"_id": p["id"], "_v": 0, "profile": {"name": p["name"], "role": p["role"]},
        "seed": {"source": "persona_bank_v1", "stated_preferences": {
            "preferred_channel": max(p["chan"], key=p["chan"].get), "preferred_tone": max(p["tone"], key=p["tone"].get)}},
        "ties": {c["name"]: {"relationship": c["rel"], "importance": round(c["imp"], 2), "warmth": .5, "strain": 0.0,
                             "n": 0, "last_contact": None, "evidence": []} for c in contacts},
        "values": {"channel": {}, "tone": {}, "timing": {}},
        "hard_rules": [{"id": rid, "when": when, "forbid": forbid}], "proposals": {}, "counts": {},
        "calib": {"n": 0, "brier": 0.0, "bins": [[0, 0.0, 0] for _ in range(10)]}}
    return contacts, memory

def make_events(p, contacts, memory):
    t0 = datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp()
    times = sorted(t0 + rnd.uniform(0, 90 * 86400) for _ in range(N))
    rule = memory["hard_rules"][0]; out = []
    for i, ts in enumerate(times):
        cal = rnd.choices(list(CAL), p["cal"])[0]; crit = CAL[cal]
        s = clip(p["stress"] * .6 + crit * .4 + rnd.gauss(0, .2)); stress = "low" if s < .35 else "medium" if s < .65 else "high"
        loc = "transit" if cal == "commute" else "home" if cal == "sleep" else rnd.choice(["home", "office"])
        c = rnd.choices(contacts, [x["freq"] for x in contacts])[0]; imp, urg = c["imp"], clip(c["urg"] + rnd.gauss(0, .2))
        ctx = {"calendar": cal, "stress": stress, "location": loc}
        stakes = "high" if urg > .7 and imp > .6 else "medium" if urg > .45 or imp > .7 else "low"
        # --- what the Action Block did ---
        w = {"text_reassure": 3, "hold_and_summarize": 2, "schedule_callback": 2, "silent_log": 1, "escalate_notify": 1 + 3 * urg, "auto_call_back": 1}
        ex = {"action_type": rnd.choices(ACTIONS, [w[a] for a in ACTIONS])[0], "channel": rnd.choices(CHANNELS, [.45, .35, .2])[0],
              "tone": rnd.choice(TONES), "timing": rnd.choices(TIMINGS, [.2, .2, .6] if crit >= .6 else [.5, .3, .2])[0]}
        # --- how the user reacted (hidden preferences) ---
        pa = clip(.05 + .9 * (.40 * p["chan"][ex["channel"]] + .20 * p["tone"][ex["tone"]] + .15 * p["timing"][ex["timing"]]
                              + .25 * fit(ex["action_type"], imp, urg, crit)), .02, .97)
        if all(ctx.get(k) == v for k, v in rule["when"].items()) and all(ex.get(k) == v for k, v in rule["forbid"].items()):
            pa *= .15                                            # hard-rule violation: mostly rejected, sometimes accepted
        u = rnd.random()
        if u < pa * .85: outcome = "accepted"
        elif u < pa: outcome = "modified"
        else: outcome = rnd.choices(["ignored", "dismissed", "overridden"], [.35, .35 + .2 * (1 - pa), .3])[0]
        base = {"accepted": 6000, "modified": 15000, "dismissed": 3000, "overridden": 2500}.get(outcome)
        latency = int(rnd.lognormvariate(math.log(base), .8)) if base else None
        rating = (1 if outcome in ("accepted", "modified") else -1) if rnd.random() < .08 else None
        # --- what the user really did, and what the Prediction module guessed ---
        st = STRESS_V[stress]
        logit = {"ignore": 2 * crit * (1 - imp) + .6 * st - .4, "send_text": 1.6 * imp * (.3 + crit) + .2,
                 "pick_up": 3 * imp * urg - 2.6 * crit + p["pickup"] + .8, "call_back_later": 1.4 * imp * crit * (1 - urg) + .1,
                 "reply_later": .6 + .5 * (1 - imp)}
        true_p = softmax(logit); actual = rnd.choices(USER_ACTIONS, [true_p[a] for a in USER_ACTIONS])[0]
        probs = softmax({a: math.log(true_p[a]) + rnd.gauss(0, .5) for a in USER_ACTIONS}, T=.75)   # overconfident predictor
        top = max(probs, key=probs.get)
        out.append({"feedback_id": f"fb_{p['id']}_{i:05d}", "user_id": p["id"], "snapshot_id": f"snap_{p['id']}_{i:05d}",
            "ts": round(ts, 3), "context": ctx, "stakes": stakes, "counterpart": c["name"], "executed": ex,
            "response": {"outcome": outcome, "latency_ms": latency, "user_action": actual}, "rating": rating,
            "prediction": {"top": top, "confidence": round(probs[top], 4), "probs": {k: round(v, 4) for k, v in probs.items()}}})
    return out

STRESS_V = {"low": 0.0, "medium": 0.5, "high": 1.0}
personas, events = [], []
for p in P:
    contacts, memory = make_persona(p)
    personas.append({"persona_memory": memory, "ground_truth": {"channel": p["chan"], "tone": p["tone"], "timing": p["timing"]}})
    events += make_events(p, contacts, memory)
events.sort(key=lambda e: e["ts"])
json.dump({"meta": {"contract": "ActionFeedback v1", "n_personas": len(P), "n_events": len(events),
                    "note": "ground_truth is for evaluation only; never send it to the memory service"},
           "personas": personas, "action_feedback": events}, open("dataset.json", "w"), separators=(",", ":"))
print(f"dataset.json: {len(P)} personas, {len(events)} events")