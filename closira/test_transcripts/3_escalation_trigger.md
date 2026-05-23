# Test Transcript 3: Escalation Trigger — Angry Customer / Complaint
### Scenario: Customer expresses frustration; AI detects sentiment and hands off

Session Date: 2026-05-23

---

**Customer:** I had a treatment last week and my face is still swollen. I'm really unhappy.

**Bloom (AI):** I'm so sorry to hear you're experiencing this — that must be really worrying, and your concern is completely valid. Post-treatment reactions like swelling are something our clinical team needs to look at directly. I'm escalating your message to a senior member of our team right now so they can follow up with you as a priority. Could you share your name and a contact number so they can reach you quickly?

*Stage: escalation | Confidence: high | Escalate: true*
*Escalation Reason: Post-treatment complaint with potential adverse reaction — customer expressing distress. Medical and complaint escalation triggered.*

---

**Customer:** I want to speak to someone NOW — this is unacceptable.

**Bloom (AI):** Completely understood, and I sincerely apologise for the distress this is causing. I've already flagged your case as urgent and a member of our team will be in touch very shortly. If you need to reach us immediately, please WhatsApp the clinic directly so we can get you the help you need as fast as possible.

*Stage: escalation | Confidence: high | Escalate: true*
*Escalation Reason: Continued complaint + explicit request for human agent. Escalation already active.*

---

> **System Log:** Escalation triggered at Turn 1. Reason: "Post-treatment complaint with potential adverse reaction — medical and sentiment escalation." Logged with full transcript snapshot to session_log.json.

---
