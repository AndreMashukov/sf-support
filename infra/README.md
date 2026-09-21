# Support event bus and ticket CDC (Terraform)

```bash
cd infra/envs/dev
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

This creates:

- Pub/Sub `support-events` plus DLQ
- Push subscription to sfs `/pubsub/push` (filter: `command.submitted`)
- Cloud SQL Postgres 16 (pgvector) for tickets and Help index
- Datastream stream: `tickets` and `messages` to GCS JSON
- Eventarc on GCS object finalized to Cloud Run `/__eventarc/publish`
- IAM for Cloud Run runtime (Pub/Sub publish, GCS read)

After the first Cloud Run deploy against Cloud SQL, run the bootstrap SQL from `terraform output datastream_bootstrap_sql` (or `infra/sql/bootstrap-datastream.sql`) so Datastream can attach to publication `support_cdc`.

StudyForge Firebase Functions:

- `supportCommandCdc` publishes `command.submitted`
- `supportLeanProject` writes `supportAskResults` from `ask.completed`
- `supportTicketLeanProject` writes `supportTickets` from `ticket.updated`

Local emulator uses `LOCAL_CDC_SHORTCUT=true` (polls `supportCommands` and `tickets.write_id`). Production Cloud Run should use `SUPPORT_EVENTS_BACKEND=pubsub`, `LOCAL_CDC_SHORTCUT=false`, and `SUPPORT_CDC_GCS_BUCKET` set to the Terraform output bucket.
