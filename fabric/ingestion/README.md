# Ingestion Module

The executable reference accepts documents, performs deterministic paragraph-aware hard-limit/overlap chunking, and writes chunks only through the memory API. Durable jobs, parsing/OCR, enrichment, evaluation, quarantine, and publish gates remain planned stages.

- Runtime: `viewsense_ingestion`
- Reference endpoint: `POST /v1/documents:ingest`
- Helm selection: `products.ingestion`
- Design contract: governed ingestion pipeline and provenance rules
