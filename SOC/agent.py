
import os
from dotenv import load_dotenv
import json
import requests
import sys
import uuid
import time
from datetime import datetime, timezone
from openai import OpenAI

load_dotenv()

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════
SOC_BASE_URL   = os.getenv("SOC_BASE_URL", "http://localhost:5000")

OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
MODEL           = os.getenv("MODEL", "deepseek/deepseek-chat")

MAX_LOGS_BATCH = int(os.getenv("MAX_LOGS_BATCH", "20"))
POLL_INTERVAL  = int(os.getenv("POLL_INTERVAL", "30"))

client = OpenAI(

    api_key=OPENAI_API_KEY,

    base_url=OPENAI_BASE_URL,

    timeout=30.0,

    max_retries=1

)


# ── Terminal colors ───────────────────────────────────────────
R   = "\033[91m"
G   = "\033[92m"
Y   = "\033[93m"
C   = "\033[96m"
W   = "\033[97m"
DIM = "\033[2m"
B   = "\033[1m"
NC  = "\033[0m"


def now():
    return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")


def log(msg, color=W):
    print(f"{DIM}[{now()}]{NC} {color}{msg}{NC}")


def err(msg):
    print(f"{DIM}[{now()}]{NC} {R}ERROR — {msg}{NC}")


def banner():
    print(f"""
{C}{B}╔══════════════════════════════════════════════════════╗
║          SOC AI Agent — Cloud LLM Mode               ║
╚══════════════════════════════════════════════════════╝{NC}
  SOC endpoint : {W}{SOC_BASE_URL}{NC}
  Model        : {W}{MODEL}{NC}
  Provider     : {W}{OPENAI_BASE_URL}{NC}
""")


# ══════════════════════════════════════════════════════════════
# SOC COMMUNICATION
# ══════════════════════════════════════════════════════════════

def fetch_pending_logs():
    try:
        r = requests.get(
            f"{SOC_BASE_URL}/api/agent/pending-logs",
            params={"limit": MAX_LOGS_BATCH},
            timeout=10
        )
        return r.json().get("logs", [])
    except Exception as e:
        err(f"fetch_pending_logs: {e}")
        return []


def post_decision(decision: dict):
    try:
        r = requests.post(
            f"{SOC_BASE_URL}/api/agent/decision",
            json=decision,
            timeout=10
        )
        data = r.json()
        if data.get("status") == "ok":
            log(f"✓ Decision sent → {data['decision_id']}", G)
        else:
            err(f"SOC rejected decision: {data}")
    except Exception as e:
        err(f"post_decision: {e}")


# ══════════════════════════════════════════════════════════════
# CLOUD LLM CALL
# ══════════════════════════════════════════════════════════════

def ask_llm(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a cybersecurity SOC analyst working on SCADA/ICS systems."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=512
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        err(f"ask_llm: {e}")
        return ""


# ══════════════════════════════════════════════════════════════
# SYSTEM PROMPT — SCADA-aware
# ══════════════════════════════════════════════════════════════

SYSTEM_CONTEXT = """You are a cybersecurity analyst AI working inside a Security Operations Center (SOC).
You specialize in SCADA / Industrial Control System (ICS) security.
Your job is to analyze sensor anomaly logs from industrial machines and decide:
  1. Is this a mechanical/electrical FAULT or a CYBER ATTACK?
  2. What action should be taken?

Rules:
- Output ONLY valid JSON — no markdown, no backticks, no explanation outside the JSON.
- confidence is a number from 0 to 100.
- severity must be exactly one of: critical, high, medium, low, info
- decision must be a single clear recommended action (one sentence).
- reasoning must explain WHY in 1-3 sentences.
- threat_type must clearly indicate FAULT vs ATTACK, e.g.:
    "High Pressure Mechanical Fault", "Sensor Spoofing / Cyber Tampering",
    "Vibration Anomaly - Possible Bearing Fault", "Unauthorized Data Injection"
- If you suspect a cyber attack, the threat_type MUST include one of these words:
    tamper, inject, spoof, replay, manipulat, attack, unauthoriz
- extra must include any parsed SCADA fields.
"""

JSON_SCHEMA = """{
  "threat_type":  "<string — e.g. High Pressure Fault | Cyber Tampering | Sensor Spoofing>",
  "severity":     "<critical|high|medium|low|info>",
  "confidence":   <0-100>,
  "decision":     "<one clear recommended action>",
  "reasoning":    "<1-3 sentences explaining why>",
  "extra": {
    "root_cause":          "<mechanical_fault|cyber_attack|unknown>",
    "false_positive_risk": "<low|medium|high>"
  }
}"""


def build_prompt(log_entry: dict) -> str:
    raw = log_entry.get("raw", {})
    raw_inner = raw.get("raw", raw)
    raw_clean = {k: v for k, v in raw_inner.items()
                 if k not in ("source", "severity", "message")}

    return f"""{SYSTEM_CONTEXT}

--- SCADA LOG TO ANALYZE ---
Log ID      : {log_entry.get('log_id', 'unknown')}
Received    : {log_entry.get('received', 'unknown')}
Source      : {log_entry.get('source', 'unknown')}
Severity    : {log_entry.get('severity', 'unknown')}
Message     : {log_entry.get('message', '(no message)')}
Sensor Data : {json.dumps(raw_clean, indent=2) if raw_clean else '(none)'}
--- END LOG ---

Analyze and respond with ONLY this JSON:
{JSON_SCHEMA}
"""


# ══════════════════════════════════════════════════════════════
# JSON PARSER
# ══════════════════════════════════════════════════════════════

def parse_json_response(text: str):
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def validate(data: dict) -> dict:
    valid_severities = {"critical", "high", "medium", "low", "info"}
    severity = str(data.get("severity", "medium")).lower().strip()
    if severity not in valid_severities:
        severity = "medium"
    confidence = max(0, min(100, int(data.get("confidence", 50))))
    extra = data.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}
    return {
        "threat_type": str(data.get("threat_type", "Unknown Threat")).strip(),
        "severity":    severity,
        "confidence":  confidence,
        "decision":    str(data.get("decision", "Investigate and monitor")).strip(),
        "reasoning":   str(data.get("reasoning", "")).strip(),
        "extra":       extra,
    }


# ══════════════════════════════════════════════════════════════
# CORE PIPELINE
# ══════════════════════════════════════════════════════════════

def analyze_log(log_entry):
    log_id = log_entry.get("log_id", "?")
    msg    = log_entry.get("message", "(no message)")[:80]
    log(f"Analyzing [{log_id[:8]}]  {msg}...", C)

    raw_response = ask_llm(build_prompt(log_entry))
    if not raw_response:
        err(f"No response from LLM for log {log_id[:8]}")
        return False

    parsed = parse_json_response(raw_response)
    if not parsed:
        err(f"Failed to parse LLM response for log {log_id[:8]}")
        print(f"{DIM}Raw response: {raw_response[:200]}{NC}")
        return False

    decision = validate(parsed)
    decision["decision_id"] = str(uuid.uuid4())
    decision["log_id"]      = log_id

    # ── SCADA enrichment — REQUIRED for app.py's decide_scada_action() ──
    # decide_scada_action() reads decision["extra"]["machine_id"]; without
    # this block every approved decision is silently skipped (no machine_id).
    raw       = log_entry.get("raw", {})
    raw_inner = raw.get("raw", raw)
    decision["extra"] = {
        **decision.get("extra", {}),
        "machine_id":   raw_inner.get("machine_id"),
        "machine_name": raw_inner.get("machine_name"),
        "sensor_name":  raw_inner.get("sensor_name"),
        "sensor_type":  raw_inner.get("sensor_type"),
        "value":        raw_inner.get("value"),
    }

    sev_color = {
        "critical": R, "high": Y, "medium": Y, "low": G, "info": C
    }.get(decision["severity"], W)

    print(f"""
{B}--- DECISION ---{NC}
Threat   : {sev_color}{decision['threat_type']}{NC}
Severity : {sev_color}{decision['severity'].upper()}{NC}  ({decision['confidence']}% confidence)
Decision : {decision['decision']}
Reason   : {DIM}{decision['reasoning']}{NC}
Machine  : {DIM}{decision['extra'].get('machine_name', '—')} — {decision['extra'].get('sensor_name', '—')}{NC}
""")

    post_decision(decision)
    return True


# ══════════════════════════════════════════════════════════════
# RUN LOOP
# ══════════════════════════════════════════════════════════════

def run():
    logs = fetch_pending_logs()

    if not logs:
        log("No logs", Y)
        return

    log(f"Found {len(logs)} log(s) to analyze.", W)
    for log_entry in logs:
        analyze_log(log_entry)


def main():
    banner()

    if not OPENAI_API_KEY:
        err("OPENAI_API_KEY is not set — add it to your .env file")
        sys.exit(1)

    log("Agent started (cloud mode)", G)

    while True:
        try:
            run()
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            err(str(e))
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()