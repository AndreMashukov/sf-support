# Pub/Sub push to Cloud Run /pubsub/push for command.submitted.
# Firestore CDC lives in StudyForge (supportCommandCdc). sfs does not publish CDC.

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

variable "project_number" {
  type = string
}

variable "region" {
  type    = string
  default = "asia-east1"
}

variable "firestore_location" {
  type    = string
  default = "asia-east1"
}

variable "cloud_run_service" {
  type = string
}

variable "cloud_run_url" {
  type = string
}

variable "events_topic" {
  type = string
}

variable "dlq_topic" {
  type = string
}

resource "google_service_account" "push" {
  project      = var.project_id
  account_id   = "sfs-bus-push"
  display_name = "sf-support Pub/Sub push"
}

resource "google_service_account_iam_member" "push_token_creator" {
  service_account_id = google_service_account.push.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = google_service_account.push.member
}

resource "google_cloud_run_v2_service_iam_member" "push_invoker" {
  project  = var.project_id
  name     = var.cloud_run_service
  location = var.region
  role     = "roles/run.invoker"
  member   = google_service_account.push.member
}

resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  project = var.project_id
  topic   = var.dlq_topic
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription" "push" {
  project                    = var.project_id
  name                       = "support-events-push"
  topic                      = var.events_topic
  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"
  filter                     = "attributes.event_type = \"command.submitted\""
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  dead_letter_policy {
    dead_letter_topic     = "projects/${var.project_id}/topics/${var.dlq_topic}"
    max_delivery_attempts = 5
  }
  push_config {
    push_endpoint = "${trimsuffix(var.cloud_run_url, "/")}/pubsub/push"
    oidc_token {
      service_account_email = google_service_account.push.email
    }
  }
  depends_on = [
    google_cloud_run_v2_service_iam_member.push_invoker,
    google_service_account_iam_member.push_token_creator,
    google_pubsub_topic_iam_member.dlq_publisher,
  ]
}

output "eventarc_trigger_names" {
  value = []
}

output "push_subscription" {
  value = google_pubsub_subscription.push.name
}
