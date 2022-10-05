"""
### Add a Simple Operational Check for dbt Cloud Jobs

This example showcases an example of adding an operational check to ensure the dbt Cloud job is not running
prior to triggering. The `DbtCloudHook` provides a `list_job_runs()` method which can be used to retrieve the
latest triggered run for a job and check the status of said run. If the job is not in a state of 10 (Success),
20 (Error), or 30 (Cancelled), the pipeline will not try to trigger it.

#### Getting Started

This pipeline requires a connection to dbt Cloud as well as an Airflow Variable for the ``job_id`` to be
triggered.

To create a connection to dbt Cloud, navigate to `Admin -> Connections` in the Airflow UI and select the
"dbt Cloud" connection type. An API token is required, however, the Account ID is not. You may provide an
Account ID and this will be used by the dbt Cloud tasks, but you can also override or supply a specific
Account ID at the task level using the `account_id` parameter if you wish.

#### Provider Details
For reference, the following provider version was used when intially authoring this pipeline:

```
    apache-airflow-providers-dbt-cloud==1.0.1
```
This provider version uses dbt Cloud API v2.
"""

from pendulum import datetime

from airflow.decorators import dag
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import ShortCircuitOperator
from airflow.providers.dbt.cloud.hooks.dbt import DbtCloudHook, DbtCloudJobRunStatus
from airflow.providers.dbt.cloud.operators.dbt import DbtCloudRunJobOperator
from airflow.utils.edgemodifier import Label


DBT_CLOUD_CONN_ID = "dbt"
JOB_ID = "{{ var.value.dbt_cloud_job_id }}"


def _check_job_not_running(job_id):
    """
    Retrieves the last run for a given dbt Cloud job and checks to see if the job is not currently running.
    """
    hook = DbtCloudHook(DBT_CLOUD_CONN_ID)
    runs = hook.list_job_runs(job_definition_id=job_id, order_by="-id")
    latest_run = runs[0].json()["data"][0]

    return DbtCloudJobRunStatus.is_terminal(latest_run["status"])


@dag(
    start_date=datetime(2022, 2, 10),
    schedule_interval="@daily",
    catchup=False,
    default_view="graph",
    doc_md=__doc__,
)
def check_before_running_dbt_cloud_job():
    begin, end = [DummyOperator(task_id=id) for id in ["begin", "end"]]

    check_job = ShortCircuitOperator(
        task_id="check_job_is_not_running",
        python_callable=_check_job_not_running,
        op_kwargs={"job_id": JOB_ID},
    )

    trigger_job = DbtCloudRunJobOperator(
        task_id="trigger_dbt_cloud_job",
        dbt_cloud_conn_id=DBT_CLOUD_CONN_ID,
        job_id=JOB_ID,
        check_interval=600,
        timeout=3600,
    )

    begin >> check_job >> Label("Job not currently running. Proceeding.") >> trigger_job >> end


dag = check_before_running_dbt_cloud_job()
