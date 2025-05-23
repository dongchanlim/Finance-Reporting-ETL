from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from data_loader.fetch_data import fetch_financial_data

default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
}

with DAG("financial_etl_dag",
         default_args=default_args,
         schedule_interval="@daily",
         catchup=False) as dag:

    fetch_task = PythonOperator(
        task_id="fetch_financial_data",
        python_callable=fetch_financial_data,
    )

    fetch_task
