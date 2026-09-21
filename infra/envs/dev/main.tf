# Event bus, Cloud SQL, Datastream ticket CDC, Pub/Sub push consumer for sf-support.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
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
    "sqladmin.googleapis.com",
    "datastream.googleapis.com",
    "storage.googleapis.com",
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

module "cloud_sql" {
  source     = "../../modules/cloud-sql"
  project_id = var.project_id
  region     = var.region
  depends_on = [google_project_service.required]
}

module "datastream_cdc" {
  source              = "../../modules/datastream-cdc"
  project_id          = var.project_id
  region              = var.region
  cloud_run_service   = var.cloud_run_service
  cloud_run_url       = var.cloud_run_url
  postgres_host       = module.cloud_sql.public_ip_address
  postgres_database   = module.cloud_sql.database_name
  postgres_username   = module.cloud_sql.datastream_user
  postgres_password   = module.cloud_sql.datastream_password
  depends_on          = [module.cloud_sql]
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
  depends_on         = [module.event_hub]
}

resource "google_pubsub_topic_iam_member" "runtime_publisher" {
  project = var.project_id
  topic   = module.event_hub.topic_name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "runtime_cdc_reader" {
  bucket = module.datastream_cdc.gcs_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

output "support_events_topic" {
  value = module.event_hub.topic_name
}

output "eventarc_trigger_names" {
  value = [module.datastream_cdc.eventarc_trigger_name]
}

output "push_subscription" {
  value = module.cdc.push_subscription
}

output "cloud_sql_connection_name" {
  value = module.cloud_sql.instance_connection_name
}

output "cloud_sql_public_ip" {
  value = module.cloud_sql.public_ip_address
}

output "support_cdc_gcs_bucket" {
  value = module.datastream_cdc.gcs_bucket_name
}

output "datastream_bootstrap_sql" {
  value     = module.datastream_cdc.bootstrap_sql
  sensitive = false
}

output "cloud_sql_app_password" {
  value     = module.cloud_sql.app_password
  sensitive = true
}
