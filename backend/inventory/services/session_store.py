import time
import uuid

# { session_id: {"ecc": bytes, "ecc_name": str, "s4": bytes, "s4_name": str,
#                "created": float} }
_SESSIONS: dict[str, dict] = {}
# { download_id: bytes }
_DOWNLOADS: dict[str, bytes] = {}
TTL = 60 * 60  # 1 hour

def _gc():
    now = time.time()
    for store in (_SESSIONS, _DOWNLOADS):
        for k in [k for k, v in store.items()
                  if now - (v.get("created", now) if isinstance(v, dict) else now) > TTL]:
            store.pop(k, None)

def create_session(ecc_bytes: bytes, ecc_name: str,
                   s4_bytes: bytes, s4_name: str) -> str:
    _gc()
    sid = uuid.uuid4().hex
    _SESSIONS[sid] = {
        "ecc": ecc_bytes, "ecc_name": ecc_name,
        "s4": s4_bytes,   "s4_name": s4_name,
        "created": time.time(),
    }
    return sid

def get_session(sid: str) -> dict | None:
    _gc()
    return _SESSIONS.get(sid)

def put_download(xlsx_bytes: bytes) -> str:
    _gc()
    did = uuid.uuid4().hex
    _DOWNLOADS[did] = {"data": xlsx_bytes, "created": time.time()}
    return did

def get_download(did: str) -> bytes | None:
    _gc()
    entry = _DOWNLOADS.get(did)
    return entry["data"] if entry else None