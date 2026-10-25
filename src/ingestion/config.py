
"""
Configuration for GeneScope AI scientific data ingestion.
"""

# Scientific research target
TARGET_GENE = "APOE"
TARGET_GENE_ID = "348"
TARGET_ORGANISM = "Homo sapiens"

# Initial dataset limits
MAX_PUBMED_RECORDS = 10
MAX_CLINVAR_RECORDS = 10

# Local storage
RAW_DATA_DIR = "data/raw"
PROCESSED_DATA_DIR = "data/processed"