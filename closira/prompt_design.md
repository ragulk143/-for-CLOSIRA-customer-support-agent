# Prompt Design — Closira AI Workflow
### Bloom Aesthetics Clinic Customer Support Agent

---

## Overview

This document explains the full prompt design rationale for the Closira AI workflow: the system prompt architecture, hallucination prevention strategy, escalation logic, confidence signalling, and tone decisions.

The system is built on **Claude (Anthropic)** and uses a **single structured system prompt** that governs all four workflow stages (FAQ, Qualification, Escalation, Summary), with a separate summary prompt for end-of-session generation.

---

## 1. System Prompt — Full Text

```
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
{ ... injected at runtime ... }

════════════════════════════════════════
RESPONSE FORMAT
════════════════════════════════════════
Every response MUST be a valid JSON object with this exact shape:

{
  "message": "<your reply to the customer>",
  "stage": "<faq | qualification | escalation | summary>",
  "escalate": <true or false>,
  "escalation_reason": "<reason if escalate is true, else null>",
  "confidence": "<high | medium | low>",
  "qualification_data": { ... },
  "internal_note": "<brief internal reasoning>"
}

...
```

*(Full prompt is embedded in `workflow.py` → `SYSTEM_PROMPT_MAIN`)*

---

## 2. Key Design Decisions

### 2.1 Structured JSON Output
**Decision:** The model is required to return a strict JSON schema on every turn.

**Reasoning:**
- Enables the orchestration layer to make deterministic decisions (escalate, stage routing, data collection) without a second LLM call.
- Separates `message` (customer-facing) from `internal_note` (reasoning visible only to the system).
- Allows `qualification_data` to accumulate incrementally across turns without extra state management.
- Reduces latency vs. chain-of-thought parsing.

**Trade-off:** Forces the model to be more rigid. Mitigated by including a fallback JSON extractor using regex in `call_claude()`.

---

### 2.2 Single System Prompt for All Four Stages
**Decision:** All stages (FAQ, Qualification, Escalation, Summary) are governed by one system prompt, with stage identity controlled by the `stage` field in the output schema.

**Reasoning:**
- Avoids prompt-switching mid-conversation, which can cause context loss or jarring behaviour shifts.
- The model naturally transitions stages based on conversational context (e.g., once FAQs are answered, it moves to qualification).
- Simpler to maintain: one document of truth for all AI behaviour.

**Alternative considered:** Separate prompts per stage, switching on each turn. Rejected because it would require re-injecting conversation history into a new context, risking inconsistency.

---

### 2.3 SOP Injected Directly into System Prompt
**Decision:** The full SOP JSON is injected as plaintext into the system prompt at startup.

**Reasoning:**
- Gives the model clear, structured access to all business data.
- JSON format is natively understood; no need for retrieval or embedding.
- For an SMB with limited SOP size (< 2,000 tokens), this is efficient and reliable.

**Scaling note:** For larger SOPs (multiple locations, hundreds of services), this would be replaced with semantic retrieval (RAG) before injection.

---

## 3. Hallucination Prevention

### Strategy: SOP-Grounded with Explicit Prohibition + Confidence Signal

Three layers prevent hallucination:

**Layer 1 — Explicit instruction in system prompt:**
```
You must ONLY answer using the information in the SOP below.
Do NOT guess or infer. Do NOT invent prices, services, or policies not in the SOP.
```

**Layer 2 — Confidence field:**
The model reports its own confidence (`high | medium | low`) on every turn. `low` signals uncertainty and automatically triggers escalation after 2 consecutive low-confidence turns (enforced in Python, not relying on the model to self-escalate).

**Layer 3 — SOP gap tracking:**
When the model's `internal_note` indicates a question is not in the SOP, the Python layer records it as a `sop_gap` and includes it in the end-of-session summary. This creates an actionable feedback loop: the operations team can update the SOP based on real customer questions.

**Why this works:**
- The model is explicitly told *what to do* when it doesn't know (acknowledge + escalate), removing the temptation to fill the gap with plausible-sounding information.
- The `internal_note` field creates a separation between the model's reasoning and its customer-facing output — this makes it less likely to "rationalize" a hallucinated answer.

---

## 4. Confidence-Based Escalation

### Detection Method: Multi-Signal with Python Fallback

Escalation is detected through **four parallel signals:**

| Signal | How Detected | Who Triggers |
|--------|-------------|--------------|
| Explicit request | Customer says "speak to human", "agent", etc. | Model sets `escalate: true` |
| Out-of-scope question | SOP doesn't cover the topic | Model sets `escalate: true`, `confidence: low` |
| Negative sentiment | Frustration, complaint, anger detected in message | Model sets `escalate: true` |
| Consecutive low confidence | Two turns with `confidence: low` | **Python fallback** overrides |

**Why Python fallback?**
The model might not always self-escalate consistently after two low-confidence answers. The orchestration layer (`handle_turn()` in `workflow.py`) tracks `low_confidence_streak` independently and forces escalation if the threshold is hit — making the system reliable even if the model's self-assessment is inconsistent.

**Escalation output format:**
```json
{
  "escalate": true,
  "escalation_reason": "Medical question: customer asked about allergy contraindications"
}
```

Escalation reasons are human-readable and logged to `session_log.json` with a full transcript snapshot at that point.

---

## 5. Tone and Persona

### Persona: "Bloom" — The Trusted Front-Desk Receptionist

**Design rationale for SMB context:**

Aesthetic clinics deal with customers who may feel vulnerable or anxious about their appearance. The persona must:
- Feel personal and warm, not transactional
- Project calm competence (this is a medical-adjacent setting)
- Not oversell — trust is the core product

**Specific tone rules:**
- **Lead with empathy, close with action.** ("That's a great question — Botox starts from £200 and takes just 30 minutes. Would you like to book a free consultation to discuss what's right for you?")
- **No corporate language.** No "As per your query...", "Please be advised that...", etc.
- **Acknowledge uncertainty without embarrassment.** If the AI doesn't know, it says so naturally: "That's something our team would be better placed to answer — let me connect you with them."
- **Qualification questions are woven in naturally**, not fired as a list. The model asks one at a time.

**Named persona:**
Giving the AI the name "Bloom" (matching the clinic) creates coherence: the customer feels they're talking to a clinic representative, not a generic chatbot. This reduces friction and increases trust in the responses.

---

## 6. Lead Qualification Design

The qualification flow collects three data points:

1. **Primary interest / what brings them in** — Identifies the right service and frames the consultation.
2. **Prior treatment experience** — Helps the practitioner calibrate expectations and approach.
3. **Preferred contact/booking method** — Enables follow-up without friction.

**Pacing rule:** Questions are asked one at a time, naturally woven into the conversation after 1–2 FAQ responses. This avoids making the customer feel interrogated and keeps the conversation feeling human.

Collected data is stored in `qualification_data` in the JSON schema and surfaced in the session summary.

---

## 7. Summary Prompt Design

The summary uses a **separate system prompt** (`SYSTEM_PROMPT_SUMMARY`) to produce a structured JSON report. It receives:
- Full conversation transcript
- SOP gaps flagged during session
- Qualification data collected
- Escalation status and reason

**Key design decision:** The summary is generated in a fresh API call (not appended to the main conversation) to avoid the model being influenced by its own previous responses. It is given only facts, not the prior system prompt.

**Output structure:**
```json
{
  "customer_intent": "...",
  "key_details_collected": { ... },
  "sop_gaps": ["..."],
  "recommended_next_action": "...",
  "conversation_quality": "good | needs_review"
}
```

The `recommended_next_action` field is the most operationally useful: it tells the human team exactly what to do next (e.g., "Book free consultation", "Human follow-up required — post-treatment complaint").

---

## 8. Known Limitations & Trade-offs

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No persistent memory across sessions | Each session starts fresh | Session JSON saved to disk; can be loaded for continuity |
| JSON parsing can fail on edge cases | Rare model output format errors | Regex fallback extractor in `call_claude()` |
| Sentiment detection is model-dependent | May miss subtle passive aggression | Low-confidence fallback catches most edge cases |
| SOP injected in full | Won't scale past ~4,000 tokens | RAG/retrieval layer recommended for larger SOPs |
| No real-time human handoff | Escalation is logged, not routed | Integration with CRM/ticketing (e.g., HubSpot, Zendesk) is the next step |

---

## 9. What Makes This Different

Most AI support bots either:
- Hallucinate confidently (no guardrails), or
- Refuse to answer anything (over-cautious)

This workflow is designed to **fail gracefully and informatively**:
- When it can't help, it says *why* and logs the gap.
- It tracks its own uncertainty and escalates proactively.
- Every session produces a summary that makes the human team *smarter*, not just informed.

The SOP gap tracking is particularly differentiated: after a week of real conversations, the operations team would have a ranked list of the most common questions the AI couldn't answer — enabling rapid SOP improvement.
