# Datastream Postgres CDC to GCS, Eventarc to Cloud Run /__eventarc/publish.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "cloud_run_service" {
  type = string
}

variable "cloud_run_url" {
  type = string
}

variable "postgres_host" {
  type = string
}

variable "postgres_port" {
  type    = number
  default = 5432
}

variable "postgres_database" {
  type = string
}

variable "postgres_username" {
  type = string
}

variable "postgres_password" {
  type      = string
  sensitive = true
}

variable "publication_name" {
  type    = string
  default = "support_cdc"
}

variable "replication_slot" {
  type    = string
  default = "support_cdc_slot"
}

variable "gcs_bucket_name" {
  type    = string
  default = ""
}

locals {
  bucket_name = var.gcs_bucket_name != "" ? var.gcs_bucket_name : "${var.project_id}-sf-support-cdc"
}

resource "google_storage_bucket" "cdc" {
  project                     = var.project_id
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_service_account" "eventarc" {
  project      = var.project_id
  account_id   = "sfs-cdc-eventarc"
  display_name = "sf-support Datastream Eventarc"
}

resource "google_project_iam_member" "eventarc_event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = google_service_account.eventarc.member
}

resource "google_cloud_run_v2_service_iam_member" "eventarc_invoker" {
  project  = var.project_id
  location = var.region
  name     = var.cloud_run_service
  role     = "roles/run.invoker"
  member   = google_service_account.eventarc.member
}

resource "google_eventarc_trigger" "datastream_gcs" {
  project  = var.project_id
  name     = "support-cdc-gcs"
  location = var.region

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.cdc.name
  }

  destination {
    cloud_run_service {
      service = var.cloud_run_service
      region  = var.region
      path    = "/__eventarc/publish"
    }
  }

  service_account = google_service_account.eventarc.email

  depends_on = [google_cloud_run_v2_service_iam_member.eventarc_invoker]
}

resource "google_datastream_connection_profile" "source" {
  project               = var.project_id
  location              = var.region
  connection_profile_id = "sf-support-pg-source"
  display_name          = "sf-support Postgres source"

  postgresql_profile {
    hostname = var.postgres_host
    port     = var.postgres_port
    username = var.postgres_username
    password = var.postgres_password
    database = var.postgres_database
  }
}

resource "google_datastream_connection_profile" "destination" {
  project               = var.project_id
  location              = var.region
  connection_profile_id = "sf-support-gcs-dest"
  display_name          = "sf-support GCS destination"

  gcs_profile {
    bucket    = google_storage_bucket.cdc.name
    root_path = "/support-cdc"
  }
}

resource "google_datastream_stream" "support_tickets" {
  project       = var.project_id
  location      = var.region
  stream_id     = "sf-support-tickets"
  display_name  = "sf-support tickets and messages"
  desired_state = "RUNNING"

  source_config {
    source_connection_profile = google_datastream_connection_profile.source.id

    postgresql_source_config {
      publication      = var.publication_name
      replication_slot = var.replication_slot

      include_objects {
        postgresql_schemas {
          schema = "public"
          postgresql_tables {
            table = "tickets"
          }
          postgresql_tables {
            table = "messages"
          }
        }
      }
    }
  }

  destination_config {
    destination_connection_profile = google_datastream_connection_profile.destination.id

    gcs_destination_config {
      file_format = "JSON"
    }
  }

  backfill_none {}
}

output "gcs_bucket_name" {
  value = google_storage_bucket.cdc.name
}

output "eventarc_trigger_name" {
  value = google_eventarc_trigger.datastream_gcs.name
}

output "datastream_stream_id" {
  value = google_datastream_stream.support_tickets.stream_id
}

output "bootstrap_sql" {
  value = <<-SQL
    GRANT SELECT ON tickets, messages TO ${var.postgres_username};
    CREATE PUBLICATION ${var.publication_name} FOR TABLE tickets, messages;
  SQL
}
