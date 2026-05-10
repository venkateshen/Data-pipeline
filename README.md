# Sales Data Cleaning Pipeline

A serverless data cleaning and reconciliation pipeline built with **Azure Functions (Python)** and **pandas**. This project demonstrates how to handle multi-source data ingestion, automated cleaning via Event Grid triggers (simulated), and final reconciliation.

## Architecture

1. **CleanSales1**: Groups by Name/Region, filters to 'east' region.
2. **CleanSales2**: Groups by Name/Item, filters to 'binder' item.
3. **Reconcile**: Merges both datasets via an outer join on 'Name'.

---

## 🚀 Quick Start (Demonstration)

To run the entire pipeline and see the results immediately, use the automated demo script:

1. Open **PowerShell** as Administrator (or ensure you have permissions to run scripts).
2. Navigate to the project folder:
   ```powershell
   cd C:\Users\venki\Data-pipeline
   ```
3. Run the demo script:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_demo.ps1
   ```

**What the script does:**
- Starts **Azurite** (local storage emulator).
- Initializes blob containers and uploads sample data.
- Starts the **Azure Functions** host.
- Automatically triggers the cleaning and reconciliation functions.
- Stops the services when you're done.

---

## 🛠 Manual Setup (Local Dev)

### Prerequisites
- Python 3.8+
- [Azure Functions Core Tools v4](https://docs.microsoft.com/azure/azure-functions/functions-run-local)
- [Azurite](https://github.com/Azure/Azurite) (`npm install -g azurite`)

### Installation
```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure storage
# Ensure Azurite is running: azurite --location ./azurite_data --skipApiVersionCheck
python setup_local_storage.py
```

### Running Functions
```powershell
func start
```

---

## 🧪 Verification
After running the demo or manual triggers, you can verify the results in local storage.
- **Cleaned Data:** Containers `c1raw` and `c2raw`.
- **Final Report:** Container `reconciled`.

You can use [Azure Storage Explorer](https://azure.microsoft.com/en-us/products/storage/storage-explorer/) and point it to your local Azurite instance to view the CSV files visually.

---

## Project Structure
- `CleanSales1/`: Logic for source 1 (Region-based cleaning).
- `CleanSales2/`: Logic for source 2 (Item-based cleaning).
- `Reconcile/`: Final merge logic.
- `dataset/`: Sample raw CSV data.
- `run_demo.ps1`: One-click automation script.
