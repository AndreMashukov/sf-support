# Support event bus (Terraform)

Copied from `example/label-hold` (Eventarc plus Pub/Sub). Datastream is not used.

```bash
cd infra/envs/dev
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
```

Local development does not apply this. Use Firebase emulators and `LOCAL_CDC_SHORTCUT=true` on sfs so `supportCommands` are processed without Eventarc.
