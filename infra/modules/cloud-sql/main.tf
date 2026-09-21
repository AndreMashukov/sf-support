# Cloud SQL Postgres 16 (pgvector) for sf-support SoT.

terraform {
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

variable "region" {
  type = string
}

variable "instance_name" {
  type    = string
  default = "study-forge-support"
}

variable "database_name" {
  type    = string
  default = "support"
}

variable "tier" {
  type    = string
  default = "db-custom-1-3840"
}

variable "deletion_protection" {
  type    = bool
  default = false
}

data "google_datastream_static_ips" "region" {
  project  = var.project_id
  location = var.region
}

resource "random_password" "postgres" {
  length  = 24
  special = false
}

resource "random_password" "datastream" {
  length  = 24
  special = false
}

resource "google_sql_database_instance" "support" {
  project             = var.project_id
  name                = var.instance_name
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = var.deletion_protection

  settings {
    tier              = var.tier
    availability_type = "ZONAL"
    disk_size         = 20
    disk_type         = "PD_SSD"

    database_flags {
      name  = "cloudsql.logical_decoding"
      value = "on"
    }

    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"

      dynamic "authorized_networks" {
        for_each = data.google_datastream_static_ips.region.static_ips
        content {
          name  = "datastream-${replace(authorized_networks.value, ".", "-")}"
          value = authorized_networks.value
        }
      }
    }

    backup_configuration {
      enabled = true
    }
  }
}

resource "google_sql_database" "support" {
  project  = var.project_id
  name     = var.database_name
  instance = google_sql_database_instance.support.name
}

resource "google_sql_user" "app" {
  project  = var.project_id
  name     = "support"
  instance = google_sql_database_instance.support.name
  password = random_password.postgres.result
}

resource "google_sql_user" "datastream" {
  project  = var.project_id
  name     = "datastream"
  instance = google_sql_database_instance.support.name
  password = random_password.datastream.result
}

output "instance_connection_name" {
  value = google_sql_database_instance.support.connection_name
}

output "public_ip_address" {
  value = google_sql_database_instance.support.public_ip_address
}

output "database_name" {
  value = google_sql_database.support.name
}

output "app_user" {
  value = google_sql_user.app.name
}

output "app_password" {
  value     = random_password.postgres.result
  sensitive = true
}

output "datastream_user" {
  value = google_sql_user.datastream.name
}

output "datastream_password" {
  value     = random_password.datastream.result
  sensitive = true
}

output "server_ca_cert" {
  value     = google_sql_database_instance.support.server_ca_cert[0].cert
  sensitive = true
}

output "database_url_hint" {
  value = "postgresql+psycopg://${google_sql_user.app.name}:<password>@${google_sql_database_instance.support.public_ip_address}:5432/${google_sql_database.support.name}?sslmode=require"
}
