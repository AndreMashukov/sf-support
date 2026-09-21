# Support event bus and ticket CDC (Terraform)

```bash
cd infra/envs/dev
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
# After Cloud SQL has tickets/messages, run terraform output -raw datastream_bootstrap_sql
# (or infra/sql/bootstrap-datastream.sql). Then start the stream:
# terraform apply -var='datastream_stream_desired_state=RUNNING'
```

This creates:

- Pub/Sub `support-events` plus DLQ
- Push subscription to sfs `/pubsub/push` (filter: `command.submitted`)
- Cloud SQL Postgres 16 (pgvector) for tickets and Help index
- Datastream stream: `tickets` and `messages` to GCS JSON
- Eventarc on GCS object finalized to Cloud Run `/__eventarc/publish`
- IAM for Cloud Run runtime (Pub/Sub publish, GCS read)

First apply leaves the Datastream stream `NOT_STARTED`. After Cloud SQL has `tickets` and `messages`, run `terraform output -raw datastream_bootstrap_sql` (or `infra/sql/bootstrap-datastream.sql`): GRANTs, `REPLICATION`, publication `support_cdc`, and slot `support_cdc_slot` (create the slot as user `datastream`). Then `terraform apply -var='datastream_stream_desired_state=RUNNING'`.

Cloud SQL instance name is `study-forge-support` (`cloud_sql_instance_name`). Import that instance before any apply. Do not apply this module in a way that creates a second database.

Cloud SQL `authorized_networks` is filled from Datastream regional static IPs (`google_datastream_static_ips`) so the public source profile can connect. Public connections require TLS (`ssl_mode = ENCRYPTED_ONLY`). The Datastream source profile uses `ssl_config.server_verification` with the instance server CA. Direct app URLs need `sslmode=require`. Cloud SQL Auth Proxy already encrypts the path to Cloud SQL.

StudyForge Firebase Functions:

- `supportCommandCdc` publishes `command.submitted`
- `supportLeanProject` writes `supportAskResults` from `ask.completed`
- `supportTicketLeanProject` writes `supportTickets` from `ticket.updated`

Local emulator uses `LOCAL_CDC_SHORTCUT=true` (polls `supportCommands` and `tickets.write_id`). Production Cloud Run should use `SUPPORT_EVENTS_BACKEND=pubsub`, `LOCAL_CDC_SHORTCUT=false`, and `SUPPORT_CDC_GCS_BUCKET` set to the Terraform output bucket.

Review notes for the Datastream Terraform Critical comments: [docs/pr-1-critical-comments.md](../docs/pr-1-critical-comments.md).
