# Eventarc Firestore CDC plus Pub/Sub push consumer for sf-support.

terraform {
  required_version = ">= 1.6.0"
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

variable "cloud_run_service" {
  type    = string
  default = "study-forge-support"
}

variable "cloud_run_url" {
  type = string
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "required" {
  for_each = toset([
    "pubsub.googleapis.com",
    "eventarc.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
  ])
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

module "event_hub" {
  source     = "../../modules/event-hub"
  project_id = var.project_id
  depends_on = [google_project_service.required]
}

module "cdc" {
  source             = "../../modules/cdc"
  project_id         = var.project_id
  project_number     = var.project_number
  region             = var.region
  firestore_location = var.region
  cloud_run_service  = var.cloud_run_service
  cloud_run_url      = var.cloud_run_url
  events_topic       = module.event_hub.topic_name
  dlq_topic          = module.event_hub.dlq_topic_name
}

resource "google_pubsub_topic_iam_member" "runtime_publisher" {
  project = var.project_id
  topic   = module.event_hub.topic_name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

output "support_events_topic" {
  value = module.event_hub.topic_name
}

output "eventarc_trigger_names" {
  value = module.cdc.eventarc_trigger_names
}

output "push_subscription" {
  value = module.cdc.push_subscription
}

