# PathVest GCP Infrastructure - Terraform Configuration

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    bucket = "pathvest-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "bigquery.googleapis.com",
    "storage-api.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "pubsub.googleapis.com",
    "redis.googleapis.com",
    "sqladmin.googleapis.com",
    "compute.googleapis.com"
  ])
  
  service            = each.key
  disable_on_destroy = false
}

# Cloud Storage Bucket for data
resource "google_storage_bucket" "data_bucket" {
  name          = "${var.project_id}-pathvest-data"
  location      = var.region
  force_destroy = false
  
  uniform_bucket_level_access = true
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# BigQuery Dataset for SEC Filings
resource "google_bigquery_dataset" "sec_filings" {
  dataset_id                 = "sec_filings"
  friendly_name              = "SEC Filings Data"
  description                = "13F, 13D/G, Form 4 filings"
  location                   = var.region
  default_table_expiration_ms = 0  # No expiration (full history retention)
  
  labels = {
    env = var.environment
  }
}

# BigQuery Dataset for Backtest Results
resource "google_bigquery_dataset" "backtest_results" {
  dataset_id    = "backtest_results"
  friendly_name = "Backtest Results"
  description   = "Strategy backtest outputs and analytics"
  location      = var.region
  
  labels = {
    env = var.environment
  }
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "pathvest_db" {
  name             = "pathvest-postgres-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier = "db-custom-2-7680"  # 2 vCPU, 7.5 GB RAM
    
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "02:00"
      backup_retention_settings {
        retained_backups = 30
      }
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }
    
    disk_size         = 100
    disk_autoresize   = true
    disk_type         = "PD_SSD"
    availability_type = "REGIONAL"  # High availability
  }
  
  deletion_protection = true
}

resource "google_sql_database" "pathvest" {
  name     = "pathvest"
  instance = google_sql_database_instance.pathvest_db.name
}

# MemoryStore Redis for caching
resource "google_redis_instance" "cache" {
  name               = "pathvest-cache-${var.environment}"
  tier               = "STANDARD_HA"
  memory_size_gb     = 5
  region             = var.region
  redis_version      = "REDIS_7_0"
  authorized_network = google_compute_network.vpc.id
  
  display_name = "PathVest Cache"
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "pathvest-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "pathvest-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
  
  private_ip_google_access = true
}

# Pub/Sub Topic for backtest queue
resource "google_pubsub_topic" "backtest_queue" {
  name = "pathvest-backtest-queue"
  
  message_retention_duration = "604800s"  # 7 days
}

resource "google_pubsub_subscription" "backtest_worker" {
  name  = "pathvest-backtest-worker"
  topic = google_pubsub_topic.backtest_queue.name
  
  ack_deadline_seconds = 600  # 10 minutes
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.backtest_dlq.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_topic" "backtest_dlq" {
  name = "pathvest-backtest-dlq"
}

# Secret Manager for sensitive data
resource "google_secret_manager_secret" "database_url" {
  secret_id = "DATABASE_URL"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "alphavantage_api_key" {
  secret_id = "ALPHAVANTAGE_API_KEY"
  
  replication {
    auto {}
  }
}

# Cloud Scheduler for periodic tasks
resource "google_cloud_scheduler_job" "daily_data_refresh" {
  name             = "pathvest-daily-data-refresh"
  description      = "Trigger daily SEC data refresh"
  schedule         = "0 2 * * *"  # 2 AM daily
  time_zone        = "America/New_York"
  attempt_deadline = "320s"
  
  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.backend.status[0].url}/api/v1/admin/trigger-data-refresh"
    
    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}

# Service Account for Cloud Scheduler
resource "google_service_account" "scheduler" {
  account_id   = "pathvest-scheduler"
  display_name = "PathVest Cloud Scheduler"
}

# Cloud Run Service - Backend
resource "google_cloud_run_service" "backend" {
  name     = "pathvest-backend"
  location = var.region
  
  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/pathvest-backend:latest"
        
        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }
        
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.database_url.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name = "ALPHAVANTAGE_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.alphavantage_api_key.secret_id
              key  = "latest"
            }
          }
        }
      }
      
      service_account_name = google_service_account.backend.email
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "10"
        "autoscaling.knative.dev/minScale" = "1"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Service Account for Backend
resource "google_service_account" "backend" {
  account_id   = "pathvest-backend"
  display_name = "PathVest Backend Service"
}

# IAM bindings for Backend Service Account
resource "google_project_iam_member" "backend_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "backend_storage" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Cloud Run IAM - Allow unauthenticated for public API
resource "google_cloud_run_service_iam_member" "backend_public" {
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "backend_url" {
  value       = google_cloud_run_service.backend.status[0].url
  description = "URL of the backend API"
}

output "bigquery_dataset_id" {
  value       = google_bigquery_dataset.sec_filings.dataset_id
  description = "BigQuery dataset for SEC filings"
}

output "redis_host" {
  value       = google_redis_instance.cache.host
  description = "Redis cache host"
}

output "database_connection" {
  value       = google_sql_database_instance.pathvest_db.connection_name
  description = "Cloud SQL connection name"
  sensitive   = true
}

