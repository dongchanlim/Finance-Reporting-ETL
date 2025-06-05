# Financial Reporting ETL Pipeline

A cost-optimized AWS S3 + open-source analytical pipeline for financial reporting.

![Infrastructure Diagram](docs/images/infrastructure.png)

## Overview

This repository provides a complete solution for building an analytical ETL pipeline for financial reporting. It leverages AWS S3 for storage while using open-source technologies for processing and analysis to optimize costs.

## Tech Stack

| Component | Technology | Monthly Cost | Notes |
|-----------|------------|--------------|-------|
| Data Storage | AWS S3 | ~$2 | Cost-effective object storage |
| Orchestration | Apache Airflow | ~$0* | Self-hosted or managed |
| Transformation | Python + dbt | $0 | Open-source tools |
| Data Warehouse | PostgreSQL + TimescaleDB | ~$0* | Self-hosted open-source database |
| Data Sources | Public Financial APIs | $0 | Alpha Vantage, Yahoo Finance, etc. |
| Reporting | Metabase | $0 | Open-source BI tool |

*Hosting costs depend on deployment choice: self-hosted, cloud VM ($5-20/month), or existing infrastructure

## Architecture Overview

The pipeline follows these stages:

1. **Extraction**: Collect financial data from public APIs
2. **Storage**: Store raw data in AWS S3
3. **Transformation**: Process data using Airflow and Python
4. **Loading**: Move processed data to TimescaleDB
5. **Modeling**: Apply business transformations with dbt
6. **Visualization**: Create dashboards with Metabase

## Getting Started

### Prerequisites

- AWS Account with S3 access
- Docker and Docker Compose
- Git
- Python 3.8+

### Quick Start

```bash
# Clone this repository
git clone https://github.com/yourusername/financial-etl-pipeline.git
cd financial-etl-pipeline

# Set up AWS credentials
aws configure

# Create S3 buckets
aws s3 mb s3://financial-reporting-raw
aws s3 mb s3://financial-reporting-processed

# Configure environment variables
cp .env.example .env
# Edit .env with your AWS keys and other configurations

# Start the infrastructure
docker-compose up -d
```

## Project Structure

```
financial-etl-pipeline/
├── docker-compose.yml             # Container orchestration
├── dags/                          # Airflow DAGs
│   └── financial_reporting_dag.py
├── plugins/                       # Airflow custom plugins
│   └── operators/
│       └── financial_api_to_s3.py
├── dbt_project/                   # dbt models
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
├── metabase/                      # Metabase dashboards
│   └── dashboards/
│       └── financial_overview.json
└── docs/                          # Documentation
    └── images/
        └── infrastructure.png
```

## Implementation Guide

### 1. AWS S3 Setup

Create two S3 buckets: one for raw data and one for processed data.

```bash
aws s3 mb s3://financial-reporting-raw
aws s3 mb s3://financial-reporting-processed
```

Set up a dedicated IAM user for the pipeline:

```bash
aws iam create-user --user-name financial-etl-user
aws iam attach-user-policy --user-name financial-etl-user --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam create-access-key --user-name financial-etl-user
```

Save the access key and secret key in your `.env` file.

### 2. Docker Infrastructure

The provided `docker-compose.yml` sets up:

- PostgreSQL with TimescaleDB extension
- Apache Airflow webserver and scheduler
- dbt for data transformations
- Metabase for dashboards

```yaml
version: '3'

services:
  # PostgreSQL with TimescaleDB
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: financial
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Apache Airflow
  airflow:
    image: apache/airflow:2.5.0
    depends_on:
      - timescaledb
    ports:
      - "8080:8080"
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://postgres:postgres@timescaledb:5432/airflow
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
    volumes:
      - ./dags:/opt/airflow/dags
      - ./plugins:/opt/airflow/plugins
      - ./logs:/opt/airflow/logs
    command: bash -c "airflow db init && airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com && airflow webserver & airflow scheduler"

  # dbt service
  dbt:
    build:
      context: ./dbt_project
      dockerfile: Dockerfile
    depends_on:
      - timescaledb
    volumes:
      - ./dbt_project:/usr/app
    environment:
      - DBT_PROFILES_DIR=/usr/app
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
    command: /bin/bash -c "tail -f /dev/null"  # Keep container running
    
  # Metabase
  metabase:
    image: metabase/metabase:latest
    ports:
      - "3000:3000"
    environment:
      MB_DB_TYPE: postgres
      MB_DB_DBNAME: metabase
      MB_DB_PORT: 5432
      MB_DB_USER: postgres
      MB_DB_PASS: postgres
      MB_DB_HOST: timescaledb
    depends_on:
      - timescaledb

volumes:
  postgres_data:
```

### 3. Airflow DAG Implementation

The Airflow DAG orchestrates the entire pipeline:

```python
# dags/financial_reporting_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.amazon.aws.transfers.s3_to_sql import S3ToSqlOperator
from airflow.operators.bash import BashOperator
from plugins.operators.financial_api_to_s3 import FinancialApiToS3Operator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define companies and financial data types to fetch
companies = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
report_types = ['income_statement', 'balance_sheet', 'cash_flow']

with DAG(
    'financial_reporting_pipeline',
    default_args=default_args,
    description='A pipeline to extract, transform and load financial data',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['financial'],
) as dag:

    # Task to extract data from financial API and store in S3
    extract_financial_data = FinancialApiToS3Operator(
        task_id='extract_financial_data',
        companies=companies,
        report_types=report_types,
        s3_bucket='financial-reporting-raw',
        s3_key='financial_data/{{ ds }}',
    )

    # Create tables in TimescaleDB
    create_tables = PostgresOperator(
        task_id='create_tables',
        postgres_conn_id='postgres_default',
        sql="""
        CREATE TABLE IF NOT EXISTS raw_financial_data (
            symbol VARCHAR(10),
            report_type VARCHAR(20),
            fiscal_date DATE,
            currency VARCHAR(5),
            total_revenue NUMERIC(18,2),
            gross_profit NUMERIC(18,2),
            operating_income NUMERIC(18,2),
            net_income NUMERIC(18,2),
            total_assets NUMERIC(18,2),
            total_liabilities NUMERIC(18,2),
            total_equity NUMERIC(18,2),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        
        SELECT create_hypertable('raw_financial_data', 'created_at', if_not_exists => TRUE);
        """
    )

    # Task to load data from S3 to TimescaleDB
    load_to_timescaledb = S3ToSqlOperator(
        task_id='load_to_timescaledb',
        s3_bucket='financial-reporting-raw',
        s3_key='financial_data/{{ ds }}',
        dest_table='raw_financial_data',
        postgres_conn_id='postgres_default',
    )

    # Task to run dbt transformations
    run_dbt_transformations = BashOperator(
        task_id='run_dbt_transformations',
        bash_command='docker-compose exec -T dbt dbt run --profiles-dir /usr/app',
    )

    # Define task dependencies
    extract_financial_data >> create_tables >> load_to_timescaledb >> run_dbt_transformations
```

### 4. Custom S3 Operator

Create a custom operator for extracting financial data to S3:

```python
# plugins/operators/financial_api_to_s3.py
import json
import requests
import pandas as pd
import io
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

class FinancialApiToS3Operator(BaseOperator):
    """
    Operator to extract financial data from API and upload to S3
    """
    
    @apply_defaults
    def __init__(
        self,
        companies,
        report_types,
        s3_bucket,
        s3_key,
        api_key='demo',  # Using Alpha Vantage demo key (limited requests)
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.companies = companies
        self.report_types = report_types
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.api_key = api_key
        
    def execute(self, context):
        s3_hook = S3Hook()
        
        for company in self.companies:
            for report_type in self.report_types:
                self.log.info(f"Extracting {report_type} for {company}")
                
                # Call Alpha Vantage API to get financial data
                if report_type == 'income_statement':
                    function = 'INCOME_STATEMENT'
                elif report_type == 'balance_sheet':
                    function = 'BALANCE_SHEET'
                elif report_type == 'cash_flow':
                    function = 'CASH_FLOW'
                
                url = f"https://www.alphavantage.co/query?function={function}&symbol={company}&apikey={self.api_key}"
                response = requests.get(url)
                data = response.json()
                
                # Convert to DataFrame for easier processing
                if 'annualReports' in data:
                    df = pd.DataFrame(data['annualReports'])
                    df['symbol'] = company
                    df['report_type'] = report_type
                    
                    # Save to CSV file
                    csv_data = df.to_csv(index=False)
                    
                    # Upload to S3
                    s3_hook.load_string(
                        string_data=csv_data,
                        key=f"{self.s3_key}/{company}_{report_type}.csv",
                        bucket_name=self.s3_bucket,
                        replace=True
                    )
                    
                    self.log.info(f"Uploaded {report_type} for {company} to S3")
                else:
                    self.log.warning(f"No data found for {company} {report_type}")
                    
                # Respect API rate limits
                import time
                time.sleep(15)  # Alpha Vantage free tier has limitations
```

### 5. dbt Setup

Configure dbt for transforming financial data:

**profiles.yml**:
```yaml
financial:
  target: dev
  outputs:
    dev:
      type: postgres
      host: timescaledb
      user: postgres
      password: postgres
      port: 5432
      dbname: financial
      schema: public
      threads: 4
```

**dbt_project.yml**:
```yaml
name: 'financial_reporting'
version: '1.0.0'
config-version: 2

profile: 'financial'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  financial_reporting:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

Example models:

**models/staging/stg_financial_data.sql**:
```sql
{{ config(materialized='view') }}

WITH source AS (
    SELECT 
        symbol,
        report_type,
        fiscal_date,
        currency,
        total_revenue,
        gross_profit,
        operating_income,
        net_income
    FROM raw_financial_data
    WHERE report_type = 'income_statement'
),

balance_sheet AS (
    SELECT 
        symbol,
        fiscal_date,
        total_assets,
        total_liabilities,
        total_equity
    FROM raw_financial_data
    WHERE report_type = 'balance_sheet'
)

SELECT
    s.symbol,
    s.fiscal_date,
    s.currency,
    s.total_revenue,
    s.gross_profit,
    s.operating_income,
    s.net_income,
    b.total_assets,
    b.total_liabilities,
    b.total_equity
FROM source s
LEFT JOIN balance_sheet b
    ON s.symbol = b.symbol
    AND s.fiscal_date = b.fiscal_date
```

**models/marts/financial_kpis.sql**:
```sql
{{ config(materialized='table') }}

WITH financial_data AS (
    SELECT * FROM {{ ref('stg_financial_data') }}
)

SELECT
    symbol,
    fiscal_date,
    currency,
    total_revenue,
    net_income,
    gross_profit,
    operating_income,
    total_assets,
    total_liabilities,
    total_equity,
    
    -- Calculate financial KPIs
    {{ calculate_profit_margin('gross_profit', 'total_revenue') }} AS gross_profit_margin,
    {{ calculate_profit_margin('operating_income', 'total_revenue') }} AS operating_profit_margin,
    {{ calculate_profit_margin('net_income', 'total_revenue') }} AS net_profit_margin,
    {{ calculate_return_on_assets('net_income', 'total_assets') }} AS return_on_assets,
    {{ calculate_return_on_equity('net_income', 'total_equity') }} AS return_on_equity,
    (total_assets / NULLIF(total_liabilities, 0)) AS asset_to_liability_ratio
FROM financial_data
```

### 6. Metabase Setup

1. Access Metabase at http://localhost:3000
2. Connect to your TimescaleDB instance
3. Create questions based on the dbt models
4. Build dashboards for financial reporting

## Cost Analysis

| Component | AWS Solution | Hybrid Solution | Monthly Savings |
|-----------|-------------|-----------------|----------------|
| Storage | S3 (~$2) | S3 (~$2) | $0 |
| Data Warehouse | Redshift (~$180) | PostgreSQL + TimescaleDB (~$0*) | ~$180 |
| Orchestration | EC2 for Airflow (~$30) | Self-hosted Airflow (~$0*) | ~$30 |
| **Total** | **~$212/month** | **~$2/month** + hosting | **~$210/month** |

*Hosting costs depend on deployment choice

## Deployment Options

### 1. Local Development
Run the entire stack on your local machine for development.

### 2. Self-Hosted Server
Deploy on an on-premises server or a single cloud VM.

**Estimated costs**: 
- Small VM (4GB RAM): ~$20/month
- Medium VM (8GB RAM): ~$40/month

### 3. Hybrid Cloud
Use AWS S3 for storage but host processing components yourself.

## Maintenance and Operations

### Daily Tasks
- Monitor Airflow DAG runs
- Check for API rate limiting issues
- Verify data freshness in dashboards

### Weekly Tasks
- Check disk space usage
- Review logs for errors
- Backup database and configurations

### Monthly Tasks
- Update API keys if needed
- Apply system updates
- Review and optimize performance

## Extending the Solution

### Adding New Data Sources
1. Create a new operator in Airflow plugins
2. Add new models in dbt
3. Update dashboards in Metabase

### Scaling Up
For larger datasets:
1. Increase server resources
2. Consider partitioning data in TimescaleDB
3. Implement incremental loading in dbt models

## Troubleshooting

### Common Issues

**API Rate Limiting**
- Use multiple API keys
- Implement retry logic with backoff
- Stagger API requests

**S3 Access Issues**
- Verify IAM permissions
- Check AWS credentials in environment variables
- Test connection with `aws s3 ls`

**Pipeline Failures**
- Check Airflow logs
- Verify database connections
- Test API connectivity

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
