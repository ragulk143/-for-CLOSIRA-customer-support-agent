"""
Closira AI Customer Support Workflow
=====================================
A multi-stage AI agent for Bloom Aesthetics Clinic built with Groq API (free tier).
 
Stages:
  1. FAQ Answering        — Grounded SOP responses only
  2. Lead Qualification   — Structured questions + collection
  3. Escalation Detection — Sentiment, confidence, out-of-scope
  4. Conversation Summary — Structured end-of-session report
 
Author: Built for Breakout / Closira internship assignment
"""
 
import json
import re
import os
import sys
from datetime import datetime
from groq import Groq

# ──────────────────────────────────────────────
# CONFIG — paste your Groq key here
# ──────────────────────────────────────────────
 
GROQ_API_KEY = "Replace with your actual Groq API key"  # Get from console.groq.com/keys
SOP_FILE = "sop_data.json"
LOG_FILE = "session_log.json"

client = Groq(api_key=GROQ_API_KEY)
 
# ──────────────────────────────────────────────
# LOAD SOP
# ──────────────────────────────────────────────
 
def load_sop(path: str = SOP_FILE) -> str:
    with open(path, "r") as f:
        data = json.load(f)
    return json.dumps(data, indent=2)
 
SOP_CONTENT = load_sop()
 
# ──────────────────────────────────────────────
# SYSTEM PROMPTS
# ──────────────────────────────────────────────
 
SYSTEM_PROMPT_MAIN = f"""
You are Bloom, the AI customer support assistant for Bloom Aesthetics Clinic.
Your role is to handle inbound customer enquiries with warmth, professionalism, and precision.
 
════════════════════════════════════════
PERSONA & TONE
════════════════════════════════════════
- Warm, reassuring, and professional — like a trusted front-desk receptionist at a premium clinic.
- Use natural, human language. Avoid robotic phrasing.
- Keep responses concise: 2–4 sentences unless the customer asks for detail.
- Always address the customer's need first, then offer next steps.
 
════════════════════════════════════════
SOP — YOUR ONLY SOURCE OF TRUTH
════════════════════════════════════════
You must ONLY answer using the information in the SOP below.
If a customer asks something NOT covered in the SOP, do NOT guess or infer.
Instead, acknowledge the gap honestly and escalate.
 
SOP DATA:
{SOP_CONTENT}
 
════════════════════════════════════════
RESPONSE FORMAT
════════════════════════════════════════
CRITICAL: You must respond with ONLY a valid JSON object. No extra text before or after.
 
{{
  "message": "<your reply to the customer>",
  "stage": "<current stage: faq | qualification | escalation | summary>",
  "escalate": <true or false>,
  "escalation_reason": "<reason if escalate is true, else null>",
  "confidence": "<high | medium | low>",
  "qualification_data": {{
    "business_type": "<collected or null>",
    "team_size": "<collected or null>",
    "current_tools": "<collected or null>"
  }},
  "internal_note": "<brief internal reasoning — not shown to customer>"
}}
 
════════════════════════════════════════
ESCALATION RULES (set escalate: true if ANY apply)
════════════════════════════════════════
1. Customer asks a medical question (medications, allergies, contraindications, adverse reactions)
2. Customer is expressing frustration, anger, or making a complaint
3. Customer asks to negotiate pricing or requests a discount
4. You cannot answer a question from the SOP (out-of-scope)
5. Customer explicitly asks for a human agent
6. You have failed to answer 2+ questions in a row (confidence: low twice)
7. Post-treatment concerns or any safety-related concern
 
When escalating, set escalation_reason to a clear specific reason.
Example: "Medical question: customer asked about allergy contraindications"
 
════════════════════════════════════════
LEAD QUALIFICATION
════════════════════════════════════════
After successfully answering 1–2 FAQ questions, naturally transition to qualify the lead.
Ask ONE qualification question at a time (do not list all at once). Collect:
  1. What brings them in / their primary interest
  2. Whether they have had aesthetic treatments before
  3. Their preferred way to be contacted / book
 
Store answers in qualification_data. Once all 3 are collected, offer to book a free consultation.
 
════════════════════════════════════════
HALLUCINATION PREVENTION
════════════════════════════════════════
- NEVER invent prices, services, staff names, or policies not in the SOP.
- If you are uncertain, set confidence to "low" and escalate.
- Do not infer or extrapolate beyond what is explicitly stated.
- If the SOP is silent on a topic, say so and offer to connect the customer with the team.
"""
 
SYSTEM_PROMPT_SUMMARY = f"""
You are generating an end-of-session summary for the Bloom Aesthetics Clinic support team.
 
SOP DATA:
{SOP_CONTENT}
 
CRITICAL: Respond with ONLY a valid JSON object, no extra text.
 
Produce a structured JSON summary in this exact format:
{{
  "session_id": "<provided>",
  "timestamp": "<provided>",
  "customer_intent": "<1-2 sentence summary of what the customer wanted>",
  "key_details_collected": {{
    "services_enquired": ["<list>"],
    "qualification_data": {{
      "primary_interest": "<or null>",
      "prior_treatments": "<or null>",
      "preferred_contact": "<or null>"
    }},
    "escalated": false,
    "escalation_reason": null
  }},
  "sop_gaps": ["<questions the AI could not answer from SOP>"],
  "recommended_next_action": "<e.g. Book free consultation, Human follow-up required>",
  "conversation_quality": "<good | needs_review>",
  "notes": "<any other relevant detail for the team>"
}}
"""
 
# ──────────────────────────────────────────────
# CORE AI CALL (GROQ)
# ──────────────────────────────────────────────
 
def call_gemini(messages: list, system: str = SYSTEM_PROMPT_MAIN) -> dict:
    """Call Groq API and parse structured JSON response."""
    
    # Convert messages to Groq format
    groq_messages = [{"role": "system", "content": system}]
    for m in messages:
        groq_messages.append({
            "role": m["role"] if m["role"] == "user" else "assistant",
            "content": m["content"]
        })
    
    try:
        response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",  # ← CHANGED (was llama-3.1-70b-versatile)
    messages=groq_messages,
    temperature=0.7,
    max_tokens=1000
)

        
        raw = response.choices[0].message.content.strip()
        
        # Strip markdown code fences if wrapped
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: extract first JSON object found in text
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
            # Last resort: return error structure so session doesn't crash
            print(f"\n  [WARN] Could not parse JSON response. Raw output:\n{raw[:300]}\n")
            return {
                "message": "I'm sorry, I had a technical issue. Could you repeat that?",
                "stage": "faq",
                "escalate": False,
                "escalation_reason": None,
                "confidence": "low",
                "qualification_data": {"business_type": None, "team_size": None, "current_tools": None},
                "internal_note": "JSON parse failure"
            }
    except Exception as e:
        print(f"\n  [ERROR] Groq API call failed: {e}\n")
        return {
            "message": "I'm experiencing technical difficulties. Please try again.",
            "stage": "faq",
            "escalate": True,
            "escalation_reason": f"API Error: {str(e)}",
            "confidence": "low",
            "qualification_data": {"business_type": None, "team_size": None, "current_tools": None},
            "internal_note": f"API call exception: {str(e)}"
        }
 
# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────
 
class Session:
    def __init__(self):
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.messages = []
        self.escalated = False
        self.escalation_reason = None
        self.qualification_data = {
            "business_type": None,
            "team_size": None,
            "current_tools": None
        }
        self.sop_gaps = []
        self.low_confidence_streak = 0
        self.turn_count = 0
        self.transcript = []
 
    def add_turn(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
 
    def log(self, role: str, text: str):
        self.transcript.append({
            "turn": self.turn_count,
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
 
# ──────────────────────────────────────────────
# STAGE HANDLERS
# ──────────────────────────────────────────────
 
def handle_turn(session: Session, user_input: str) -> dict:
    """Process one customer message through the full workflow."""
    session.turn_count += 1
    session.log("customer", user_input)
    session.add_turn("user", user_input)
 
    result = call_gemini(session.messages)
 
    # Update qualification data with anything newly collected
    if result.get("qualification_data"):
        for key, val in result["qualification_data"].items():
            if val and not session.qualification_data.get(key):
                session.qualification_data[key] = val
 
    # Track confidence and SOP gaps
    if result.get("confidence") == "low":
        session.low_confidence_streak += 1
        note = result.get("internal_note", "").lower()
        if "not in sop" in note or "out of scope" in note or "cannot answer" in note:
            gap = user_input[:120]
            if gap not in session.sop_gaps:
                session.sop_gaps.append(gap)
    else:
        session.low_confidence_streak = 0
 
    # Python-layer escalation fallback (don't rely solely on the model)
    if session.low_confidence_streak >= 2 and not result.get("escalate"):
        result["escalate"] = True
        result["escalation_reason"] = "Low confidence on 2+ consecutive turns — routing to human agent"
 
    # Lock in escalation state and log it
    if result.get("escalate") and not session.escalated:
        session.escalated = True
        session.escalation_reason = result.get("escalation_reason")
        log_escalation(session)
 
    session.add_turn("assistant", json.dumps(result))
    session.log("bloom", result.get("message", ""))
 
    return result
 
 
def generate_summary(session: Session) -> dict:
    """Stage 4: Generate structured end-of-session summary."""
    conversation_text = "\n".join(
        f"{t['role'].upper()}: {t['text']}" for t in session.transcript
    )
 
    summary_prompt = f"""
Session ID: {session.id}
Timestamp: {datetime.now().isoformat()}
 
Full Conversation:
{conversation_text}
 
SOP Gaps Detected: {json.dumps(session.sop_gaps)}
Qualification Data Collected: {json.dumps(session.qualification_data)}
Escalated: {session.escalated}
Escalation Reason: {session.escalation_reason}
 
Generate the structured session summary now.
"""
 
    try:
        response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",  # ← CHANGED
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT_SUMMARY},
        {"role": "user", "content": summary_prompt}
    ],
    temperature=0.5,
    max_tokens=1000
)
        
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        
        try:
            return json.loads(raw)
        except Exception:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
            return {"error": "Could not parse summary", "raw": raw[:500]}
    except Exception as e:
        return {"error": f"Summary generation failed: {str(e)}"}
 
# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
 
def log_escalation(session: Session):
    """Log escalation event to session_log.json."""
    entry = {
        "session_id": session.id,
        "timestamp": datetime.now().isoformat(),
        "turn": session.turn_count,
        "reason": session.escalation_reason,
        "transcript_so_far": session.transcript
    }
 
    log_data = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                log_data = json.load(f)
            except Exception:
                log_data = []
 
    log_data.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2)
 
    print(f"\n  ⚠  ESCALATION LOGGED: {session.escalation_reason}")
 
 
def save_session(session: Session, summary: dict):
    """Save full session data to a JSON file."""
    data = {
        "session_id": session.id,
        "timestamp": datetime.now().isoformat(),
        "transcript": session.transcript,
        "qualification_data": session.qualification_data,
        "escalated": session.escalated,
        "escalation_reason": session.escalation_reason,
        "sop_gaps": session.sop_gaps,
        "summary": summary
    }
 
    fname = f"session_{session.id}.json"
    with open(fname, "w") as f:
        json.dump(data, f, indent=2)
 
    print(f"\n  💾  Session saved to {fname}")
    return fname
 
# ──────────────────────────────────────────────
# CLI DISPLAY HELPERS
# ──────────────────────────────────────────────
 
BANNER = """
╔══════════════════════════════════════════════════════════╗
║         🌸  BLOOM AESTHETICS CLINIC  🌸                  ║
║         Powered by Closira AI — Customer Support         ║
║         Using Groq API (Llama 3.1 70B)                   ║
╚══════════════════════════════════════════════════════════╝
  Type your message and press Enter.
  Commands: /summary  -> generate session summary + exit
            /status   -> show session state
            /quit     -> end session
"""
 
def print_bloom(message: str, stage: str, confidence: str, escalated: bool):
    badge = {
        "faq": "💬 FAQ",
        "qualification": "📋 QUALIFY",
        "escalation": "⚠️  ESCALATE",
        "summary": "📊 SUMMARY"
    }.get(stage, "💬")
 
    conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence, "⚪")
    esc_flag = "  [ESCALATED ⚠️]" if escalated else ""
 
    print(f"\n  {badge} {conf_icon}{esc_flag}")
    print(f"  Bloom: {message}\n")
 
 
def show_status(session: Session):
    print(f"""
  ─── Session Status ───────────────────────
  ID:           {session.id}
  Turns:        {session.turn_count}
  Escalated:    {session.escalated}
  Esc. Reason:  {session.escalation_reason or 'N/A'}
  SOP Gaps:     {len(session.sop_gaps)}
  Qualification:
    Interest:   {session.qualification_data.get('business_type') or 'Not collected'}
    Prior Tx:   {session.qualification_data.get('team_size') or 'Not collected'}
    Contact:    {session.qualification_data.get('current_tools') or 'Not collected'}
  ──────────────────────────────────────────
""")
 
# ──────────────────────────────────────────────
# INTERACTIVE CLI MODE
# ──────────────────────────────────────────────
 
def run_cli():
    print(BANNER)
    session = Session()
 
    # Opening greeting
    print("  Connecting to Bloom AI...\n")
    greeting_result = call_gemini(
        messages=[{"role": "user", "content": "Hi, I'd like some information about your clinic."}]
    )
    session.add_turn("user", "Hi, I'd like some information about your clinic.")
    session.add_turn("assistant", json.dumps(greeting_result))
    session.log("customer", "Hi, I'd like some information about your clinic.")
    session.log("bloom", greeting_result.get("message", ""))
    print_bloom(
        greeting_result.get("message", ""),
        greeting_result.get("stage", "faq"),
        greeting_result.get("confidence", "high"),
        False
    )
 
    while True:
        try:
            user_input = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            user_input = "/quit"
 
        if not user_input:
            continue
 
        if user_input.lower() == "/quit":
            print("\n  Ending session...\n")
            break
 
        if user_input.lower() == "/status":
            show_status(session)
            continue
 
        if user_input.lower() == "/summary":
            print("\n  📊 Generating session summary...\n")
            summary = generate_summary(session)
            print(json.dumps(summary, indent=2))
            save_session(session, summary)
            return
 
        result = handle_turn(session, user_input)
        print_bloom(
            result.get("message", ""),
            result.get("stage", "faq"),
            result.get("confidence", "high"),
            session.escalated
        )
 
    # Auto-generate summary on /quit
    if session.turn_count > 0:
        print("\n  📊 Auto-generating end-of-session summary...\n")
        summary = generate_summary(session)
        print(json.dumps(summary, indent=2))
        save_session(session, summary)
 
# ──────────────────────────────────────────────
# DEMO MODE — all 5 test scenarios headlessly
# ──────────────────────────────────────────────
 
DEMO_SCENARIOS = [
    {
        "name": "in_sop_question",
        "description": "In-SOP question: Customer asks about Botox prices",
        "messages": [
            "Hi, what are your Botox prices?",
            "And how long does Botox last?"
        ]
    },
    {
        "name": "out_of_scope_question",
        "description": "Out-of-scope: Customer asks something not in the SOP",
        "messages": [
            "Do you offer laser hair removal?",
            "What about skin peels?"
        ]
    },
    {
        "name": "escalation_trigger",
        "description": "Escalation: Customer is angry and makes a complaint",
        "messages": [
            "I had a treatment last week and my face is still swollen. I'm really unhappy.",
            "I want to speak to someone NOW — this is unacceptable."
        ]
    },
    {
        "name": "lead_qualification",
        "description": "Lead qualification: AI collects structured answers",
        "messages": [
            "I'm interested in getting fillers. Can you tell me more?",
            "Yes, I've never had any treatment before.",
            "I'd prefer to be contacted via WhatsApp."
        ]
    },
    {
        "name": "conversation_summary",
        "description": "Full conversation ending in structured summary",
        "messages": [
            "What consultations do you offer?",
            "Are consultations really free?",
            "Great, I'd like to book one. I'm free Saturdays.",
            "/summary"
        ]
    }
]
 
 
def run_demo():
    print("\n" + "═" * 60)
    print("  CLOSIRA DEMO MODE — Running all 5 test scenarios")
    print("  Using Groq API (Free Tier)")
    print("═" * 60)
 
    os.makedirs("test_transcripts", exist_ok=True)
 
    for scenario in DEMO_SCENARIOS:
        print(f"\n\n{'─' * 60}")
        print(f"  Scenario: {scenario['description']}")
        print("─" * 60)
 
        session = Session()
        transcript_lines = [
            f"# Test Transcript: {scenario['description']}",
            f"Session ID: {session.id}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            ""
        ]
 
        for msg in scenario["messages"]:
            if msg == "/summary":
                print("\n  [Generating summary...]")
                summary = generate_summary(session)
                summary_text = json.dumps(summary, indent=2)
                print(summary_text)
                transcript_lines.append("**[SESSION SUMMARY GENERATED]**")
                transcript_lines.append(f"```json\n{summary_text}\n```")
                save_session(session, summary)
                break
 
            print(f"\n  Customer: {msg}")
            result = handle_turn(session, msg)
            print_bloom(
                result.get("message", ""),
                result.get("stage", "faq"),
                result.get("confidence", "high"),
                session.escalated
            )
 
            transcript_lines.append(f"**Customer:** {msg}")
            transcript_lines.append("")
            transcript_lines.append(f"**Bloom (AI):** {result.get('message', '')}")
            transcript_lines.append(
                f"*Stage: {result.get('stage')} | "
                f"Confidence: {result.get('confidence')} | "
                f"Escalate: {result.get('escalate')}*"
            )
            if result.get("escalation_reason"):
                transcript_lines.append(f"*Escalation Reason: {result.get('escalation_reason')}*")
            transcript_lines.append("")
            transcript_lines.append("---")
            transcript_lines.append("")
 
        # Save transcript markdown
        fname = f"test_transcripts/{scenario['name']}.md"
        with open(fname, "w") as f:
            f.write("\n".join(transcript_lines))
        print(f"\n  ✅ Transcript saved: {fname}")
 
    print("\n\n" + "═" * 60)
    print("  ✅ All scenarios complete. Check test_transcripts/ folder.")
    print("═" * 60 + "\n")
 
# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────
 
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo()
    else:
        run_cli()