# AWS-DATA-PIPELINE-TERRAFORM

## 2026-07-28
* Installed AWS CLI
* Terraform is blcoked in Venezuela, should use VPN for all of this

## 2026-07-29
* Installed Terraform using a VPN and the Binary
* Installed npm to installed LocalStack
* Login with my LocalStack basic account in my  local pc 

## 2026-07-30
* Create Python .ven for pip installing terraform-local 
* I needed to use VPN for Terraform init. It makes calles to a registry
* Manage to run "tflocal apply" and got the all good prompt

## 2026-07-31
* Set Up AWS CLI for LocalStack
* Test AWS CLI and LocalStack S3

## 2026-08-01
* Research about posible data Sources

## 2026-06-03
* Testing the API Micro-Mobility & Spatial Feeds APIs

## 2026-08-05
* Testing the US Energy Information Administration (EIA v2 API) and OpenMeteo API

## 2026-08-22
* Objective: Give Shape to Data that can be extracted from the APIs

### Raw Data Collector

The pipeline begins when an upstream collector uploads data to the raw S3 bucket. The collector is deliberately independent from the ETL infrastructure: it calls public APIs, uploads each API response unchanged as `payload.json`, and writes a sibling `metadata.json` with non-secret request details and a SHA-256 checksum.

Install the collector dependencies in the active Python environment:

```bash
pip install -r collector/requirements.txt
```

Copy `.env.example` to `.env` and set `EIA_API_KEY`. The collector writes locally by default, preserving the same raw path layout it uses in S3. Use `--destination s3` to upload to the configured bucket.

```bash
.venv/bin/python collector/collect_raw_data.py --dataset texas_weather --mode backfill --start 2025-01-01 --end 2025-01-31
.venv/bin/python collector/collect_raw_data.py --dataset ercot_fuel_type --mode backfill --start 2025-01-01T00 --end 2025-01-31T23 --destination s3
.venv/bin/python collector/collect_raw_data.py --dataset ercot_demand_forecast --mode incremental --destination s3
.venv/bin/python collector/collect_raw_data.py --dataset tx_retail_sales --mode backfill --start 2024-01 --end 2025-12 --destination s3
```

For AWS, omit `S3_ENDPOINT_URL`, set `RAW_BUCKET` to the deployed bucket name, and authenticate Boto3 using the standard AWS credential chain. The ETL pipeline processes only these S3 objects; it never calls a live source API.

## 2026-08-24 - Texas Raw Data Collection

Defined Texas as the project data domain and implemented the upstream raw-data collector in `collector/collect_raw_data.py`. Collection remains outside the ETL pipeline: the collector is responsible for live public API requests, while the pipeline is responsible only for files delivered to the raw S3 bucket.

The collector supports these datasets:

* EIA hourly ERCOT generation by fuel type (`ercot_fuel_type`)
* EIA hourly ERCOT day-ahead demand forecast (`ercot_demand_forecast`)
* EIA monthly Texas retail electricity price, sales, and revenue (`tx_retail_sales`)
* Open-Meteo hourly Houston weather, including temperature, solar irradiance, and wind speed (`texas_weather`)

Both `backfill` and `incremental` deliveries are supported. A backfill requires an explicit start and end range; an incremental collection defaults to the previous 24 completed hours. Each delivery uses an immutable, partition-style path:

```text
source=<eia|open_meteo>/dataset=<dataset>/delivery_type=<backfill|incremental>/ingested_date=YYYY-MM-DD/request_id=<uuid>/
```

Every delivery contains the unmodified API response in `payload.json` and a `metadata.json` sidecar. Metadata records the source URL, non-secret request parameters, UTC collection time, HTTP status, payload SHA-256 checksum, and the intended raw S3 key. API keys are excluded from metadata.

Local output is the default development mode and writes to `data/raw/`, which is ignored by Git. This was validated using real Open-Meteo archive data and a real EIA ERCOT fuel-type response. When LocalStack or AWS is available, pass `--destination s3` to use the same object layout in the raw bucket.

Validation completed with the repository Python environment:

```bash
.venv/bin/python -m py_compile collector/collect_raw_data.py
.venv/bin/python collector/collect_raw_data.py --dataset texas_weather --mode backfill --start 2025-01-01 --end 2025-01-02
```

The next project stage is the raw-zone processing contract: read these objects from S3, validate and normalize each source schema, quarantine failures, and write refined Parquet datasets for analytical querying.

## 2026-08-26
* Housekeeping in the repo cleaning, moving and committing files.
* Wrote an improve README for the current conditon of the project.

## 2026-08-27
* Added a Bash script to backfill all four datasets for June 2026.
* Added retry handling for temporary API and network failures; Open-Meteo collection succeeded.
* TODO: Eval Preliminary DataSet

## 2026-09-07
* Evaluated the preliminary June 2026 raw datasets in `collector/data_exploration.ipynb`.
* Normalized API timestamps, numeric measures, and categorical fields for the EIA forecast, fuel-type, retail-sales, and Open-Meteo data.
* Added explicit missing-value checks and comments describing each analysis step.
* Confirmed 720 forecast rows, 5,000 fuel-type rows, six retail-sales rows, and 720 weather rows execute successfully in the notebook.
* Documented that retail sales cover one month and contain missing measures for the `other` sector.
* TODO: Finish looking at the Meteo Data.

## 2026-09-08
* Added a month-batched 2026 backfill runner for all four datasets.
* The runner defaults to completed months, pauses between API requests, and supports local or S3 delivery.

## 2026-09-10 - Architecture Alignment & Sprint Planning
* Realigned end-to-end pipeline architecture based on core project objectives:
  1. **Data Ingestion:** Package the verified Python collector into an AWS Lambda function triggered by EventBridge cron schedules, outputting immutable JSON payloads with checksum metadata to the raw S3 bucket.
  2. **Local Prototyping:** Standardize local testing with LocalStack. Next immediate environment action is enabling Docker Desktop WSL 2 integration so LocalStack runs offline locally.
  3. **ETL & Transformation Engine:** Selected AWS Glue (PySpark) to ingest from S3 raw (Bronze), validate schemas, quarantine anomalies, and output partitioned Snappy Parquet to S3 refined (Silver).
  4. **Analytics & Serving:** AWS Glue Data Catalog + Athena for serverless SQL querying.
  5. **Terraform Modularization:** Restructure IaC into reusable modules (`modules/kms`, `modules/s3`, `modules/iam`, `modules/lambda`, `modules/glue`) and environment configurations (`envs/dev`, `envs/prod`).
* Updated `internal_README.md` and `README.md` to reflect the serverless Lambda + S3 + Glue + Athena pipeline architecture.
* Defined the upcoming Terraform modularization plan (modules/kms, modules/s3, modules/iam) and dual-bucket architecture (Bronze & Silver).
* Documented LocalStack operations and operational hygiene:
  * Health verification (`lstk status`, `curl http://localhost:4566/_localstack/health | jq .`), Docker container state, and GUI resource inspection via LocalStack Web App (`app.localstack.cloud`).
  * Emulation concepts (edge gateway port 4566, dummy credentials, CLI/Terraform shims `lstk aws` and `tflocal`).
  * State lifecycle: running ephemeral in-memory by default, reversing `--persist` via `lstk volume clear --force`, and quick in-memory resets with `lstk reset --force`.
* TODO: Start writing basic Terraform files (`modules/kms`, `modules/s3`, `modules/iam`, and `envs/dev/main.tf`).

## 2026-09-15 - Terraform Modularization & KMS Module Implementation
* **Terraform IaC Restructuring:**
  * Retired the monolithic prototype root `main.tf` in favor of an environment-driven structure (`envs/dev`) and reusable child modules (`modules/`).
* **KMS Module (`modules/kms`):**
  * Created reusable module defining customer-managed KMS key (`aws_kms_key`) and alias (`aws_kms_alias`).
  * Implemented security defaults: automatic key rotation enabled (`enable_key_rotation = true`) and configurable deletion window (7–30 days) with variable input validation.
  * Added alias naming validation enforcing the `alias/` prefix.
  * Exported `key_arn`, `key_id`, `alias_arn`, and `alias_name`.
* **Dev Environment Setup (`envs/dev`):**
  * Configured `providers.tf` targeting LocalStack on `http://localhost:4566` across core services (`kms`, `s3`, `iam`, `lambda`, `cloudwatch`, `glue`, `sts`).
  * Added `versions.tf` specifying required Terraform version (`>= 1.5.0`) and AWS provider (`>= 5.0`).
  * Defined parameterized `variables.tf` and environment inputs for region, environment (`dev`), and project naming (`texas-data-pipeline`).
  * Instantiated the KMS module in `envs/dev/main.tf` with standardized project and environment resource tagging.
  * Exposed module outputs via `envs/dev/outputs.tf`.
* **Verification & LocalStack Deployment:**
  * Initialized Terraform environment (`terraform init`), validated syntax and configurations (`terraform validate`).
  * Verified execution plan (`terraform plan`) and successfully provisioned resources against running LocalStack via `terraform apply`.
* **TODO:** Implement the S3 module (`modules/s3`) with encryption referencing the KMS module outputs for Bronze (raw) and Silver (refined) buckets.

## 2026-09-16
* Committed Terraform modularization structure and KMS module.
* Created S3 child module (`modules/s3`):
  * `variables.tf`: defined bucket naming regex, mandatory KMS ARN, versioning status validation, and `force_destroy`.
  * `main.tf`: configured bucket with SSE-KMS encryption, versioning, `BucketOwnerEnforced`, and public access block.
* TODO: Complete `modules/s3/outputs.tf`, instantiate raw and refined buckets in `envs/dev/main.tf`, and test in LocalStack.

## 2026-09-17 - S3 Child Module Completion, LocalStack DNS Troubleshooting, & Dual-Bucket Provisioning
* **Completed S3 Child Module (`modules/s3`):**
  * Created `outputs.tf` exposing bucket attributes: `bucket_id`, `bucket_arn`, `bucket_regional_domain_name`, and `s3_uri`.
  * Fixed syntax typo in `modules/kms/main.tf`.
* **Dual-Layer Architecture Provisioning (`envs/dev`):**
  * Instantiated Bronze (`s3_bronze` -> `texas-data-pipeline-dev-bronze`) and Silver (`s3_silver` -> `texas-data-pipeline-dev-silver`) buckets in `envs/dev/main.tf`.
  * Secured both layers with customer-managed KMS encryption (`modules/kms`), enforced ownership controls (`BucketOwnerEnforced`), blocked public access, enabled versioning, and tagged layers explicitly.
  * Exposed Bronze and Silver bucket IDs and ARNs via `envs/dev/outputs.tf`.
  * Initialized and registered the new module definitions in Terraform (`terraform init`).
  * Deployed infrastructure via `terraform apply` and verified resources in LocalStack using `lstk aws s3 ls`.
* **Engineering Deep-Dive & Lessons Learned: LocalStack S3 & Virtual-Hosted vs. Path-Style DNS Resolution:**
  * **The Problem:** During initial `terraform apply` for S3 bucket creation, Terraform failed with:
    `Error: creating S3 Bucket (...): dial tcp: lookup texas-data-pipeline-dev-raw.localhost on 10.255.255.254:53: no such host`.
  * **Root Cause:** By default, AWS SDKs and the Terraform AWS provider use **virtual-hosted-style** addressing for S3 endpoints (`<bucket-name>.<endpoint>`). When configured with `endpoint = "http://localhost:4566"`, Terraform formulated bucket URLs as `http://<bucket-name>.localhost:4566/`. While modern specifications treat `*.localhost` as loopback domains, local network and OS DNS resolvers (especially inside WSL 2 or custom system resolvers like `10.255.255.254:53`) do not support wildcard subdomains of `localhost`. Consequently, the DNS lookup fails before the request ever reaches port 4566.
  * **The Solution:** Added `s3_use_path_style = true` inside the `provider "aws"` block in `envs/dev/providers.tf`. This instructs the AWS client to format S3 requests using **path-style** addressing (`http://localhost:4566/<bucket-name>`). The DNS query evaluates strictly to `localhost` (resolving immediately to `127.0.0.1`), allowing LocalStack's edge proxy to route the request properly without custom `/etc/hosts` DNS overrides.
  * **Module Indexing Gotcha:** When adding new module calls (`module "s3_silver"`), Terraform references an internal manifest (`.terraform/modules/modules.json`). Even for local paths, `terraform init` (or `terraform get`) must be executed to register new module blocks before `terraform plan` or `terraform apply`.
* **TODO:** Package Python ingestion collector (`collector/collect_raw_data.py`) into an AWS Lambda function with EventBridge scheduled triggers.

## 2026-09-19 - Python Lambda Refactoring, Packaging Pipeline, & Serverless Best Practices
* **Refactored Ingestion Collector (`collector/collect_raw_data.py`):**
  * Decoupled collection logic from CLI `argparse` by extracting `collect_dataset()`, returning structured provenance and upload metrics (`dataset`, `status`, `bytes`, `payload_key`, `metadata_key`).
  * Updated `resolve_date_range()` to flexibly handle both programmatic string arguments and `argparse.Namespace` objects, preserving 100% backward compatibility for existing backfill scripts (`backfill_june_2026.sh`, `backfill_year_2026.sh`).
* **Created AWS Lambda Handler (`collector/lambda_handler.py`):**
  * Implemented standard entry point `lambda_handler(event, context)` supporting flexible invocation modes:
    * Single dataset invocation (e.g. `{"dataset": "texas_weather", "mode": "incremental"}`).
    * Multi-dataset batch invocation (e.g. `{"datasets": ["ercot_fuel_type", "ercot_demand_forecast"]}`).
    * Default cron invocation: automatically iterates over all supported project datasets when triggered by EventBridge scheduled rules with an empty payload.
  * Runtime configuration injected via environment variables (`RAW_BUCKET`, `DESTINATION`, `S3_ENDPOINT_URL`, `EIA_API_KEY`).
  * Implemented structured CloudWatch logging and exception propagation: unhandled failures raise `RuntimeError` to ensure AWS Lambda invocation metrics, EventBridge retries, and dead-letter queues (DLQs) trigger properly.
* **Automated Packaging Pipeline (`scripts/package_lambda.py`, `scripts/package_lambda.sh`):**
  * Created `collector/lambda_requirements.txt` isolating third-party runtime dependencies (`requests`, `python-dotenv`) while deliberately omitting `boto3`/`botocore` (which are pre-installed in the AWS Lambda runtime).
  * Built portable Python packaging script utilizing Python's built-in `zipfile` module (eliminating dependency on host-level `zip` binary).
  * Implemented vendor isolation via `pip install --target build/lambda`, stripping `__pycache__` and `*.pyc` files, and generating a lean 0.66 MB deployment artifact (`dist/collector_lambda.zip`).
  * Added `--skip-pip` flag enabling rapid sub-second re-packaging during local code iteration.
  * Updated `.gitignore` to exclude `build/`, `dist/`, and `*.zip`.
* **Automated Testing Suite (`tests/test_collector.py`):**
  * Added 10 automated unit tests covering date resolution, CLI/programmatic compatibility, input validation, S3 error scenarios, single/multi-dataset batching, and error propagation.
  * Verified 10/10 tests passing via `python -m unittest discover -s tests`.
* **Engineering Deep-Dive & Lessons Learned: Working with Python in AWS Lambda:**
  * **Handler Anatomy & Invocation Contract:**
    * Entry point format: AWS maps functions using `<file_name>.<function_name>` (e.g., `lambda_handler.lambda_handler`).
    * `event` parameter: A Python dictionary containing the invocation payload. Its schema is defined by the trigger source (custom JSON for EventBridge rules, S3 bucket/object metadata for S3 triggers, HTTP request envelopes for API Gateway).
    * `context` parameter: An AWS runtime object providing execution metadata, including `context.get_remaining_time_in_millis()` (time left before function timeout) and `context.aws_request_id` (unique invocation ID for log correlation).
  * **Statelessness & Ephemeral Disk Storage:**
    * Lambda containers are ephemeral and stateless. The filesystem is read-only except for `/tmp` (512 MB to 10 GB), which is purged when the execution environment is decommissioned.
    * Persistent pipeline artifacts must always be written to external storage (S3 Bronze layer) rather than local disk.
  * **Optimizing Cold Starts vs. Warm Starts (Global Scope):**
    * Code outside `lambda_handler()` executes once during container initialization ("cold start").
    * Heavy objects (e.g., `boto3.client("s3")`, HTTP session pools, database connections) should always be initialized in the global scope so they are cached and reused across subsequent "warm" invocations.
  * **Packaging Mechanics & Flat-Root Vendoring:**
    * AWS Lambda does not activate virtual environments (`.venv`). It executes against `/var/task/`.
    * All third-party packages must sit directly at the root of the `.zip` archive alongside handler files (or inside a Lambda Layer).
    * Pre-installed dependencies: AWS provides `boto3` and `botocore` out of the box. Omitting them from the package bundle reduced our zip size from ~40 MB to 0.66 MB, slashing cold-start download and initialization time.
  * **Deterministic Checksumming for Terraform (`source_code_hash`):**
    * Terraform detects Lambda code modifications using cryptographic file hashes (`filebase64sha256`).
    * Without updating this hash, Terraform's state assumes the function is up to date and skips deployment even if local files changed. The packaging pipeline computes SHA-256 hashes to guarantee clean Terraform drift detection.
  * **Error Handling Strategy (Async vs. Sync):**
    * For asynchronous triggers (EventBridge cron, S3 notifications), handlers must never silently catch and swallow errors. Raising an exception instructs AWS Lambda to record the invocation as failed, increment CloudWatch Error metrics, and trigger EventBridge retries / Dead Letter Queues (DLQs).
* **TODO:** Implement Terraform IAM execution role (`modules/iam`), Lambda function module (`modules/lambda`), and EventBridge scheduled rule (`modules/eventbridge`), then verify deployment against LocalStack.

## 2026-09-22 - IAM Child Module Implementation & Least-Privilege Policy Architecture
* **Created IAM Child Module (`modules/iam`):**
  * `variables.tf`: Defined inputs for `role_name`, `description`, `s3_bucket_arn`, `kms_key_arn`, and resource `tags`.
  * `main.tf`: Configured 3-tier IAM structure:
    1. `aws_iam_role.this`: Identity definition with `assume_role_policy` granting trust strictly to `lambda.amazonaws.com`.
    2. `aws_iam_role_policy_attachment.lambda_basic_execution`: Attached AWS managed policy `AWSLambdaBasicExecutionRole` for CloudWatch Logs permissions.
    3. `aws_iam_role_policy.collector_permissions`: Custom inline policy scoped strictly to least-privilege actions:
       * S3 write permissions (`s3:PutObject`, `s3:AbortMultipartUpload`) scoped strictly to `${var.s3_bucket_arn}/*`.
       * KMS encryption permissions (`kms:Encrypt`, `kms:GenerateDataKey`) scoped strictly to `var.kms_key_arn`.
  * `outputs.tf`: Exposed `role_arn` and `role_name` for downstream module consumption.
* **Engineering Deep-Dive & Lessons Learned: IAM Execution Policies & Encryption Mechanics:**
  * **Envelope Encryption & `kms:GenerateDataKey`:** KMS master keys cannot directly encrypt large data files (maximum 4 KB). Instead, S3 uses envelope encryption: S3 invokes KMS on behalf of the calling role to generate a one-time plaintext/ciphertext Data Encryption Key (DEK). If an IAM role only has `kms:Encrypt` and lacks `kms:GenerateDataKey`, S3 PUT operations will fail with `AccessDenied`.
  * **Orphaned Upload Prevention & `s3:AbortMultipartUpload`:** AWS SDKs (`boto3`) chunk larger files or streams via S3 Multipart Uploads. If a Lambda execution times out or errors mid-stream, `boto3` attempts to abort the multipart upload. Without `s3:AbortMultipartUpload`, stranded, incomplete chunks remain invisibly in S3 and accumulate ongoing storage billing.
  * **HCL Function Pitfall (`jsonencode` vs. `jsondecode`):** In Terraform HCL, IAM policy documents expect valid JSON strings. Using `jsonencode({...})` serializes the HCL object map into a valid JSON string at compile time. Conversely, `jsondecode()` parses an incoming JSON string into an HCL object, which causes a type mismatch (`string required, but have object`) if called on an HCL block.
* **TODO:** Implement Lambda child module (`modules/lambda`), configure EventBridge scheduled trigger, wire modules into `envs/dev/main.tf`, and verify deployment in LocalStack.




