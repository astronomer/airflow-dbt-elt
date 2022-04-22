# ELT with Airflow and dbt
This repo contains DAGs to demonstrate a variety of ELT patterns using Airflow along with dbt.
All DAGs can be found under the `dags/` folder, which is partitioned by dbt Core and dbt Cloud use. Specific
data stores need connections and may require accounts with cloud providers. Further details are provided in
the data store specific sections below.

## Requirements
The Astronomer CLI and Docker installed locally are needed to run all DAGs in this repo.

## Getting Started
The easiest way to run these example DAGs is to use the Astronomer CLI to get an Airflow instance up and
running locally:
1. [Install the Astronomer CLI](https://www.astronomer.io/docs/cloud/stable/develop/cli-quickstart).
2. Clone this repo locally and navigate into it.
3. Start Airflow locally by running `astro dev start`.
4. Create all necessary connections and variables - see below for specific DAG cases.
5. Navigate to localhost:8080 in your browser and you should see the tutorial DAGs there.

## dbt Cloud

To create a connection to dbt Cloud, navigate to `Admin -> Connections` in the Airflow UI and select the
"dbt Cloud" connection type. An API token is required, however, the Account ID is not. You may provide an
Account ID and this will be used by the dbt Cloud tasks, but you can also override or supply a specific
Account ID at the task level using the `account_id` parameter if you wish.

### DAGs
All dbt Cloud DAGs used the following dbt Cloud provider version:

```
    apache-airflow-providers-dbt-cloud==1.0.1
```
This provider version uses dbt Cloud API v2.


#### Add a Simple Operational Check for dbt Cloud Jobs

This example showcases an example of adding an operational check to ensure the dbt Cloud job is not running
prior to triggering. The `DbtCloudHook` provides a `list_job_runs()` method which can be used to retrieve the
latest triggered run for a job and check the status of said run. If the job is not in a state of 10 (Success),
20 (Error), or 30 (Cancelled), the pipeline will not try to trigger it.

This pipeline requires a connection to dbt Cloud as well as an Airflow Variable for the ``job_id`` to be
triggered.

#### Salesforce ELT with Fivetran, dbt Cloud, and Census

This example showcases how a modern ELT pipeline can be created for extracting and loading Salesforce data
into a data warehouse with Fivetran, performing data transformations via a dbt Cloud job, and finally
reverse-syncing the transformed data back to a marketing platform using Census.

This pipeline requires connections to Fivetran, dbt Cloud, and Census as well as an Airflow Variable for the
`connector_id` to be used in the Fivetran extract.

To create a connection to Fivetran, navigate to `Admin -> Connections` in the Airflow UI and select the
"Fivetran" connection type. Provide your Fivetran API key and secret.

To create a connection to Census, navigate to `Admin -> Connections` in the Airflow UI and select the
"Census" connection type. Provide your Census secret token.

Additional Airflow provider packages are required for this DAG:
```
    airflow-provider-census==1.1.1
    airflow-provider-fivetran==1.0.3
```

## dbt Core
### DAGs
#### Rerun dbt Models from Failure

This example shows how you can use the new `dbt build +=` command to rerun a model from the point of failure.
By defining the new command as a downstream dependency of the `dbt run` command, you can rerun your dbt model
from the point of failure if it fails.

Furthermore, you can use trigger rules to avoid redundant task runs and ensure that your downstream tasks as
intended. In this case, we suppose that after the dbt models are successfully built, the data is sent to
Salesforce using Hightouch.

This pipeline assumes that you are using dbt Core with the `BashOperator`.

### Project Setup

We are currently using [the jaffle_shop sample dbt project](https://github.com/dbt-labs/jaffle_shop).
The only files required for the Airflow DAGs to run are `dbt_project.yml`, `profiles.yml` and
`target/manifest.json`, but we included the models for completeness. If you would like to try these DAGs with
your own dbt workflow, feel free to drop in your own project files.

### Additional Notes
- If you make changes to the dbt project, you will need to run `dbt compile` in order to update the
`manifest.json` file. This may be done manually during development, as part of a CI/CD pipeline, or as a
separate step in a production pipeline run *before* the Airflow DAG is triggered.
- The sample dbt project contains the `profiles.yml`, which is configured to use environment variables. The
database credentials from an Airflow connection are passed as environment variables to the `BashOperator`
tasks running the dbt commands.
- Each DAG runs a `dbt_seed` task at the beginning that loads sample data into the database. This is
simply for the purpose of this demo.
