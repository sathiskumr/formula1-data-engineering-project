# Databricks notebook source
import requests
import time
from datetime import datetime, timezone
from pyspark.dbutils import DBUtils

dbutils = DBUtils(spark)

# COMMAND ----------

dbutils.widgets.text("p_season", "")
dbutils.widgets.text("p_round_no", "")

# COMMAND ----------

p_season   = dbutils.widgets.get("p_season")
p_round_no = dbutils.widgets.get("p_round_no")

# COMMAND ----------

PBI_GROUP_ID  = "40986bf1-d823-46d9-be2e-78f0abfd900b"
PBI_REPORT_ID = "0917ad65-16c2-493e-ac4f-3ebda77d977c"
EXPORT_FORMAT = "PDF"

# Managed volume in dev/Free Edition, external (abfss-backed) volume in premium 
# the path stays the same either way, UC handles the backend.
OUTPUT_PATH = "/Volumes/formula1_incr/reports/snapshots"

SECRET_SCOPE = "pbi-secrets"
SECRET_KEYS  = {"tenant": "pbi-tenant-id", "client": "pbi-client-id", "secret": "pbi-client-secret"}

POLL_INTERVAL = 10
MAX_WAIT      = 600   # raise for long/multi-page reports — PBI processes 5 pages at a time

PBI_BASE = "https://api.powerbi.com/v1.0/myorg"

# COMMAND ----------

def get_token(tenant_id, client_id, client_secret):
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "grant_type": "client_credentials", "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]

# COMMAND ----------

def start_export(token, group_id, report_id, fmt):
    url = f"{PBI_BASE}/groups/{group_id}/reports/{report_id}/ExportTo"
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                          json={"format": fmt}, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]

# COMMAND ----------

def poll_export(token, group_id, report_id, export_id, interval, max_wait):
    url = f"{PBI_BASE}/groups/{group_id}/reports/{report_id}/exports/{export_id}"
    headers = {"Authorization": f"Bearer {token}"}
    waited = 0
    while waited < max_wait:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print(f"  [{waited:>4}s] {data['status']} — {data.get('percentComplete', 0)}%")
        if data["status"] == "Succeeded":
            return
        if data["status"] in ("Failed", "Cancelled"):
            raise RuntimeError(f"Export {data['status']}: {data}")
        time.sleep(interval)
        waited += interval
    raise TimeoutError(f"Export not done after {max_wait}s — consider raising MAX_WAIT")

# COMMAND ----------

def download_export(token, group_id, report_id, export_id):
    url = f"{PBI_BASE}/groups/{group_id}/reports/{report_id}/exports/{export_id}/file"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=120)
    resp.raise_for_status()
    return resp.content

# COMMAND ----------

def save_snapshot(file_bytes, output_path, season, round_no, fmt):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{season}_{round_no}_{ts}.{fmt.lower()}"
    full_path = f"{output_path.rstrip('/')}/{filename}"

    # Volumes are FUSE-mounted regardless of backend (managed or external/abfss) —
    # plain file I/O works directly either way.
    with open(full_path, "wb") as f:
        f.write(file_bytes)
    return full_path

# COMMAND ----------

tenant_id     = dbutils.secrets.get(SECRET_SCOPE, SECRET_KEYS["tenant"])
client_id     = dbutils.secrets.get(SECRET_SCOPE, SECRET_KEYS["client"])
client_secret = dbutils.secrets.get(SECRET_SCOPE, SECRET_KEYS["secret"])

token     = get_token(tenant_id, client_id, client_secret)
export_id = start_export(token, PBI_GROUP_ID, PBI_REPORT_ID, EXPORT_FORMAT)
poll_export(token, PBI_GROUP_ID, PBI_REPORT_ID, export_id, POLL_INTERVAL, MAX_WAIT)
file_bytes = download_export(token, PBI_GROUP_ID, PBI_REPORT_ID, export_id)

snapshot_path = save_snapshot(file_bytes, OUTPUT_PATH, p_season, p_round_no, EXPORT_FORMAT)
print(f"Saved snapshot to {snapshot_path} ({len(file_bytes):,} bytes)")
