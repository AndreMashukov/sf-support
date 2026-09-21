# Ticket CDC via Datastream, GCS, and Eventarc

We publish `ticket.updated` only after Postgres changes, not from the command worker in the same process. Cloud SQL holds ticket SoT. Datastream streams `tickets` and `messages` to GCS JSON. Eventarc calls sfs `/__eventarc/publish`, which re-reads Postgres and publishes to `support-events`. StudyForge `supportTicketLeanProject` writes lean Firestore.

We rejected in-process publish after persist because it couples the worker to the bus and skips a durable CDC boundary. We rejected a transactional outbox in v1 because the team chose managed Datastream over another table and poller. Ask results still use in-process `ask.completed` until `rag_runs` stores enough fields for CDC.

Local Compose uses a `write_id` poller instead of Datastream.
