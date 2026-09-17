# StudyForge Support

User-facing help and a staff ticket queue for StudyForge. Users ask how the product works, report bugs, or ask billing questions. RAG answers how-it-works questions from **Help articles** only.

Maintained via `/grill-with-docs`. ADRs live in `docs/adr/` (created lazily). Full product spec: [docs/architecture.md](docs/architecture.md).

## Tickets

**Ticket**:
An open or closed request from a StudyForge user. Categories: how it works, bug, billing. Not a StudyForge workspace-agent thread.
_Avoid_: issue (alone), case, Zendesk ticket

**How-it-works question**:
A product question answered from Help articles first. A **Ticket** is created only if the user chooses Still need help.
_Avoid_: FAQ query, deflection (in user-facing copy)

**Bug ticket**:
A **Ticket** that something is broken. Always created. No auto-answer as a resolution.
_Avoid_: incident, defect (in user-facing copy)

**Billing ticket**:
A **Ticket** about charges, credits, or plans. Always created. Do not invent credit amounts.
_Avoid_: invoice dispute (unless that is the user's wording)

**Still need help**:
The user action that turns a how-it-works RAG turn into a **Ticket**.
_Avoid_: escalate, file anyway

**Ticket thread**:
Messages on one **Ticket** from user, staff, or system (RAG draft). In-app only in v1.
_Avoid_: email thread, chat

## Knowledge

**Help article**:
Published markdown used for hybrid search. Seeded from curated files or written by staff. Distinct from a user's StudyForge **Document**.
_Avoid_: knowledge base (alone), RAG doc, platform agent knowledge (that term belongs to StudyForge)

**Help chunk**:
Embedded slice of a published **Help article**, plus a `tsvector` for keyword search.
_Avoid_: RAG chunk (alone)

**Hybrid search**:
Vector similarity plus Postgres full-text, fused with RRF, over **Help chunks**.
_Avoid_: semantic search (alone), BM25 (alone)

## People

**Support user**:
A signed-in StudyForge account (Firebase UID) using this app.
_Avoid_: customer (prefer user)

**Staff**:
A Support user with Firebase custom claim `role: admin`. Closes tickets and edits **Help articles**.
_Avoid_: agent (when meaning a human), admin (when meaning this app's staff UI)

## Relationships

- A **Support user** may have many **Tickets**
- A **Ticket** has one category and many thread messages
- A published **Help article** has many **Help chunks**
- How-it-works RAG reads **Help chunks** only, never raw **Ticket** text
