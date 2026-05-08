# Changelog

## [1.0.0] — 2024-01-15

### Added
- `CleanSales1`: HTTP-triggered function to clean source-1 CSV (filter by region)
- `CleanSales2`: HTTP-triggered function to clean source-2 CSV (filter by item type)
- `Reconcile`: HTTP-triggered function to merge both cleaned datasets
- Random CSV generator with configurable column distributions
- Comprehensive pytest test suite for all cleaning transformations
- `fetch_blob.py` helper module for reusable blob I/O
- Full inline documentation across all modules
