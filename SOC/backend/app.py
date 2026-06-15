import os, uuid, threading, requests as req
from collections import deque
from datetime import datetime, timezone
from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS

app = Flask(__name__, static_folder=None)
app.config["SECRET_KEY"] = os.urandom(32).hex()
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ── In-memory stores ──────────────────────────────────────────
pending_log_queue = deque(maxlen=500)
pending_decisions = {}
decision_history  = deque(maxlen=500)
ingest_log_store  = deque(maxlen=1000)
_lock = threading.Lock()

# ── SCADA / Laravel config ────────────────────────────────────
MACHINES_SYSTEM = os.getenv("LARAVEL_URL", "http://127.0.0.1:8000")

def _now():
    return datetime.now(timezone.utc).isoformat()

# ════════════════════════════════════════════════════════════════
#  SCADA ACTION — calls Laravel after operator approves
# ════════════════════════════════════════════════════════════════
def call_scada_action(action: str, machine_id: int, reason: str):
    """Send an action command to the SCADA Laravel backend."""
    try:
        res = req.post(
            f"{MACHINES_SYSTEM}/api/scada/action",
            json={
                "action":     action,
                "machine_id": machine_id,
                "reason":     reason
            },
            timeout=5
        )
        print(f"[SCADA ACTION] {action} → machine {machine_id} | HTTP {res.status_code}")
    except req.exceptions.ConnectionError:
        print(f"[SCADA ACTION] Cannot reach Laravel at {MACHINES_SYSTEM}")
    except Exception as e:
        print(f"[SCADA ACTION ERROR] {e}")


def decide_scada_action(decision: dict):
    """
    Determine which SCADA action to take based on the AI decision.

    Logic:
      critical severity           → shutdown_machine  (immediate danger)
      cyber attack indicators     → isolate_machine   (tamper / injection)
      high / medium severity      → alert_maintenance (needs inspection)
    """
    machine_id = decision.get("extra", {}).get("machine_id")
    if not machine_id:
        print("[SCADA ACTION] No machine_id in decision extra — skipping")
        return

    severity   = (decision.get("severity")   or "").lower()
    threat     = (decision.get("threat_type") or "").lower()
    reason     = decision.get("decision", "SOC approved action")

    # Cyber attack keywords → isolate first
    cyber_keywords = ["tamper", "inject", "spoof", "replay", "manipulat", "attack", "unauthoriz"]
    is_cyber = any(kw in threat for kw in cyber_keywords)

    if is_cyber:
        call_scada_action("isolate_machine", machine_id, reason)

    elif severity == "critical":
        call_scada_action("shutdown_machine", machine_id, reason)

    elif severity in ("high", "medium"):
        call_scada_action("alert_maintenance", machine_id, reason)

    else:
        # low / info — just log, no physical action
        print(f"[SCADA ACTION] severity={severity} — no physical action taken")


# ════════════════════════════════════════════════════════════════
#  WEBHOOK — SOC notifies Laravel of resolved decision
#  Laravel stores it in DB so the SCADA Vue page can display it
# ════════════════════════════════════════════════════════════════
def notify_laravel(decision: dict):
    """Forward the resolved decision to Laravel for persistence."""
    try:
        req.post(
            f"{MACHINES_SYSTEM}/api/soc/webhook",
            json=decision,
            timeout=5
        )
        print(f"[WEBHOOK] Decision {decision['decision_id'][:8]} sent to Laravel")
    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")


# ── Static files ──────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/css/<path:f>")
def css(f):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), f)

@app.route("/js/<path:f>")
def js(f):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), f)

# ════════════════════════════════════════════════════════════════
#  ROUTE 1  POST /api/ingest
# ════════════════════════════════════════════════════════════════
@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"status": "error", "message": "JSON body required"}), 400
    log_id = str(uuid.uuid4())
    entry = {
        "log_id":   log_id,
        "received": _now(),
        "source":   payload.get("source", "external"),
        "severity": payload.get("severity", "info"),
        "message":  payload.get("message", "(no message)"),
        "raw":      payload,
    }
    with _lock:
        ingest_log_store.appendleft(entry)
        pending_log_queue.appendleft(entry)
    socketio.emit("ingest_log", entry)
    print(f"[INGEST] [{entry['severity'].upper()}] {entry['source']}: {entry['message']}")
    return jsonify({"status": "ok", "log_id": log_id}), 201

# ════════════════════════════════════════════════════════════════
#  ROUTE 2  GET /api/agent/pending-logs
# ════════════════════════════════════════════════════════════════
@app.route("/api/agent/pending-logs")
def api_pending_logs():
    limit = int(request.args.get("limit", 50))
    with _lock:
        logs = list(pending_log_queue)[:limit]
        pending_log_queue.clear()
    return jsonify({"status": "ok", "count": len(logs), "logs": logs})

# ════════════════════════════════════════════════════════════════
#  ROUTE 3  POST /api/agent/decision
# ════════════════════════════════════════════════════════════════
@app.route("/api/agent/decision", methods=["POST"])
def api_agent_decision():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"status": "error", "message": "JSON body required"}), 400
    decision_id = payload.get("decision_id") or str(uuid.uuid4())
    decision = {
        "decision_id":   decision_id,
        "log_id":        payload.get("log_id", ""),
        "threat_type":   payload.get("threat_type", "Unknown Threat"),
        "severity":      payload.get("severity", "high"),
        "confidence":    payload.get("confidence", 0),
        "decision":      payload.get("decision", "(no decision provided)"),
        "reasoning":     payload.get("reasoning", ""),
        "extra":         payload.get("extra", {}),
        "status":        "pending",
        "created":       _now(),
        "resolved":      None,
        "operator_note": "",
    }
    with _lock:
        pending_decisions[decision_id] = decision
    socketio.emit("ai_decision", decision)
    print(f"[DECISION] {decision_id} | {decision['threat_type']} | {decision['severity'].upper()}")
    return jsonify({"status": "ok", "decision_id": decision_id}), 201

# ════════════════════════════════════════════════════════════════
#  ROUTE 4  POST /api/decision/<id>/resolve
# ════════════════════════════════════════════════════════════════
@app.route("/api/decision/<decision_id>/resolve", methods=["POST"])
def api_resolve(decision_id):
    payload = request.get_json(force=True, silent=True) or {}
    action  = payload.get("action", "").lower()
    if action not in ("approved", "rejected"):
        return jsonify({"status": "error", "message": "action must be 'approved' or 'rejected'"}), 400
    with _lock:
        decision = pending_decisions.pop(decision_id, None)
    if not decision:
        return jsonify({"status": "error", "message": "Not found or already resolved"}), 404

    decision["status"]        = action
    decision["resolved"]      = _now()
    decision["operator_note"] = payload.get("operator_note", "")

    with _lock:
        decision_history.appendleft(decision)

    socketio.emit("decision_resolved", decision)
    print(f"[RESOLVED] {decision_id} → {action.upper()}")

    # ── ACTION HOOK ──────────────────────────────────────────
    if action == "approved":
        # 1. Execute physical SCADA action (shutdown / isolate / alert)
        threading.Thread(
            target=decide_scada_action,
            args=(decision,),
            daemon=True
        ).start()

        # 2. Notify Laravel to store decision in DB
        threading.Thread(
            target=notify_laravel,
            args=(decision,),
            daemon=True
        ).start()

    elif action == "rejected":
        # Still notify Laravel so SCADA page shows rejected decisions too
        threading.Thread(
            target=notify_laravel,
            args=(decision,),
            daemon=True
        ).start()
    # ─────────────────────────────────────────────────────────

    return jsonify({"status": "ok", "decision": decision})

# ════════════════════════════════════════════════════════════════
#  ROUTE 5  GET /api/decisions/pending
#  ROUTE 6  GET /api/decisions/history?limit=50
#  ROUTE 7  GET /api/ingest/logs?limit=100
# ════════════════════════════════════════════════════════════════
@app.route("/api/decisions/pending")
def api_pending():
    with _lock:
        return jsonify({"status": "ok", "decisions": list(pending_decisions.values())})

@app.route("/api/decisions/history")
def api_history():
    limit = int(request.args.get("limit", 50))
    with _lock:
        return jsonify({"status": "ok", "decisions": list(decision_history)[:limit]})

@app.route("/api/ingest/logs")
def api_ingest_logs():
    limit = int(request.args.get("limit", 100))
    with _lock:
        return jsonify({"status": "ok", "logs": list(ingest_log_store)[:limit]})

# ── Socket.IO ─────────────────────────────────────────────────
@socketio.on("connect")
def on_connect():
    print("[SOC] Client connected")
    with _lock:
        for d in pending_decisions.values():
            socketio.emit("ai_decision", d)

@socketio.on("disconnect")
def on_disconnect():
    print("[SOC] Client disconnected")

# ── Start ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  SOC — AI Agent Bridge")
    print("=" * 55)
    print(f"  Laravel URL : {MACHINES_SYSTEM}")
    print("  POST /api/ingest               Send logs")
    print("  GET  /api/agent/pending-logs   AI agent polls")
    print("  POST /api/agent/decision       AI posts decision")
    print("  POST /api/decision/<id>/resolve Operator resolves")
    print("  http://localhost:5000          Dashboard")
    print("=" * 55)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)