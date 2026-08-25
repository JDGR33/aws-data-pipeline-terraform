# AWS Data Pipeline with Terraform

An evolving data-engineering project focused on collecting and preparing Texas energy and weather data with AWS-compatible infrastructure.

## Vision

Build a reliable, serverless data pipeline that turns public Texas energy and environmental APIs into well-structured, queryable datasets. The project is also a transparent record of learning how to design, provision, test, and document data infrastructure with Terraform.

## Abilities I Want to Show

- Infrastructure as Code with Terraform, developed locally with LocalStack and designed for AWS.
- Python data collection from public APIs, including EIA ERCOT data and Open-Meteo weather data.
- Data engineering practices such as schema validation, quality checks, partitioning, and Parquet-based analytical storage.
- Clear engineering documentation and a public record of the project's progress in [`log_book.md`](log_book.md).

## What This Project Is Not

- It is not a finished production platform.
- It is not a general-purpose data ingestion service.
- It does not yet provide a complete transformation, serving, or CI/CD layer.
- It does not store API secrets in the repository or treat local development as a substitute for production security and operations.

## Current State and Next Steps

The repository has its initial Terraform and LocalStack foundation, and the raw-data collector is working for Texas energy and weather datasets. It supports backfill and incremental deliveries, keeps source payloads unchanged, and records collection metadata separately.

The next step is to define the raw-zone processing contract: read delivered objects from S3, validate and normalize each source schema, quarantine failures, and write refined Parquet datasets for analytical querying. Later stages will add quality gates, a serving layer, CI/CD, and deployment documentation.
