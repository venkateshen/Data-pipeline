"""
CleanSales1 — Azure Function (HTTP Trigger)

Handles two types of Event Grid events:
  1. SubscriptionValidationEvent  – handshake when the Event Grid subscription is created
  2. BlobCreated                  – fired when a new CSV lands in the c1raw container

The actual pandas cleaning logic lives in clean.py (separation of concerns).
"""

import json
import logging

import azure.functions as func

from . import clean as cleaning_service


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("CleanSales1: received request")

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    if _is_validation_event(req_body):
        # Event Grid sends a validation handshake the first time a subscription is created.
        # We must echo back the validationCode to confirm the endpoint.
        logging.info("CleanSales1: responding to Event Grid validation handshake")
        return func.HttpResponse(_build_validation_response(req_body))

    if _is_blob_created_event(req_body):
        logging.info("CleanSales1: blob created event — starting clean")
        result = cleaning_service.clean(req_body)

        if result == "Success":
            return func.HttpResponse("Successfully cleaned source-1 data", status_code=200)
        else:
            logging.error("CleanSales1: cleaning failed")
            return func.HttpResponse("Cleaning failed", status_code=500)

    # Any other event type is silently ignored
    logging.warning("CleanSales1: unrecognised event type — ignoring")
    return func.HttpResponse("Event ignored", status_code=200)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_validation_event(body: list) -> bool:
    """Return True if the request is an Event Grid subscription-validation event."""
    try:
        return body[0]["eventType"] == "Microsoft.EventGrid.SubscriptionValidationEvent"
    except (KeyError, IndexError, TypeError):
        return False


def _is_blob_created_event(body: list) -> bool:
    """Return True if the request signals that a new blob has been created."""
    try:
        return body[0]["eventType"] == "Microsoft.Storage.BlobCreated"
    except (KeyError, IndexError, TypeError):
        return False


def _build_validation_response(body: list) -> str:
    """Build the JSON response required by the Event Grid validation handshake."""
    validation_code = body[0]["data"]["validationCode"]
    return json.dumps({"validationResponse": validation_code})
