"""
CleanSales2 — Cleaning Logic

Pipeline for source-2 sales data:
  1. Read raw CSV from the c2raw blob container.
  2. Group by (names, item) and sum units and price.
  3. Filter to a single item type ('binder').
  4. Upload the cleaned CSV back to blob storage.
"""

import logging
import os
from io import StringIO

import pandas as pd
from azure.storage.blob import BlobServiceClient

_blob_account_name = os.getenv("BlobAccountName")
_blob_account_key = os.getenv("BlobAccountKey")
_out_container = os.getenv("C2", "c2raw")

_connection_string = f"DefaultEndpointsProtocol=https;AccountName={_blob_account_name};AccountKey={_blob_account_key};EndpointSuffix=core.windows.net"
_blob_service_client = BlobServiceClient.from_connection_string(_connection_string)

TARGET_ITEM = "binder"  # Only keep rows for this item type after aggregation


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
        logging.error("CleanSales2.clean() failed: %s", exc)
        return "Error"


def _read_blob_to_dataframe(blob_url: str):
    """Download blob and return a (DataFrame, filename) tuple."""
    filename = blob_url.rsplit("/", 1)[-1]
    container = blob_url.rsplit("/", 2)[-2]

    logging.info("CleanSales2: reading blob '%s' from container '%s'", filename, container)
    blob_client = _blob_service_client.get_blob_client(container=container, blob=filename)
    blob_content = blob_client.download_blob().readall().decode("utf-8")

    df = pd.read_csv(StringIO(blob_content))
    logging.info("CleanSales2: loaded %d rows, %d columns", len(df), len(df.columns))
    return df, filename


def _clean_and_upload(df: pd.DataFrame, original_filename: str) -> None:
    """
    Apply cleaning transformations and write the result back to blob storage.

    Transformations
    ---------------
    1. Group by (names, item) → sum units and price per name/item pair.
    2. Filter rows where item == TARGET_ITEM.
    """
    aggregated = (
        df.groupby(["names", "item"], as_index=False)[["units", "price"]]
        .sum()
    )

    filtered = aggregated[aggregated["item"] == TARGET_ITEM].copy()

    logging.info(
        "CleanSales2: %d rows after groupby; %d rows after filtering to item='%s'",
        len(aggregated), len(filtered), TARGET_ITEM,
    )

    out_csv = filtered.to_csv(index=False)
    out_filename = f"cleaned_{original_filename}"

    blob_client = _blob_service_client.get_blob_client(container=_out_container, blob=out_filename)
    blob_client.upload_blob(out_csv, overwrite=True)
    logging.info("CleanSales2: uploaded '%s' to container '%s'", out_filename, _out_container)
