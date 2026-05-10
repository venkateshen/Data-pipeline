"""
fetch_blob.py — Blob fetching helpers for the Reconcile function.

Separating blob I/O from business logic (clean.py) keeps each module
focused and easier to test independently.
"""

import logging
import os
from io import StringIO

import pandas as pd
from azure.storage.blob import BlobServiceClient

_connection_string = os.getenv("BlobConnectionString", "UseDevelopmentStorage=true")
_blob_service_client = BlobServiceClient.from_connection_string(_connection_string)


def list_blobs_with_prefix(container_name: str, prefix: str) -> list:
    """
    Return a list of blob names in *container_name* whose names start with *prefix*.

    Used by clean.py to discover the cleaned CSV files for a given batch.
    """
    container_client = _blob_service_client.get_container_client(container_name)
    blobs = container_client.list_blobs(name_starts_with=prefix)
    names = [b.name for b in blobs]
    logging.info(
        "fetch_blob: found %d blob(s) in container '%s' with prefix '%s'",
        len(names), container_name, prefix,
    )
    return names


def blob_to_dataframe(container_name: str, blob_name: str) -> pd.DataFrame:
    """
    Download a single blob as text and parse it into a pandas DataFrame.

    Parameters
    ----------
    container_name : str
        The Azure Blob container to read from.
    blob_name : str
        The blob filename inside that container.

    Returns
    -------
    pd.DataFrame
    """
    logging.info("fetch_blob: downloading '%s' from container '%s'", blob_name, container_name)
    blob_client = _blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_content = blob_client.download_blob().readall().decode("utf-8")
    df = pd.read_csv(StringIO(blob_content))
    logging.info("fetch_blob: loaded %d rows from '%s'", len(df), blob_name)
    return df


def build_dataframe_from_url(blob_url: str) -> pd.DataFrame:
    """
    Convenience wrapper: parse a full blob URL and return its contents as a DataFrame.

    Example URL:
        https://<account>.blob.core.windows.net/c1raw/cleaned_s1_raw.csv
    """
    blob_name = blob_url.rsplit("/", 1)[-1]
    container_name = blob_url.rsplit("/", 2)[-2]
    return blob_to_dataframe(container_name, blob_name)
