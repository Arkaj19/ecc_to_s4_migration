# backend/config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # backend\

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

TEMPLATES_DIR      = os.path.join(BASE_DIR, "fico", "templates")
REFERENCE_DATA_DIR = os.path.join(BASE_DIR, "fico", "reference_data")

BUT_REFERENCE_PATH = os.path.join(REFERENCE_DATA_DIR, "but0id_qs4_500.xlsx")
CLERK_CODES_PATH   = os.path.join(REFERENCE_DATA_DIR, "DAP_CODES.xlsx")