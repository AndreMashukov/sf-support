-- Run once after sf-support schema exists on Cloud SQL (tickets + messages tables).
-- 1) GRANTs, REPLICATION, and publication: run as postgres (cloudsqlsuperuser).
-- 2) Replication slot: run as the Datastream user (datastream) so that user owns the slot.
-- Replace datastream / support_cdc / support_cdc_slot if Terraform outputs differ.

GRANT USAGE ON SCHEMA public TO datastream;
GRANT SELECT ON tickets, messages TO datastream;
ALTER USER datastream WITH REPLICATION;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'support_cdc') THEN
    CREATE PUBLICATION support_cdc FOR TABLE tickets, messages;
  END IF;
END $$;

-- Connect as datastream, then:
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_replication_slots WHERE slot_name = 'support_cdc_slot'
  ) THEN
    PERFORM pg_create_logical_replication_slot('support_cdc_slot', 'pgoutput');
  END IF;
END $$;
