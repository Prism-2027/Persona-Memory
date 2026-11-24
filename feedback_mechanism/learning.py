"""Pure learning logic (no DB, no web). Input: persona doc + feedback dict -> mutates persona doc."""
import math
OUTCOME_REWARD = {"accepted": 1.0, "modified": .4, "ignored": -.3, "dismissed": -.7, "overridden": -1.0}
KEY_FIELDS, BINS = ("calendar", "stress"), 10
FEATS = ("action_type", "channel", "tone", "timing")   # factors the value model learns jointly
LR, L2 = 0.1, 0.002                                   # AdaGrad step size, weight decay

def reward(fb):
    r = OUTCOME_REWARD[fb["response"]["outcome"]]
    if fb.get("rating") is not None: r = .3 * r + .7 * fb["rating"]            # explicit signal outweighs implicit
    lat = fb["response"].get("latency_ms")
    if r > 0 and lat and lat > 60_000: r *= .7                                  # slow acceptance = weaker
    return max(-1.0, min(1.0, r))

def ema(old, target, n):                                                         # fast early, stable later (floor 0.1)
    a = max(.1, 1 / (n + 2)); return (1 - a) * old + a * target

def ctx_key(ctx): return "|".join(f"{k}={ctx.get(k, 'any')}" for k in KEY_FIELDS)

def ensure_schema(p):                                                            # tolerate docs written by other tools
    p.setdefault("ties", {}); p.setdefault("hard_rules", []); p.setdefault("proposals", {}); p.setdefault("counts", {})
    v = p.setdefault("values", {})
    for d in FEATS: v.setdefault(d, {})
    p.setdefault("model", {"w": {}, "g": {}, "cnt": {}, "n": 0})
    p.setdefault("calib", {"n": 0, "brier": 0.0, "bins": [[0, 0.0, 0] for _ in range(BINS)]})
    return p

def blank_persona(uid):
    return ensure_schema({"_id": uid, "_v": 0, "profile": {}})

def sigmoid(x): return 1 / (1 + math.exp(-max(-30, min(30, x))))

def update_model(p, ex, ctx, target):
    """Online logistic regression on one-hot factors (AdaGrad). All factors are fitted together, so each
    option's weight is its effect AFTER accounting for the others (fixes the credit-assignment problem)."""
    m, w, g = p["model"], p["model"]["w"], p["model"]["g"]
    x = [f"{d}={ex[d]}" for d in FEATS if ex.get(d)] + [f"ctx_{k}={ctx[k]}" for k in KEY_FIELDS if ctx.get(k)]
    err = sigmoid(w.get("__bias", 0.0) + sum(w.get(f, 0.0) for f in x)) - target
    for f in x + ["__bias"]:
        grad = err + (L2 * w.get(f, 0.0) if f != "__bias" else 0.0)
        g[f] = g.get(f, 0.0) + grad * grad
        w[f] = w.get(f, 0.0) - LR * grad / math.sqrt(g[f] + 1e-8)
        if f != "__bias": m["cnt"][f] = m["cnt"].get(f, 0) + 1
    m["n"] += 1
    b = w.get("__bias", 0.0)                                   # readable summary: score = P(accept) with other factors neutral
    for f, wt in w.items():
        if f != "__bias" and not f.startswith("ctx_"):          # context terms only absorb situation effects
            d, opt = f.split("=", 1)
            p["values"].setdefault(d, {})[opt] = {"score": round(sigmoid(b + wt), 4), "weight": round(wt, 4), "n": m["cnt"].get(f, 0)}

def violated_rule(p, fb):
    for h in p["hard_rules"]:
        if all(fb["context"].get(k) == v for k, v in h["when"].items()) and \
           all(fb["executed"].get(k) == v for k, v in h["forbid"].items()): return h["id"]

def learn(p, fb, r):
    ensure_schema(p); ex, ctx, resp = fb["executed"], fb["context"], fb["response"]; target = .5 + .5 * r
    if fb.get("counterpart"):                                                    # relationship graph
        t = p["ties"].setdefault(fb["counterpart"], {"relationship": "unknown", "importance": .5, "warmth": .5,
                                                     "strain": 0.0, "n": 0, "last_contact": None, "evidence": []})
        t["warmth"] = ema(t["warmth"], target, t["n"])
        t["strain"] = ema(t["strain"], float(resp["outcome"] in ("dismissed", "overridden")), t["n"])
        t["n"] += 1; t["last_contact"] = fb["ts"]; t["evidence"] = (t["evidence"] + [fb["feedback_id"]])[-10:]
    rule = violated_rule(p, fb)                                                  # value model
    if rule:                                                                     # hard rules are never learned from or edited
        if r > 0:
            pr = p["proposals"].setdefault(rule, {"accepted_violations": 0}); pr["accepted_violations"] += 1
            pr["last_feedback_id"] = fb["feedback_id"]
    else:
        update_model(p, ex, ctx, target)
    act = resp.get("user_action")                                                # prediction statistics
    if act:
        c = p["counts"].setdefault(ctx_key(ctx), {}); c[act] = c.get(act, 0) + 1
        pred = fb.get("prediction")
        if pred:
            hit, conf, cal = int(pred["top"] == act), pred["confidence"], p["calib"]
            b = p["calib"]["bins"][min(int(conf * BINS), BINS - 1)]
            cal["n"] += 1; cal["brier"] += (conf - hit) ** 2; b[0] += 1; b[1] += conf; b[2] += hit

def action_prior(p, ctx):                                                        # add-one smoothed P(action | context)
    c = p.get("counts", {}).get(ctx_key(ctx), {}); tot = sum(c.values()) + len(c)
    return {a: round((n + 1) / tot, 3) for a, n in c.items()}

def calibration_summary(p):
    cal = p.get("calib") or {"n": 0, "bins": []}; n = cal["n"]
    if not n: return {"n": 0}
    rows = [{"conf": round(s / k, 3), "acc": round(h / k, 3), "n": k} for k, s, h in cal["bins"] if k]
    return {"n": n, "brier": round(cal["brier"] / n, 4), "ece": round(sum(r["n"] / n * abs(r["conf"] - r["acc"]) for r in rows), 4), "bins": rows}