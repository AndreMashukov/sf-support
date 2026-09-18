# Pub/Sub topic + DLQ + IAM. Copied from example/label-hold, renamed for Support.

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

variable "topic_name" {
  type    = string
  default = "support-events"
}

variable "dlq_topic_name" {
  type    = string
  default = "support-events-dlq"
}

variable "message_retention_days" {
  type    = number
  default = 7
}

resource "google_pubsub_topic" "events" {
  project                    = var.project_id
  name                       = var.topic_name
  message_retention_duration = "${var.message_retention_days * 24 * 3600}s"
  labels = {
    app  = "sf-support"
    role = "event-hub"
  }
}

resource "google_pubsub_topic" "events_dlq" {
  project                    = var.project_id
  name                       = var.dlq_topic_name
  message_retention_duration = "${var.message_retention_days * 24 * 3600}s"
  labels = {
    app  = "sf-support"
    role = "event-hub-dlq"
  }
}

resource "google_service_account" "publisher" {
  project      = var.project_id
  account_id   = "support-eventhub-publisher"
  display_name = "Support event-hub publisher"
}

resource "google_pubsub_topic_iam_member" "publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.events.name
  role    = "roles/pubsub.publisher"
  member  = google_service_account.publisher.member
}

resource "google_service_account" "subscriber" {
  project      = var.project_id
  account_id   = "support-eventhub-subscriber"
  display_name = "Support event-hub subscriber"
}

resource "google_pubsub_topic_iam_member" "subscriber" {
  project = var.project_id
  topic   = google_pubsub_topic.events.name
  role    = "roles/pubsub.subscriber"
  member  = google_service_account.subscriber.member
}

resource "google_pubsub_subscription" "dlq_catch_all" {
  project                    = var.project_id
  name                       = "${var.dlq_topic_name}-catchall"
  topic                      = google_pubsub_topic.events_dlq.name
  message_retention_duration = "${var.message_retention_days * 24 * 3600}s"
  retain_acked_messages      = true
  ack_deadline_seconds       = 60
}

output "topic_id" {
  value = google_pubsub_topic.events.id
}

output "topic_name" {
  value = google_pubsub_topic.events.name
}

output "dlq_topic_id" {
  value = google_pubsub_topic.events_dlq.id
}

output "publisher_service_account_email" {
  value = google_service_account.publisher.email
}

output "subscriber_service_account_email" {
  value = google_service_account.subscriber.email
}
