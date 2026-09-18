# Support event bus (Terraform)

Copied from `example/label-hold` (Eventarc plus Pub/Sub). Datastream is not used.

```bash
cd infra/envs/dev
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

This creates:

- Pub/Sub `support-events` plus DLQ
- Eventarc Firestore triggers on `supportCommands` (created), `supportAskSot` and `supportTicketSot` (written)
- Destination: Cloud Run `study-forge-support` path `/__eventarc/publish`
- Push subscription to `/pubsub/push`

Local emulator still uses `LOCAL_CDC_SHORTCUT=true` (poller). Production Cloud Run should use `SUPPORT_EVENTS_BACKEND=pubsub` and `LOCAL_CDC_SHORTCUT=false`.
