# Financial ETL Pipeline Cookbook

This is personal open-source analytical ETL pipeline for financial reporting using AWS S3 for storage and open-source tools for processing and analytics.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Cost Structure](#cost-structure)
- [Prerequisites](#prerequisites)
- [Setup Guide](#setup-guide)
- [Usage Guide](#usage-guide)
- [Development](#development)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

This repository provides a complete solution for building an analytical ETL pipeline for financial reporting. It combines AWS S3 for reliable data storage with open-source tools for processing and visualization to create a cost-effective, production-ready solution.

### Features
- Collect financial data from public APIs
- Store raw and processed data in AWS S3
- Transform and model data using dbt
- Analyze financial metrics with PostgreSQL/TimescaleDB
- Create interactive dashboards with Metabase
- Schedule and monitor workflows with Apache Airflow

## Architecture

![Infrastructure Diagram](docs/images/architecture-diagram.png)

### Components

| Layer | Component | Technology | Function |
|-------|-----------|------------|----------|
| Data Sources | Financial APIs | Alpha Vantage, FRED, etc. | Provide financial data |
| Data Lake | Object Storage | AWS S3 | Store raw and processed data |
| Orchestration | Workflow Manager | Apache Airflow | Schedule and monitor workflows |
| Processing | Transformation | Python, dbt | Transform and model data |
| Data Warehouse | Database | PostgreSQL + TimescaleDB | Store and query analytical data |
| Visualization | Dashboarding | Metabase | Create reports and dashboards |

### Data Flow
1. Airflow triggers data extraction from financial APIs
2. Raw data is stored in the AWS S3 Raw zone
3. Python transformations process the data
4. Processed data is stored in the AWS S3 Processed zone
5. Data is loaded into PostgreSQL/TimescaleDB
6. dbt models transform the data into analytics-ready tables
7. Metabase connects to the database to generate reports and dashboards

## Cost Structure

| Component | Technology | Monthly Cost | Notes |
|-----------|------------|--------------|-------|
| Data Lake | AWS S3 | $1-3 | ~50-100GB storage |
| Data Warehouse | PostgreSQL/TimescaleDB | $0* | Self-hosted |
| Orchestration | Apache Airflow | $0* | Self-hosted |
| Visualization | Metabase | $0* | Self-hosted |
| Compute Resources | Self-hosted or Cloud VM | $5-20 | Depends on deployment |
| **Total** | | **$6-23/month** | |

*Software is free, compute resources cost depends on deployment method.

### Cost Comparison with Full AWS Stack
| Component | AWS Native | This Solution | Monthly Savings |
|-----------|------------|---------------|----------------|
| Data Lake | AWS S3: $1-3 | AWS S3: $1-3 | $0 |
| Data Warehouse | AWS Redshift: $108-180 | PostgreSQL: $0* | $108-180 |
| Orchestration | EC2 for Airflow: $20-32 | Self-hosted Airflow: $0* | $20-32 |
| **Total Savings** | | | **$128-212/month** |

## Prerequisites

Before beginning setup, ensure you have:

1. AWS Account with permissions to create:
   - S3 buckets
   - IAM roles and policies

2. Development environment with:
   - Docker and Docker Compose
   - AWS CLI configured
   - Git
   - Python 3.8+

3. API access:
   - Alpha Vantage API key (free tier available)
   - Other financial APIs as needed

## Setup Guide

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/financial-etl-cookbook.git
cd financial-etl-cookbook
```

### 2. AWS Infrastructure Setup

#### Create S3 Buckets

```bash
# Create raw data bucket
aws s3 mb s3://financial-reporting-raw-data

# Create processed data bucket
aws s3 mb s3://financial-reporting-processed-data

# Enable versioning (optional but recommended)
aws s3api put-bucket-versioning --bucket financial-reporting-raw-data --versioning-configuration Status=Enabled
aws s3api put-bucket-versioning --bucket financial-reporting-processed-data --versioning-configuration Status=Enabled
```

#### Create IAM Policy

Create a file named `s3-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::financial-reporting-raw-data",
        "arn:aws:s3:::financial-reporting-raw-data/*",
        "arn:aws:s3:::financial-reporting-processed-data",
        "arn:aws:s3:::financial-reporting-processed-data/*"
      ]
    }
  ]
}
```

Then create the policy:

```bash
aws iam create-policy --policy-name FinancialETLPolicy --policy-document file://s3-policy.json
```

Note the Policy ARN from the output, you'll need it in the next step.

#### Create IAM User for Application

```bash
# Create user
aws iam create-user --user-name financial-etl-app

# Attach policy
aws iam attach-user-policy --user-name financial-etl-app --policy-arn <POLICY_ARN_FROM_PREVIOUS_STEP>

# Create access key
aws iam create-access-key --user-name financial-etl-app
```

Save the AccessKeyId and SecretAccessKey from the output. You'll need these for configuration.

### 3. Configure Environment

Create a `.env` file:

```
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# S3 Configuration
S3_RAW_BUCKET=financial-reporting-raw-data
S3_PROCESSED_BUCKET=financial-reporting-processed-data

# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=financial

# Airflow Configuration
AIRFLOW_UID=50000
AIRFLOW__CORE__FERNET_KEY=your_fernet_key
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin_password

# API Keys
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
```

Generate a Fernet key for Airflow:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. Start the Infrastructure

```bash
# Build and start all services
docker-compose up -d

# Initialize Airflow
docker-compose exec airflow airflow db init
docker-compose exec airflow airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

### 5. Access Components

- Airflow: http://localhost:8080
- Metabase: http://localhost:3000
- PostgreSQL: localhost:5432

## Usage Guide

### Setting Up Financial Data Sources

1. **Configure Alpha Vantage API**
   - Sign up for a free API key at [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
   - Add your API key to the `.env` file

2. **Configure Additional APIs (optional)**
   - Update the `financial_api_to_s3.py` operator to include additional data sources
   - Add API keys to the `.env` file

### Running the ETL Pipeline

The pipeline is scheduled to run daily, but you can trigger it manually:

1. Open Airflow UI (http://localhost:8080)
2. Navigate to DAGs
3. Find the `financial_reporting_pipeline` DAG
4. Click "Trigger DAG"

### Creating Financial Dashboards

1. Open Metabase UI (http://localhost:3000)
2. Complete the initial setup
3. Connect to the PostgreSQL database
4. Create questions based on the financial data models
5. Build dashboards using those questions

Example dashboard setups:

- **Financial Overview Dashboard**
  - Income Statement Summary
  - Balance Sheet Summary
  - Key Financial Ratios
  - Profit Margin Trends

## Development

### Project Structure

```
financial-etl-cookbook/
├── docker-compose.yml          # Infrastructure definition
├── .env                        # Environment variables
├── dags/                       # Airflow DAGs
│   └── financial_reporting_dag.py
├── plugins/                    # Airflow custom plugins
│   └── operators/
│       └── financial_api_to_s3.py
├── dbt_project/                # dbt models
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   │   └── stg_financial_data.sql
│   │   └── marts/
│   │       ├── income_statement.sql
│   │       ├── balance_sheet.sql
│   │       └── financial_kpis.sql
│   └── macros/
│       └── financial_ratios.sql
├── metabase/                   # Metabase dashboards
│   └── dashboards/
│       └── financial_overview.json
└── docs/                       # Documentation
    └── images/
        └── architecture-diagram.png
```

### Customizing the DAGs

The main DAG is located at `dags/financial_reporting_dag.py`. To modify:

1. Update the list of companies or report types
2. Change the schedule interval
3. Add or remove processing steps

Example of adding a new processing step:

```python
# In financial_reporting_dag.py

# Add a new task
notify_completion = EmailOperator(
    task_id='notify_completion',
    to='finance@example.com',
    subject='Financial ETL Pipeline Completed',
    html_content='The financial reporting ETL pipeline has completed successfully.'
)

# Update dependencies
run_dbt_transformations >> notify_completion
```

### Adding New Financial Data Sources

To add a new financial data source:

1. Create a new operator in `plugins/operators/` or extend the existing one
2. Add the new data source to the DAG
3. Create corresponding dbt models

Example of adding a new data source:

```python
# Add to financial_reporting_dag.py

# New task for FRED data
extract_fred_data = FredApiToS3Operator(
    task_id='extract_fred_data',
    fred_series=['GDP', 'UNRATE', 'FEDFUNDS'],
    s3_bucket='{{ var.value.s3_raw_bucket }}',
    s3_key='fred_data/{{ ds }}',
)

# Update dependencies
extract_financial_data >> extract_fred_data >> create_tables
```

### Customizing dbt Models

The dbt models are located in `dbt_project/models/`. To customize:

1. Modify existing models or create new ones
2. Update the schema.yml file with descriptions
3. Create or modify macros for reusable SQL

Example of adding a new model:

```sql
-- Create models/marts/economic_indicators.sql
{{ config(materialized='table') }}

WITH fred_data AS (
    SELECT * FROM {{ ref('stg_fred_data') }}
)

SELECT
    date,
    series_id,
    value,
    CASE
        WHEN series_id = 'GDP' THEN 'Gross Domestic Product'
        WHEN series_id = 'UNRATE' THEN 'Unemployment Rate'
        WHEN series_id = 'FEDFUNDS' THEN 'Federal Funds Rate'
    END AS indicator_name
FROM fred_data
```

## Maintenance

### Daily Operations

- Monitor Airflow DAG runs for failures
- Check for API rate limiting issues
- Verify data freshness in dashboards

### Weekly Maintenance

- Review S3 storage usage
- Check for failed tasks in Airflow
- Back up the database

### Monthly Tasks

- Update API keys if needed
- Review and optimize dbt models
- Analyze database performance

### Data Retention

Configure S3 lifecycle policies to manage data retention:

```bash
# Create lifecycle policy for raw data (keep for 90 days, then move to Glacier)
aws s3api put-bucket-lifecycle-configuration \
    --bucket financial-reporting-raw-data \
    --lifecycle-configuration file://raw-lifecycle-policy.json
```

Example `raw-lifecycle-policy.json`:

```json
{
  "Rules": [
    {
      "ID": "Move to Glacier after 90 days",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

## Troubleshooting

### Common Issues

#### Airflow DAG Not Running
- Check that the DAG is enabled in the Airflow UI
- Ensure all required connections are configured
- Check for syntax errors in the DAG file

#### API Rate Limiting
- Alpha Vantage free tier has a limit of 5 API calls per minute and 500 per day
- Implement exponential backoff in the API operator
- Consider using a paid API tier for production

#### S3 Access Issues
- Verify IAM permissions are correctly configured
- Check that the AWS credentials are correctly set in the environment
- Ensure S3 bucket names are correct in the configuration

#### Database Connection Issues
- Verify the database is running
- Check connection strings in the Airflow connection settings
- Ensure the database user has appropriate permissions

### Logs and Debugging

- Airflow logs: Available in the Airflow UI or in `./logs/dag_id/task_id/`
- Container logs: `docker-compose logs -f [service_name]`
- PostgreSQL logs: `docker-compose logs -f postgres`

## Contributing

We welcome contributions to improve this cookbook!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Quick Reference

### URLs
- Airflow: http://localhost:8080
- Metabase: http://localhost:3000

### Docker Commands
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Execute command in a container
docker-compose exec [service_name] [command]
```

### Airflow Commands
```bash
# Create a connection
docker-compose exec airflow airflow connections add 's3_conn' \
    --conn-type 's3' \
    --conn-extra '{"aws_access_key_id":"your_access_key", "aws_secret_access_key":"your_secret_key", "region_name":"us-east-1"}'

# List DAGs
docker-compose exec airflow airflow dags list

# Trigger a DAG
docker-compose exec airflow airflow dags trigger financial_reporting_pipeline
```

### dbt Commands
```bash
# Run dbt models
docker-compose exec dbt dbt run

# Generate documentation
docker-compose exec dbt dbt docs generate

# Test models
docker-compose exec dbt dbt test
```
