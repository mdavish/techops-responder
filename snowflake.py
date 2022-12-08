import logging
from typing import Optional
from rich.logging import RichHandler

logging.basicConfig(
    level="INFO", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)
LOGGER = logging.getLogger(__name__)

import os
import pandas as pd
from snowflake.connector import SnowflakeConnection, connect
from snowflake.connector.errors import DatabaseError


def connect_to_snowflake(
    snowflake_user: str = None,
    snowflake_pass: str = None,
    warehouse: str = "HUMAN_WH",
    snowflake_acct: str = "tw61901.us-east-1",
) -> SnowflakeConnection:
    """
    Connecting can take three paths:
    1. If on Nomad, connect directly with the Nomad Credentials
       YEXT_DB_DATA_HUB_PASSWORD and YEXT_DB_DATA_HUB_USERNAME
    2. Else if on other machine in network (e.g. EC2), then
       connect directly with the standard credentials
       SNOWFLAKE_USER and SNOWFLAKE_PASS
    3. Else, use browser authentication, which also requires
       SNOWFLAKE_USER and SNOWFLAKE_PASS
    """
    snowflake_user = os.getenv("YEXT_DB_DATA_HUB_USERNAME")
    snowflake_pass = os.getenv("YEXT_DB_DATA_HUB_PASSWORD")
    if snowflake_user and snowflake_pass:
        logging.info("Connecting to Snowflake with Nomad Credentials")
        conn = connect(
            user=snowflake_user,
            password=snowflake_pass,
            account=snowflake_acct,
            warehouse=warehouse,
        )
        return conn

    snowflake_user = os.getenv("SNOWFLAKE_USER")
    snowflake_pass = os.getenv("SNOWFLAKE_PASS")
    if snowflake_user and snowflake_pass:
        logging.info("Connecting to Snowflake with Standard Credentials")
        try:
            conn = connect(
                user=snowflake_user,
                password=snowflake_pass,
                account=snowflake_acct,
                warehouse=warehouse,
            )
            return conn
        except DatabaseError:
            logging.info("Standard Credentials Failed, Trying Browser Auth")
            logging.info("Connecting to Snowflake with Browser Auth")
            conn = connect(
                user=snowflake_user,
                account=snowflake_acct,
                warehouse=warehouse,
                authenticator="externalbrowser",
            )
            return conn
    else:
        raise ValueError("Missing Snowflake credentials")


def get_data_from_snowflake(
    query: str, conn: Optional[SnowflakeConnection] = None
) -> pd.DataFrame:

    if not conn:
        conn = connect_to_snowflake()

    df = pd.read_sql(query, conn)
    df = df.rename(str.lower, axis="columns")

    return df
