# PR 1: Critical review comments

CodeRabbit marked four items Critical on [sf-support PR 1](https://github.com/AndreMashukov/sf-support/pull/1). This file records what each comment meant and what we changed. StudyForge PR 74 had no Critical comments.

## 1. Datastream cannot reach Cloud SQL (`infra/modules/cloud-sql/main.tf`)

**Comment:** The Datastream source profile uses the Cloud SQL public IP, but `ip_configuration` had no `authorized_networks`. Cloud SQL rejects public connections that are not on that list. Datastream publishes regional static IPs that must be allowed. Without them, the source connection test never reaches Postgres.

**Why it is Critical:** The stream never starts. No WAL JSONL, no Eventarc, no `ticket.updated`.

**Fix:** Read IPs from data source `google_datastream_static_ips` for `var.region` and add each address as an `authorized_networks` entry. For `asia-east1` that is the Taiwan Datastream allowlist (currently five addresses). Re-apply picks up changes if Google updates the list.

## 2. Stream `desired_state = RUNNING` on first apply (`infra/modules/datastream-cdc/main.tf`)

**Comment:** Terraform asked Datastream to run immediately. Publication `support_cdc` and slot `support_cdc_slot` are created later by bootstrap SQL. Datastream requires both before the stream can run. First apply fails or the stream sits in an error state.

**Why it is Critical:** A green `terraform apply` does not mean CDC is live. Operators then fight a stream that cannot attach to WAL.

**Fix:** Default `stream_desired_state` is `NOT_STARTED`. Wire it from `infra/envs/dev` as `datastream_stream_desired_state`. After bootstrap SQL succeeds, apply again with `-var='datastream_stream_desired_state=RUNNING'`. `infra/README.md` documents the two applies.

## 3. Invalid `file_format` on GCS destination (`infra/modules/datastream-cdc/main.tf`)

**Comment:** Google provider 6.x `gcs_destination_config` does not accept `file_format = "JSON"`. It requires a `json_file_format` or `avro_file_format` block. Terraform validation fails, so the stream resource cannot be applied.

**Why it is Critical:** The CDC module cannot be applied as written.

**Fix:** Use `json_file_format` with `schema_file_format = NO_SCHEMA_FILE` and `compression = NO_COMPRESSION`. That matches the JSONL objects Cloud Run already parses (`app/support_bus/datastream.py`).

## 4. Bootstrap SQL missing replication slot and privileges

**Comment:** Generated SQL and `infra/sql/bootstrap-datastream.sql` only granted `SELECT` and created a publication. Datastream also needs:

- `USAGE` on schema `public`
- `REPLICATION` on the Datastream role
- logical slot `support_cdc_slot` with plugin `pgoutput`

Without those, the stream cannot consume WAL even if it is `RUNNING`.

**Why it is Critical:** GCS stays empty after ticket writes. The app looks healthy but lean Firestore never updates.

**Fix:** Both the Terraform output and `infra/sql/bootstrap-datastream.sql` now grant schema usage, `SELECT` on `tickets` and `messages`, `ALTER USER ... WITH REPLICATION`, create publication `support_cdc` if missing, and create slot `support_cdc_slot` with `pg_create_logical_replication_slot` if missing. Create the slot while connected as user `datastream` so that user owns it. Cloud SQL rejects a slot owned by `postgres` when Datastream connects as `datastream`.
