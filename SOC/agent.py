# """
# ╔══════════════════════════════════════════════════════════════╗
# ║  SOC — AI Agent                                              ║
# ║  Model  : llama3.2 (Ollama — fully local, free)             ║
# ║  Mode   : Auto polling                                       ║
# ║                                                              ║
# ║  HOW TO RUN:                                                 ║
# ║    1. Install Ollama  →  https://ollama.com                  ║
# ║    2. ollama pull llama3.2                                   ║
# ║    3. pip install requests                                    ║
# ║    4. python agent.py                                        ║
# ╚══════════════════════════════════════════════════════════════╝
# """
# import os
# from dotenv import load_dotenv
# import json
# import requests
# import sys
# import uuid
# import time
# from datetime import datetime, timezone

# load_dotenv()

# # ══════════════════════════════════════════════════════════════
# #  CONFIG — reads from environment variables or uses defaults
# # ══════════════════════════════════════════════════════════════
# SOC_BASE_URL   = os.getenv("SOC_BASE_URL",    "http://localhost:5000")
# OLLAMA_URL     = os.getenv("OLLAMA_URL",       "http://localhost:11434")
# MODEL          = os.getenv("MODEL",            "llama3.2")
# MAX_LOGS_BATCH = int(os.getenv("MAX_LOGS_BATCH", "20"))
# POLL_INTERVAL  = int(os.getenv("POLL_INTERVAL",  "30"))

# # ── Terminal colors ───────────────────────────────────────────
# R   = "\033[91m"
# G   = "\033[92m"
# Y   = "\033[93m"
# C   = "\033[96m"
# W   = "\033[97m"
# DIM = "\033[2m"
# B   = "\033[1m"
# NC  = "\033[0m"

# def now():
#     return datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

# def log(msg, color=W):
#     print(f"{DIM}[{now()}]{NC} {color}{msg}{NC}")

# def err(msg):
#     print(f"{DIM}[{now()}]{NC} {R}ERROR — {msg}{NC}")

# def banner():
#     print(f"""
# {C}{B}╔══════════════════════════════════════════════════════╗
# ║          SOC  AI Agent  —  llama3.2 (Ollama)         ║
# ╚══════════════════════════════════════════════════════╝{NC}
#   SOC endpoint  : {W}{SOC_BASE_URL}{NC}
#   Ollama model  : {W}{MODEL}{NC}
#   Poll interval : {W}{POLL_INTERVAL}s{NC}
#   Batch max     : {W}{MAX_LOGS_BATCH} logs{NC}
# """)

# # ══════════════════════════════════════════════════════════════
# #  SOC COMMUNICATION
# # ══════════════════════════════════════════════════════════════

# def fetch_pending_logs():
#     try:
#         r = requests.get(
#             f"{SOC_BASE_URL}/api/agent/pending-logs",
#             params={"limit": MAX_LOGS_BATCH},
#             timeout=10
#         )
#         return r.json().get("logs", [])
#     except requests.exceptions.ConnectionError:
#         err(f"Cannot reach SOC at {SOC_BASE_URL} — is it running?")
#         return []
#     except Exception as e:
#         err(f"fetch_pending_logs: {e}")
#         return []


# def post_decision(decision: dict):
#     try:
#         r    = requests.post(
#             f"{SOC_BASE_URL}/api/agent/decision",
#             json=decision,
#             timeout=10
#         )
#         data = r.json()
#         if data.get("status") == "ok":
#             log(f"  ✓ Decision sent  →  {data['decision_id']}", G)
#         else:
#             err(f"SOC rejected decision: {data}")
#     except requests.exceptions.ConnectionError:
#         err(f"Cannot reach SOC at {SOC_BASE_URL}")
#     except Exception as e:
#         err(f"post_decision: {e}")

# # ══════════════════════════════════════════════════════════════
# #  OLLAMA COMMUNICATION
# # ══════════════════════════════════════════════════════════════

# def check_ollama():
#     try:
#         r      = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
#         models = [m["name"].split(":")[0] for m in r.json().get("models", [])]
#         if MODEL not in models:
#             err(f'Model "{MODEL}" not found. Run:  ollama pull {MODEL}')
#             return False
#         log(f"Ollama ready — model {MODEL} loaded", G)
#         return True
#     except requests.exceptions.ConnectionError:
#         err(f"Ollama not running at {OLLAMA_URL} — run:  ollama serve")
#         return False
#     except Exception as e:
#         err(f"check_ollama: {e}")
#         return False


# def ask_ollama(prompt: str) -> str:
#     try:
#         r = requests.post(
#             f"{OLLAMA_URL}/api/generate",
#             json={
#                 "model":   MODEL,
#                 "prompt":  prompt,
#                 "stream":  False,
#                 "options": {
#                     "temperature": 0.1,
#                     "num_predict": 512,
#                 }
#             },
#             timeout=120
#         )
#         return r.json().get("response", "").strip()
#     except requests.exceptions.Timeout:
#         err("Ollama timed out — model may be loading, try again")
#         return ""
#     except Exception as e:
#         err(f"ask_ollama: {e}")
#         return ""

# # ══════════════════════════════════════════════════════════════
# #  PROMPT
# # ══════════════════════════════════════════════════════════════

# SYSTEM_CONTEXT = """You are a cybersecurity analyst AI working inside a Security Operations Center (SOC).
# You specialize in SCADA / Industrial Control System (ICS) security.
# Your job is to analyze sensor anomaly logs from industrial machines and decide:
#   1. Is this a mechanical/electrical FAULT or a CYBER ATTACK?
#   2. What action should be taken?

# Rules:
# - Output ONLY valid JSON — no markdown, no backticks, no explanation outside the JSON.
# - confidence is a number from 0 to 100.
# - severity must be exactly one of: critical, high, medium, low, info
# - decision must be a single clear recommended action (one sentence).
# - reasoning must explain WHY in 1-3 sentences.
# - extra must include any parsed SCADA fields.
# """

# JSON_SCHEMA = """{
#   "threat_type":  "<string — e.g. High Pressure Fault | Cyber Tampering | Sensor Spoofing>",
#   "severity":     "<critical|high|medium|low|info>",
#   "confidence":   <0-100>,
#   "decision":     "<one clear recommended action>",
#   "reasoning":    "<1-3 sentences explaining why>",
#   "extra": {
#     "machine_id":          <number or null>,
#     "machine_name":        "<string or null>",
#     "sensor_name":         "<string or null>",
#     "sensor_type":         "<string or null>",
#     "value":               <number or null>,
#     "root_cause":          "<mechanical_fault|cyber_attack|unknown>",
#     "false_positive_risk": "<low|medium|high>"
#   }
# }"""


# def build_prompt(log_entry: dict) -> str:
#     raw       = log_entry.get("raw", {})
#     raw_inner = raw.get("raw", raw)
#     raw_clean = {k: v for k, v in raw_inner.items()
#                  if k not in ("source", "severity", "message")}

#     return f"""{SYSTEM_CONTEXT}

# --- SCADA LOG TO ANALYZE ---
# Log ID      : {log_entry.get('log_id', 'unknown')}
# Received    : {log_entry.get('received', 'unknown')}
# Source      : {log_entry.get('source', 'unknown')}
# Severity    : {log_entry.get('severity', 'unknown')}
# Message     : {log_entry.get('message', '(no message)')}
# Sensor Data : {json.dumps(raw_clean, indent=2) if raw_clean else '(none)'}
# --- END LOG ---

# Analyze and respond with ONLY this JSON:
# {JSON_SCHEMA}
# """

# # ══════════════════════════════════════════════════════════════
# #  JSON PARSER
# # ══════════════════════════════════════════════════════════════

# def parse_json_response(raw_text: str) -> dict | None:
#     if not raw_text:
#         return None
#     text = raw_text.strip()
#     if text.startswith("```"):
#         lines = text.split("\n")
#         text  = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
#     start = text.find("{")
#     end   = text.rfind("}")
#     if start == -1 or end == -1:
#         return None
#     try:
#         return json.loads(text[start:end+1])
#     except json.JSONDecodeError:
#         return None


# def validate_decision(data: dict) -> dict:
#     valid_severities = {"critical", "high", "medium", "low", "info"}
#     severity = str(data.get("severity", "medium")).lower().strip()
#     if severity not in valid_severities:
#         severity = "medium"
#     confidence = max(0, min(100, int(data.get("confidence", 50))))
#     extra = data.get("extra", {})
#     if not isinstance(extra, dict):
#         extra = {}
#     return {
#         "threat_type": str(data.get("threat_type", "Unknown Threat")).strip(),
#         "severity":    severity,
#         "confidence":  confidence,
#         "decision":    str(data.get("decision", "Investigate and monitor")).strip(),
#         "reasoning":   str(data.get("reasoning", "No reasoning provided")).strip(),
#         "extra":       extra,
#     }

# # ══════════════════════════════════════════════════════════════
# #  CORE PIPELINE
# # ══════════════════════════════════════════════════════════════

# def analyze_log(log_entry: dict) -> bool:
#     log_id = log_entry.get("log_id", "?")
#     msg    = log_entry.get("message", "(no message)")[:80]
#     log(f"  Analyzing  [{log_id[:8]}]  {msg}...", C)

#     raw_response = ask_ollama(build_prompt(log_entry))
#     if not raw_response:
#         err(f"  No response from Ollama for log {log_id[:8]}")
#         return False

#     parsed = parse_json_response(raw_response)
#     if not parsed:
#         err(f"  Could not parse JSON for log {log_id[:8]}")
#         print(f"  {DIM}Raw response: {raw_response[:200]}{NC}")
#         return False

#     decision_data = validate_decision(parsed)
#     decision_data["decision_id"] = str(uuid.uuid4())
#     decision_data["log_id"]      = log_id

#     # Enrich extra with SCADA context from raw
#     raw       = log_entry.get("raw", {})
#     raw_inner = raw.get("raw", raw)
#     decision_data["extra"] = {
#         **decision_data.get("extra", {}),
#         "machine_id":   raw_inner.get("machine_id"),
#         "machine_name": raw_inner.get("machine_name"),
#         "sensor_name":  raw_inner.get("sensor_name"),
#         "sensor_type":  raw_inner.get("sensor_type"),
#         "value":        raw_inner.get("value"),
#     }

#     sev_color = {
#         "critical": R, "high": Y, "medium": Y, "low": G, "info": C
#     }.get(decision_data["severity"], W)

#     print(f"""
#   {B}┌─ Decision ────────────────────────────────────────────┐{NC}
#   {B}│{NC} Threat    : {sev_color}{decision_data['threat_type']}{NC}
#   {B}│{NC} Severity  : {sev_color}{decision_data['severity'].upper()}{NC}  ({decision_data['confidence']}% confidence)
#   {B}│{NC} Decision  : {W}{decision_data['decision']}{NC}
#   {B}│{NC} Reasoning : {DIM}{decision_data['reasoning'][:120]}{NC}
#   {B}│{NC} Machine   : {DIM}{decision_data['extra'].get('machine_name','—')} — {decision_data['extra'].get('sensor_name','—')}{NC}
#   {B}└───────────────────────────────────────────────────────┘{NC}""")

#     post_decision(decision_data)
#     return True

# # ══════════════════════════════════════════════════════════════
# #  RUN — process all pending logs
# # ══════════════════════════════════════════════════════════════

# def run():
#     log("Fetching pending logs from SOC...", C)
#     logs = fetch_pending_logs()

#     if not logs:
#         log("No pending logs — queue is empty.", Y)
#         return

#     log(f"Found {len(logs)} log(s) to analyze.", W)
#     print()

#     success = 0
#     for i, log_entry in enumerate(logs, 1):
#         print(f"{DIM}─── Log {i}/{len(logs)} ─────────────────────────────────────────{NC}")
#         if analyze_log(log_entry):
#             success += 1
#         print()

#     log(f"Done — {success}/{len(logs)} decisions sent to SOC.",
#         G if success == len(logs) else Y)

# # ══════════════════════════════════════════════════════════════
# #  MAIN — auto polling
# # ══════════════════════════════════════════════════════════════

# def main():
#     banner()

#     if not check_ollama():
#         print(f"\n  {Y}Fix the issue above, then re-run the agent.{NC}\n")
#         sys.exit(1)

#     print(f"  {G}Agent ready — auto polling every {POLL_INTERVAL}s.{NC}")
#     print(f"  Press {R}Ctrl+C{NC} to stop.\n")

#     while True:
#         try:
#             run()
#             print(f"\n  {DIM}Next check in {POLL_INTERVAL}s...{NC}\n")
#             time.sleep(POLL_INTERVAL)

#         except KeyboardInterrupt:
#             print(f"\n  {Y}Stopped.{NC}\n")
#             break
#         except Exception as e:
#             err(f"Unexpected error: {e}")
#             time.sleep(POLL_INTERVAL)


# if __name__ == "__main__":
#     main()




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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
MODEL          = os.getenv("MODEL", "deepseek/deepseek-chat")

MAX_LOGS_BATCH = int(os.getenv("MAX_LOGS_BATCH", "20"))
POLL_INTERVAL  = int(os.getenv("POLL_INTERVAL", "30"))

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

# ── Terminal colors ───────────────────────────────────────────
R = "\033[91m"
G = "\033[92m"
Y = "\033[93m"
C = "\033[96m"
W = "\033[97m"
DIM = "\033[2m"
B = "\033[1m"
NC = "\033[0m"


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
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════

SYSTEM_CONTEXT = """You are a cybersecurity analyst AI working inside a Security Operations Center (SOC).
You specialize in SCADA / Industrial Control System (ICS) security.

Rules:
- Output ONLY valid JSON.
- No markdown, no explanation.
- severity: critical, high, medium, low, info
- confidence: 0-100
"""


def build_prompt(log_entry: dict) -> str:
    raw = log_entry.get("raw", {})
    raw_inner = raw.get("raw", raw)
    raw_clean = {k: v for k, v in raw_inner.items()
                 if k not in ("source", "severity", "message")}

    return f"""{SYSTEM_CONTEXT}

LOG:
ID: {log_entry.get('log_id')}
Message: {log_entry.get('message')}
Severity: {log_entry.get('severity')}
Data: {json.dumps(raw_clean, indent=2)}

Return ONLY JSON:
"""


# ══════════════════════════════════════════════════════════════
# JSON PARSER
# ══════════════════════════════════════════════════════════════

def parse_json_response(text: str):
    if not text:
        return None
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(text[start:end + 1])
    except:
        return None


def validate(data: dict) -> dict:
    return {
        "threat_type": data.get("threat_type", "Unknown"),
        "severity": data.get("severity", "medium"),
        "confidence": max(0, min(100, int(data.get("confidence", 50)))),
        "decision": data.get("decision", "Investigate"),
        "reasoning": data.get("reasoning", ""),
        "extra": data.get("extra", {})
    }


# ══════════════════════════════════════════════════════════════
# CORE PIPELINE
# ══════════════════════════════════════════════════════════════

def analyze_log(log_entry):
    log_id = log_entry.get("log_id", "?")
    log(f"Analyzing {log_id[:8]}...", C)

    raw = ask_llm(build_prompt(log_entry))
    parsed = parse_json_response(raw)

    if not parsed:
        err("Failed to parse LLM response")
        return False

    decision = validate(parsed)
    decision["decision_id"] = str(uuid.uuid4())
    decision["log_id"] = log_id

    print(f"""
{B}--- DECISION ---{NC}
Threat   : {decision['threat_type']}
Severity : {decision['severity']}
Decision : {decision['decision']}
Reason   : {decision['reasoning']}
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

    for log_entry in logs:
        analyze_log(log_entry)


def main():
    banner()
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
