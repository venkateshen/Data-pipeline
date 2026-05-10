"""
Reconcile — Business Logic

Merges the two cleaned DataFrames produced by CleanSales1 and CleanSales2
into a single reconciled CSV, then uploads it to the 'reconciled' container.

Merge strategy
--------------
An outer join on 'names' is used so that:
  - Rows present in both datasets are joined.
  - Rows present in only one dataset are still included (NaN for missing columns).
This makes it easy to spot discrepancies between the two sources.
"""

import logging
import os

import pandas as pd
from azure.storage.blob import BlobServiceClient

from . import fetch_blob as fetching_service

_connection_string = os.getenv("BlobConnectionString", "UseDevelopmentStorage=true")
_out_container = os.getenv("FINAL", "reconciled")

_blob_service_client = BlobServiceClient.from_connection_string(_connection_string)


def clean(file_1_url: str, file_2_url: str, batch_id: str) -> str:
    """
    Main entry point for the Reconcile function.

    Parameters
    ----------
    file_1_url : str
        Full blob URL for the cleaned source-1 CSV.
    file_2_url : str
        Full blob URL for the cleaned source-2 CSV.
    batch_id : str
        Identifier used to name the output file.

    Returns
    -------
    str
        "Success" or "Error".
    """
    try:
        df1 = fetching_service.build_dataframe_from_url(file_1_url)
        df2 = fetching_service.build_dataframe_from_url(file_2_url)

        reconciled = _reconcile(df1, df2)
        _upload_result(reconciled, batch_id)
        return "Success"
    except Exception as exc:
        logging.error("Reconcile.clean() failed: %s", exc)
        return "Error"


def _reconcile(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """
    Merge the two cleaned DataFrames on 'names' using an outer join.

    Suffixes _s1 / _s2 are added to disambiguate columns that exist
    in both DataFrames (e.g. units_s1, units_s2).
    """
    merged = pd.merge(df1, df2, on="names", how="outer", suffixes=("_s1", "_s2"))
    logging.info(
        "Reconcile: merged %d s1 rows + %d s2 rows → %d reconciled rows",
        len(df1), len(df2), len(merged),
    )
    return merged


def _upload_result(df: pd.DataFrame, batch_id: str) -> None:
    """Serialise the reconciled DataFrame and write it to blob storage."""
    out_csv = df.to_csv(index=False)
    out_filename = f"reconciled_{batch_id}.csv"

    blob_client = _blob_service_client.get_blob_client(container=_out_container, blob=out_filename)
    blob_client.upload_blob(out_csv, overwrite=True)
    logging.info(
        "Reconcile: uploaded '%s' to container '%s'", out_filename, _out_container
    )
