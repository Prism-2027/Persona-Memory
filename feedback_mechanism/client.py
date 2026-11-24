"""Action Block simulator: streams dataset.json events to the Persona Memory service.
  python client.py --mode rest            (batched HTTP)
  python client.py --mode ws              (WebSocket stream)
  options: --limit N  --user u_arjun  --window 50  --delay 0.01 (seconds between events, ws)  --no-report"""

import argparse, asyncio, json, time
from collections import Counter
import httpx, websockets

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["rest", "ws"], default="ws"); ap.add_argument("--url", default="http://127.0.0.1:8000")
ap.add_argument("--data", default="dataset.json"); ap.add_argument("--limit", type=int); ap.add_argument("--user")
ap.add_argument("--batch", type=int, default=200); ap.add_argument("--window", type=int, default=50)
ap.add_argument("--delay", type=float, default=0); ap.add_argument("--no-report", action="store_true")
a = ap.parse_args()

data = json.load(open(a.data))
events = sorted(data["action_feedback"], key=lambda e: e["ts"])
if a.user: events = [e for e in events if e["user_id"] == a.user]
if a.limit: events = events[:a.limit]

def send_rest():
    tot = Counter()
    with httpx.Client(base_url=a.url, timeout=120) as c:
        for i in range(0, len(events), a.batch):
            r = c.post("/feedback/batch", json=events[i:i + a.batch]); r.raise_for_status(); tot.update(r.json())
    return tot

async def send_ws():
    tot, sent, acked = Counter(), 0, 0
    async with websockets.connect(a.url.replace("http", "ws") + "/ws/feedback", max_size=None) as ws:
        for e in events:
            await ws.send(json.dumps(e)); sent += 1
            while sent - acked >= a.window: tot[json.loads(await ws.recv())["status"]] += 1; acked += 1
            if a.delay: await asyncio.sleep(a.delay)
        while acked < sent: tot[json.loads(await ws.recv())["status"]] += 1; acked += 1
    return tot

t = time.time(); res = send_rest() if a.mode == "rest" else asyncio.run(send_ws())
print(f"{a.mode}: sent {len(events)} events in {time.time() - t:.1f}s -> {dict(res)}")

if not a.no_report:                                   # compare what the memory learned with the hidden truth
    hits = total = 0
    with httpx.Client(base_url=a.url) as c:
        print(f"\n{'user':9} {'channel':16} {'tone':16} {'timing':20} {'ECE':7} {'Brier':7} rule-violations accepted")
        for p in data["personas"]:
            uid = p["persona_memory"]["_id"]
            if a.user and uid != a.user: continue
            ctx = c.get(f"/persona/{uid}/context").json(); cells = []
            for dim in ("channel", "tone", "timing"):
                learned = {k: v["weight"] for k, v in ctx["values"][dim].items()}; true = p["ground_truth"][dim]
                top = max(learned, key=lambda k: learned[k])
                ok = top == max(true, key=lambda k: true[k])
                hits += ok; total += 1; cells.append(f"{top} {'OK' if ok else 'MISS(true ' + max(true, key=true.get) + ')'}")
            cal = ctx["calibration"]; viol = sum(v["accepted_violations"] for v in ctx["proposals"].values())
            print(f"{uid:9} {cells[0]:16} {cells[1]:16} {cells[2]:20} {cal.get('ece', '-')!s:7} {cal.get('brier', '-')!s:7} {viol}")
    print(f"\nlearned the true favourite for {hits}/{total} preference slots")



    #MONGO_URI=mock python3 -m uvicorn server:app --port 8000
    #python3 client.py --mode ws