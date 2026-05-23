# Test Transcript 2: Out-of-Scope Question
### Scenario: Customer asks about services not in the SOP

Session Date: 2026-05-23

---

**Customer:** Do you offer laser hair removal?

**Bloom (AI):** Thanks for reaching out! Laser hair removal isn't something I have details on for our clinic — I wouldn't want to give you the wrong information. Let me flag this for one of our team members who can give you an accurate answer. Is there anything else I can help with in the meantime, such as our Botox or filler treatments?

*Stage: escalation | Confidence: low | Escalate: true*
*Escalation Reason: Out-of-scope question — service (laser hair removal) not found in SOP*

---

**Customer:** What about skin peels or facials?

**Bloom (AI):** I'm afraid I don't have details on skin peels or facials in the information I have available — I wouldn't want to guess and give you incorrect information. I've flagged your enquiry so a member of our team can follow up with the full picture. They'll be able to confirm exactly what's available.

*Stage: escalation | Confidence: low | Escalate: true*
*Escalation Reason: Second consecutive out-of-scope question — skin peels/facials not in SOP. Low confidence streak triggered human handoff.*

---

> **System Log:** Escalation flagged at Turn 1. SOP gaps recorded: ["Do you offer laser hair removal?", "What about skin peels or facials?"]. Logged to session_log.json.

---
