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

**Account snapshot**:
One Postgres row per Firebase UID. A StudyForge Firestore trigger publishes `account.snapshot.updated` when billing fields or monthly spent credits change. Plan status plus included and spent credits. No Stripe ids and no prices. The ticket graph reads this row and does not call StudyForge.
_Avoid_: billing record, Stripe customer, live account lookup

**Staff context**:
Postgres fields on a bug or billing **Ticket**: the **Account snapshot** (or a missing flag), retrieved Help snippets, and article titles. Not a thread message. Omitted from the lean ticket the user reads.
_Avoid_: internal note shown to the user, system message

**Suggested reply**:
A cited draft for **Staff**, stored on the bug or billing **Ticket**. Written only when Help chunks are enough. Staff edit it and post it as a staff message. Until that post, the user does not see it.
_Avoid_: auto-reply, resolution, RAG answer to the user

## Knowledge

**Help article**:
Published markdown used for hybrid search. Seeded from curated files or written by staff. Distinct from a user's StudyForge **Document**.
_Avoid_: knowledge base (alone), RAG doc, platform agent knowledge (that term belongs to StudyForge)

**Support command**:
A create-only Firestore inbox doc (`supportCommands/{id}`) from the StudyForge web app. `supportCommandCdc` publishes `command.submitted` with the full payload. sf-support consumes that event and does not read Firestore.
_Avoid_: ticket create API, webhook from web

**Ticket SoT row**:
Postgres `tickets` and `messages` in Cloud SQL (local Compose for dev). The command worker persists only. Datastream CDC publishes `ticket.updated` after row changes.
_Avoid_: lean ticket, Firestore master ticket

**Lean ticket**:
Read-model docs (`supportTickets`, `supportAskResults`) the chat window listens to. Written by StudyForge Pub/Sub functions (`supportTicketLeanProject`, `supportLeanProject`) or a local `write_id` poller.
_Avoid_: system of record

**Ticket CDC trigger leg**:
Datastream to GCS JSON, Eventarc to sfs `/__eventarc/publish`, re-read Postgres, publish `ticket.updated`. Only path for ticket domain events in production.
_Avoid_: worker publish, Firestore SoT for tickets

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
- A **Support user** has at most one **Account snapshot**
- A **Ticket** has one category and many thread messages
- A bug or billing **Ticket** has **Staff context** and an optional **Suggested reply**
- A **Suggested reply** becomes a thread message only after **Staff** post it
- A published **Help article** has many **Help chunks**
- How-it-works RAG reads **Help chunks** only, never raw **Ticket** text
- The ticket copilot grades **Help chunks** only. The **Account snapshot** is not retrieval context
