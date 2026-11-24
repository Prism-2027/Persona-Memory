# Action Block → Persona Memory integration

This folder contains only the production integration path.

## Run

From this folder, install `requirements.txt`, configure `MONGO_URI` and
`MONGO_DB`, then run:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

The Action Block posts the payload defined in `action_block_schema.py` to
`POST /feedback` or streams it to `/ws/feedback`. Batch ingestion is available
at `POST /feedback/batch`.

The service writes to the canonical `episodic_memory`, `relationship_memory`,
and `value_model` collections. `action_block_feedback` is only an idempotency
and processing audit log; it is not a separate persona database.

Existing stated values and hard rules are not overwritten. Inferred value
updates remain provisional and require confirmation. Synthetic datasets,
simulators, seed scripts, and the old standalone feedback learner are not part
of this integration.
