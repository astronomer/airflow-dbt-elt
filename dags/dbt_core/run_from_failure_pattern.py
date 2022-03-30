"""
### Rerun dbt Models from Failure

This example shows how you can use the new `dbt build +=` command to rerun a model from the point of failure.
By defining the new command as a downstream dependency of the `dbt run` command, you can rerun your dbt model
from the point of failure if it fails.

Furthermore, you can use trigger rules to avoid redundant task runs and ensure that your downstream tasks as
intended. In this case, we suppose that after the dbt models are successfully built, the data is sent to
Salesforce using Hightouch.

This pipeline assumes that you are using dbt Core with the `BashOperator`.
"""
from datetime import timedelta
from pendulum import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow_provider_hightouch.operators.hightouch import HightouchTriggerSyncOperator
from airflow.utils.edgemodifier import Label
from airflow.utils.trigger_rule import TriggerRule


# We're hardcoding the project directory value here for the purpose of the demo, but in a production
# environment this would probably come from a config file and/or environment variables!
DBT_PROJECT_DIR = "/usr/local/airflow/include/dbt"

DBT_ENV = {
    "DBT_USER": "{{ conn.postgres.login }}",
    "DBT_ENV_SECRET_PASSWORD": "{{ conn.postgres.password }}",
    "DBT_HOST": "{{ conn.postgres.host }}",
    "DBT_SCHEMA": "{{ conn.postgres.schema }}",
    "DBT_PORT": "{{ conn.postgres.port }}",
}


dag = DAG(
    "dbt_run_from_failure",
    start_date=datetime(2022, 3, 14),
    default_args={"owner": "astronomer", "email_on_failure": False},
    description="A sample Airflow DAG that shows how to use the new dbt+= command with trigger rules.",
    schedule_interval=None,
    catchup=False,
    doc_md=__doc__,
)

with dag:
    # This task loads the CSV files from dbt/data into the local Postgres database for the purpose of this demo.
    # In practice, we'd usually expect the data to have already been loaded to the database.
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"dbt seed --full-refresh --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        env=DBT_ENV,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"dbt run --profiles-dir {DBT_PROJECT_DIR} --project-dir {DBT_PROJECT_DIR}",
        env=DBT_ENV,
    )

    # Fill in the previous state artifacts needed to run from this point.
    dbt_build_rerun = BashOperator(
        task_id="dbt_build_rerun",
        bash_command=f"dbt build --select result:error+ --defer --state <path/to/previous_state_artifacts>",
        env=DBT_ENV,
        trigger_rule=TriggerRule.ALL_FAILED,
    )

    # Due to the ONE_SUCCESS rule, if one of the two upstream tasks succeed, this task will run.
    sync_data_to_salesforce = HightouchTriggerSyncOperator(
        task_id="sync_data_to_salesforce",
        connection_id="hightouch",
        sync_id=21,
        synchronous=True,
        trigger_rule=TriggerRule.ONE_SUCCESS,
    )

    # Explicitly setting this task as dependent on both upstream tasks.
    dbt_seed >> dbt_run >> Label("Only if dbt run fails") >> dbt_build_rerun >> sync_data_to_salesforce
    dbt_run >> Label("If it succeeds") >> sync_data_to_salesforce
