# Sales Data Cleaning Pipeline

A serverless data cleaning and reconciliation pipeline built with **Azure Functions (Python)** and **pandas**. Raw CSV sales data is uploaded to Azure Blob Storage, automatically cleaned by HTTP-triggered Azure Functions, and merged into a final reconciled report.

## Architecture

```
Upload s1_raw.csv          Upload s2_raw.csv
       │                          │
       ▼                          ▼
  [Azure Blob]              [Azure Blob]
  c1raw container           c2raw container
       │                          │
       ▼                          ▼
[CleanSales1 Function]    [CleanSales2 Function]
  - Filter by region         - Filter by item
  - Group & aggregate        - Group & aggregate
  - Write cleaned CSV        - Write cleaned CSV
       │                          │
       └──────────┬───────────────┘
                  ▼
         [Reconcile Function]
          - Merge both datasets
          - Write final.csv
          - Output to reconciled container
```

### Functions

| Function | Trigger | What it does |
|---|---|---|
| `CleanSales1` | HTTP (Event Grid) | Cleans source-1 CSV: groups by name & region, filters to `east` region |
| `CleanSales2` | HTTP (Event Grid) | Cleans source-2 CSV: groups by name & item, filters to `binder` item |
| `Reconcile`   | HTTP (manual)      | Merges both cleaned CSVs into a final reconciled output |

---

## Getting Started

### Prerequisites

- Python 3.8+
- [Azure Functions Core Tools v4](https://docs.microsoft.com/azure/azure-functions/functions-run-local)
- Azure Storage Account (or [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite) for local dev)

### Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/sales-data-cleaning-pipeline.git
cd sales-data-cleaning-pipeline

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure local settings
cp local.settings.json.example local.settings.json
# Fill in your BlobAccountName and BlobAccountKey

# 5. Start the function host
func host start
```

### Deploy to Azure

```bash
# Create a resource group
az group create -l eastus -n sales-pipeline-rg

# Publish function app
func azure functionapp publish <your-function-app-name> --build-native-deps
```

---

## Testing the Pipeline

### Step 1 – Upload raw CSVs to Blob Storage

Upload `dataset/s1_raw.csv` to the `c1raw` container and `dataset/s2_raw.csv` to the `c2raw` container.

### Step 2 – Trigger CleanSales1 and CleanSales2

Send an Event Grid blob-created event (or use the sample payload):

```bash
curl -X POST http://localhost:7071/api/CleanSales1 \
  -H "Content-Type: application/json" \
  -d @tests/sample_blob_event.json
```

### Step 3 – Reconcile

```bash
curl -X POST http://localhost:7071/api/Reconcile \
  -H "Content-Type: application/json" \
  -d '{
    "file_1_url": "https://<storage>.blob.core.windows.net/c1raw/cleaned_s1_raw.csv",
    "file_2_url": "https://<storage>.blob.core.windows.net/c2raw/cleaned_s2_raw.csv",
    "batchId": "batch_001"
  }'
```

A `reconciled_batch_001.csv` file will be written to the `reconciled` container.

---

## Generate Sample Data

```bash
cd dataset
python randomcsvgenerator.py   # produces generated.csv with 100 rows
```

Edit `dataset/config.ini` to change column distributions.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Key Concepts (For Interviews)

- **Azure Functions**: Serverless compute; functions scale automatically with demand, and you only pay per execution.
- **Event Grid**: A fully managed event routing service; here it fires HTTP requests when a blob is uploaded to storage.
- **Blob Storage triggers**: Functions react to file system changes in Azure Storage without polling.
- **pandas `groupby` + `sum`**: Core data aggregation — groups rows by a key and aggregates numeric columns.
- **StringIO**: Lets pandas read a blob's text content as if it were a file, avoiding disk writes.
- **Environment variables**: Secrets (account keys, container names) are never hardcoded; they're loaded via `os.getenv`.
- **Separation of concerns**: Each function folder splits routing logic (`__init__.py`) from data logic (`clean.py`).

---

## Project Structure

```
sales-data-cleaning-pipeline/
├── CleanSales1/            # Function 1: cleans source-1 data
│   ├── __init__.py         # HTTP trigger handler
│   ├── clean.py            # pandas cleaning logic
│   └── function.json       # Azure Function binding config
├── CleanSales2/            # Function 2: cleans source-2 data
│   ├── __init__.py
│   ├── clean.py
│   └── function.json
├── Reconcile/              # Function 3: merges cleaned data
│   ├── __init__.py
│   ├── clean.py
│   ├── fetch_blob.py       # helper: fetch blobs into DataFrames
│   └── function.json
├── dataset/
│   ├── config.ini          # column definitions for data generator
│   ├── randomcsvgenerator.py
│   ├── s1_raw.csv          # sample source-1 data
│   └── s2_raw.csv          # sample source-2 data
├── tests/
│   ├── test_pipeline.py    # pytest tests
│   └── sample_blob_event.json
├── host.json
├── local.settings.json.example
├── requirements.txt
└── README.md
```

## License

MIT
� sample_blob_event.json
├── host.json
├── local.settings.json.example
├── requirements.txt
└── README.md
```

## License

MIT
