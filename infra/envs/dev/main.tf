# Staging event bus. Eventarc Firestore triggers should target sfs
# /__eventarc/publish (label-hold bff-service pattern). Apply after APIs exist.

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

variable "region" {
  type    = string
  default = "asia-southeast1"
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

output "support_events_topic" {
  value = module.event_hub.topic_name
}
