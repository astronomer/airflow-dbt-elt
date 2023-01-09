"""
### Salesforce ELT with Fivetran, dbt Cloud, and Census

This example showcases how a modern ELT pipeline can be created for extracting and loading Salesforce data
into a data warehouse with Fivetran, performing data transformations via a dbt Cloud job, and finally
reverse-syncing the transformed data back to a marketing platform using Census.

#### Getting Started

This pipeline requires connections to Fivetran, dbt Cloud, and Census as well as an Airflow Variable for the
`connector_id` to be used in the Fivetran extract.

##### Fivetran
To create a connection to Fivetran, navigate to `Admin -> Connections` in the Airflow UI and select the
"Fivetran" connection type. Provide your Fivetran API key and secret.


##### dbt Cloud
To create a connection to dbt Cloud, navigate to `Admin -> Connections` in the Airflow UI and select the
"dbt Cloud" connection type. An API token is required, however, the Account ID is not. You may provide an
Account ID and this will be used by the dbt Cloud tasks, but you can also override or supply a specific
Account ID at the task level using the `account_id` parameter if you wish.

##### Census
To create a connection to Census, navigate to `Admin -> Connections` in the Airflow UI and select the
"Census" connection type. Provide your Census secret token.

#### Provider Details
For reference, the following provider versions were used when intially authoring this pipeline:

```
    airflow-provider-census==1.1.1
    apache-airflow-providers-dbt-cloud==1.0.1
    airflow-provider-fivetran-async==1.0.0a4
```
"""

from pendulum import datetime
from datetime import timedelta

from airflow_provider_census.operators.census import CensusOperator
from airflow_provider_census.sensors.census import CensusSensor
from fivetran_provider_async.operators import FivetranOperatorAsync

from airflow.decorators import dag
from airflow.operators.empty import EmptyOperator
from airflow.providers.dbt.cloud.operators.dbt import DbtCloudRunJobOperator
from airflow.providers.dbt.cloud.sensors.dbt import DbtCloudJobRunSensor
from airflow.utils.task_group import TaskGroup


@dag(
    start_date=datetime(2022, 2, 9),
    schedule_interval="@daily",
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=3)},
    default_view="graph",
    doc_md=__doc__,
)
def modern_elt():
    begin = EmptyOperator(task_id="begin")
    end = EmptyOperator(task_id="end")

    with TaskGroup(
        group_id="extract_and_load",
        prefix_group_id=False,
        default_args={
            "fivetran_conn_id": "fivetran",
            "connector_id": "{{ var.value.salesforce_connector_id }}",
        },
    ) as extract_and_load:
        extract_salesforce = FivetranOperatorAsync(
            task_id="extract_salesforce_with_async_poll",
            poll_frequency=300,
        )

    with TaskGroup(
        group_id="transform", prefix_group_id=False, default_args={"dbt_cloud_conn_id": "dbt_cloud"}
    ) as transform:
        transform_salesforce_dw = DbtCloudRunJobOperator(
            task_id="transform_salesforce_dw",
            job_id=26746,
            wait_for_termination=False,
            additional_run_config={"threads_override": 8},
        )

        wait_for_dw_transformations = DbtCloudJobRunSensor(
            task_id="wait_for_dw_transformations",
            run_id=transform_salesforce_dw.output,
            poke_interval=600,
            timeout=3600,
        )

    with TaskGroup(
        group_id="reverse_sync", prefix_group_id=False, default_args={"census_conn_id": "census"}
    ) as reverse_sync:
        sync_to_marketing_platform = CensusOperator(task_id="sync_to_marketing_platform", sync_id=9384)

        wait_for_reverse_sync = CensusSensor(
            task_id="wait_for_reverse_sync",
            sync_run_id=sync_to_marketing_platform.output,
            poke_interval=30,
        )

    begin >> extract_and_load >> transform >> reverse_sync >> end


dag = modern_elt()
