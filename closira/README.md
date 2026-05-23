# Closira AI Customer Support Workflow
### Built for Bloom Aesthetics Clinic · Breakout Internship Assignment

---

## What This Does

A Python-based, multi-stage AI customer support agent built with the **Groq API** (using `llama-3.3-70b-versatile` — free and fast). It handles real customer conversations end-to-end across four stages:

| Stage | What it does |
|-------|-------------|
| **1 — FAQ Answering** | Answers inbound questions using the clinic's SOP only. Never hallucinates. |
| **2 — Lead Qualification** | Asks structured questions one at a time. Collects interest, prior experience, contact preference. |
| **3 — Escalation Detection** | Detects frustration, out-of-scope questions, medical queries, and low confidence. Logs reason. |
| **4 — Conversation Summary** | Generates a structured JSON summary: intent, gaps, qualification data, next action. |

---

## Project Structure

```
closira/
├── workflow.py              # Main AI orchestration — all four stages
├── sop_data.json            # SOP source of truth for Bloom Aesthetics Clinic
├── prompt_design.md         # Full prompt design rationale and decisions
├── README.md                # This file
├── session_log.json         # Escalation log (auto-created on first escalation)
├── session_<id>.json        # Full session data (auto-created per session)
└── test_transcripts/
    ├── 1_in_sop_question.md
    ├── 2_out_of_scope_question.md
    ├── 3_escalation_trigger.md
    ├── 4_lead_qualification.md
    └── 5_conversation_summary.md
```

---

## Setup

### 1. Get your free Groq API key

Go to **https://console.groq.com**, sign in, and click **"Create API Key"**.
No credit card required — Groq's free tier is generous and very fast.

### 2. Install dependencies

```bash
pip install groq
```

### 3. Add your API key to workflow.py

Open `workflow.py` and paste your key on the config line near the top:

```python
GROQ_API_KEY = "your-key-here"
```

That's it. No environment variables needed.

---

## How to Run

### Interactive Mode (live conversation)

**Mac / Linux:**
```bash
python workflow.py
```

**Windows (PowerShell):**
```powershell
python workflow.py
```

You'll enter a CLI chat with **Bloom**, the AI assistant.

**Available commands during a session:**
- `/summary` — generate end-of-session summary and exit
- `/status` — show current session state (escalation, qualification data, SOP gaps)
- `/quit` — end session (auto-generates summary)

---

### Demo Mode (runs all 5 test scenarios headlessly)

```bash
python workflow.py --demo
```

Runs all five test scenarios automatically, prints output to the console, saves transcripts to `test_transcripts/`, and saves session JSON files. Best way to see all features at once for a video walkthrough.

---

## AI Behaviour — What to Expect

### ✅ In-SOP question
Ask *"What are your Botox prices?"* → AI answers accurately from SOP only, then naturally moves toward qualification.

### ❌ Out-of-scope question
Ask *"Do you offer laser hair removal?"* → AI acknowledges the gap, does not guess, escalates with reason logged.

### ⚠️ Escalation trigger
Express frustration or a complaint → AI detects sentiment, immediately escalates, logs reason and transcript snapshot.

### 📋 Lead qualification
After 1–2 FAQ turns, AI naturally asks qualification questions one at a time and stores answers.

### 📊 Conversation summary
Type `/summary` at any point → structured JSON summary with intent, details, SOP gaps, and recommended next action.

---

## SOP Data

The AI operates exclusively on `sop_data.json`. Current data covers:

- **Business:** Bloom Aesthetics Clinic
- **Hours:** Mon–Sat, 9am–7pm
- **Services:** Botox (from £200), Dermal Fillers (from £250), Free Consultations
- **Booking:** Via WhatsApp or website; 24hr cancellation policy
- **Escalation rules:** Complaints, medical questions, pricing negotiation, >2 unanswered questions

To adapt for a different business, replace or extend `sop_data.json` and update the prompt in `workflow.py`.

---

## Design Decisions & Trade-offs

### Why Groq?
Groq offers a completely free API with no credit card required, and it's significantly faster than most LLM providers due to its custom LPU hardware. `llama-3.3-70b-versatile` has strong instruction-following and reliable JSON output — ideal for a grounded SOP-only agent.

### Why structured JSON output?
Forces the model to separate customer-facing text from internal reasoning. Enables deterministic escalation logic in Python without a second LLM call.

### Why one system prompt for all stages?
Avoids context loss from mid-conversation prompt switching. The model naturally transitions stages based on conversation state.

### Known limitations

| Limitation | Detail |
|------------|--------|
| No persistent memory | Each session is independent. Session JSON can be loaded for continuity. |
| No real human routing | Escalation is logged and flagged, but not routed to a live agent (integration-ready). |
| SOP size | Full SOP is injected into the prompt. Scales well for SMBs. RAG recommended for 50+ services. |
| JSON parsing edge cases | Handled via regex fallback extractor so the session never crashes on a bad response. |

---

## What Makes This Submission Different

Most AI support bots hallucinate confidently or refuse everything. This workflow is designed to **fail informatively**:

1. **SOP gap tracking** — Every unanswerable question is logged. After a week of real conversations, you'd have a prioritised list of SOP gaps to fix.
2. **Python-layer escalation fallback** — Doesn't rely solely on the model to self-escalate. The orchestration layer independently tracks confidence streaks and forces escalation if the threshold is hit.
3. **Named AI persona** — "Bloom" matches the clinic brand, creating coherence and trust.
4. **Actionable summaries** — The `recommended_next_action` field tells the human team exactly what to do, not just what happened.

---

## Dependencies

```
groq>=0.9.0
python>=3.9
```

---

## Author

Built for the Breakout / Closira AI Engineering Internship assignment.
