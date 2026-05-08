"""
CleanSales2 — Azure Function (HTTP Trigger)

Mirrors CleanSales1 but processes source-2 CSV data (c2raw container).
Filters to a specific item type instead of a region.
"""

import json
import logging

import azure.functions as func

from . import clean as cleaning_service


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("CleanSales2: received request")

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    if _is_validation_event(req_body):
        logging.info("CleanSales2: responding to Event Grid validation handshake")
        return func.HttpResponse(_build_validation_response(req_body))

    if _is_blob_created_event(req_body):
        logging.info("CleanSales2: blob created event — starting clean")
        result = cleaning_service.clean(req_body)

        if result == "Success":
            return func.HttpResponse("Successfully cleaned source-2 data", status_code=200)
        else:
            logging.error("CleanSales2: cleaning failed")
            return func.HttpResponse("Cleaning failed", status_code=500)

    logging.warning("CleanSales2: unrecognised event type — ignoring")
    return func.HttpResponse("Event ignored", status_code=200)


def _is_validation_event(body: list) -> bool:
    try:
        return body[0]["eventType"] == "Microsoft.EventGrid.SubscriptionValidationEvent"
    except (KeyError, IndexError, TypeError):
        return False


def _is_blob_created_event(body: list) -> bool:
    try:
        return body[0]["eventType"] == "Microsoft.Storage.BlobCreated"
    except (KeyError, IndexError, TypeError):
        return False


def _build_validation_response(body: list) -> str:
    validation_code = body[0]["data"]["validationCode"]
    return json.dumps({"validationResponse": validation_code})
