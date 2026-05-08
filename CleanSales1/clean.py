"""
CleanSales1 — Cleaning Logic

Pipeline for source-1 sales data:
  1. Read the raw CSV from Azure Blob Storage into a pandas DataFrame.
  2. Group by (names, region) and sum numeric columns (units, price).
  3. Filter to a single region ('east').
  4. Write the cleaned CSV back to a different blob container.

Why keep this in a separate file from __init__.py?
  - __init__.py is wiring/routing; clean.py is pure data logic.
  - Makes unit-testing the cleaning logic trivial (no Azure SDK mocking needed).
"""

import logging
import os
from io import StringIO

import pandas as pd
from azure.storage.blob import BlobServiceClient

# ---------------------------------------------------------------------------
# Azure Blob configuration — values come from Application Settings / local.settings.json
# ---------------------------------------------------------------------------
_blob_account_name = os.getenv("BlobAccountName")
_blob_account_key = os.getenv("BlobAccountKey")
_out_container = os.getenv("C1", "c1raw")  # container where cleaned file is written

_connection_string = f"DefaultEndpointsProtocol=https;AccountName={_blob_account_name};AccountKey={_blob_account_key};EndpointSuffix=core.windows.net"
_blob_service_client = BlobServiceClient.from_connection_string(_connection_string)

TARGET_REGION = "east"  # Only keep rows for this region after aggregation


def clean(event_body: list) -> str:
    """
    Entry point called by __init__.py.

    Parameters
    ----------
    event_body : list
        Parsed JSON body of the Event Grid BlobCreated event.

    Returns
    -------
    str
        "Success" on completion, "Error" on any failure.
    """
    try:
        blob_url = event_body[0]["data"]["url"]
        df, filename = _read_blob_to_dataframe(blob_url)
        _clean_and_upload(df, filename)
        return "Success"
    except Exception as exc:
        logging.error("CleanSales1.clean() failed: %s", exc)
        return "Error"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _read_blob_to_dataframe(blob_url: str):
    """
    Parse the blob URL to extract the container name and filename,
    download the blob as text, and load it into a pandas DataFrame.

    Example URL:
        https://<account>.blob.core.windows.net/c1raw/s1_raw.csv
        → container = 'c1raw', filename = 's1_raw.csv'
    """
    filename = blob_url.rsplit("/", 1)[-1]
    container = blob_url.rsplit("/", 2)[-2]

    logging.info("CleanSales1: reading blob '%s' from container '%s'", filename, container)
    blob_client = _blob_service_client.get_blob_client(container=container, blob=filename)
    blob_content = blob_client.download_blob().readall().decode("utf-8")

    df = pd.read_csv(StringIO(blob_content))
    logging.info("CleanSales1: loaded %d rows, %d columns", len(df), len(df.columns))
    return df, filename


def _clean_and_upload(df: pd.DataFrame, original_filename: str) -> None:
    """
    Apply cleaning transformations and write the result back to blob storage.

    Transformations
    ---------------
    1. Group by (names, region) → sum units and price per name/region pair.
    2. Filter rows where region == TARGET_REGION.
    3. Drop the extra RangeIndex column added by reset_index().
    """
    # Aggregate: one row per (name, region) combination
    aggregated = (
        df.groupby(["names", "region"], as_index=False)[["units", "price"]]
        .sum()
    )

    # Keep only the target region
    filtered = aggregated[aggregated["region"] == TARGET_REGION].copy()

    logging.info(
        "CleanSales1: %d rows after groupby; %d rows after filtering to region='%s'",
        len(aggregated), len(filtered), TARGET_REGION,
    )

    # Serialise and upload
    out_csv = filtered.to_csv(index=False)
    out_filename = f"cleaned_{original_filename}"

    blob_client = _blob_service_client.get_blob_client(container=_out_container, blob=out_filename)
    blob_client.upload_blob(out_csv, overwrite=True)
    logging.info("CleanSales1: uploaded '%s' to container '%s'", out_filename, _out_container)
