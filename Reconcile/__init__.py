"""
Reconcile — Azure Function (HTTP Trigger)

Called manually (or by a Logic App) after both CleanSales1 and CleanSales2
have finished. Accepts a JSON body with two blob URLs and a batch ID,
merges the two cleaned CSVs, and writes a final reconciled file.

Expected request body:
{
    "file_1_url": "https://<storage>.blob.core.windows.net/c1raw/cleaned_s1_raw.csv",
    "file_2_url": "https://<storage>.blob.core.windows.net/c2raw/cleaned_s2_raw.csv",
    "batchId": "batch_001"
}
"""

import logging

import azure.functions as func

from . import clean as cleaning_service


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Reconcile: received request")

    try:
        req_body = req.get_json()
        file_1_url = req_body.get("file_1_url")
        file_2_url = req_body.get("file_2_url")
        batch_id = req_body.get("batchId")
    except (ValueError, AttributeError) as exc:
        logging.error("Reconcile: failed to parse request body — %s", exc)
        return func.HttpResponse("Bad Request: invalid JSON body", status_code=400)

    if not all([file_1_url, file_2_url, batch_id]):
        return func.HttpResponse(
            "Bad Request: file_1_url, file_2_url, and batchId are all required",
            status_code=400,
        )

    result = cleaning_service.clean(file_1_url, file_2_url, batch_id)

    if result == "Success":
        logging.info("Reconcile: batch '%s' completed successfully", batch_id)
        return func.HttpResponse(
            f"Reconciliation complete for batch '{batch_id}'", status_code=200
        )
    else:
        logging.error("Reconcile: batch '%s' failed", batch_id)
        return func.HttpResponse("Reconciliation failed", status_code=500)
