-- Run once after sf-support schema exists on Cloud SQL (tickets + messages tables).
-- Replace datastream with the Terraform output user if different.

GRANT SELECT ON tickets, messages TO datastream;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'support_cdc') THEN
    CREATE PUBLICATION support_cdc FOR TABLE tickets, messages;
  END IF;
END $$;
