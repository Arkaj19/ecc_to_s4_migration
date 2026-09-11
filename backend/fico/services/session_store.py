"""
In-memory download store for the fico module.

Mirrors inventory/services/session_store.py's `put_download` /
`get_download` pattern. Previously, generated reports and currency
dumps (AR/AP/Credit) were written to fixed, shared paths on disk, e.g.
REPORTS_DIR / "AR_Validation_Report.pdf". That meant:

  - two users validating at the same time could clobber each other's
    report/dump mid-write, or one user could download the other's
    file, since the path didn't depend on who generated it.
  - the file only exists on whichever instance generated it, so this
    breaks the moment the backend runs on more than one node (e.g.
    behind a load balancer in AWS) -- the download request can land
    on a different instance than the one that wrote the file.

Instead, each generated file is kept in memory under a random
`download_id` and handed back to the caller (in a response header or
JSON field), who returns it to the client. The client then fetches the
bytes via a `.../{download_id}` GET.

NOTE: this is still a single-process, in-memory store, exactly like
inventory's version -- it fixes clobbering today, but a download_id
minted on one instance still won't be found by a different instance.
Actually surviving horizontal scaling will need this dict to move to
something shared across instances (e.g. Redis or S3) once there's more
than one instance running at a time.
"""
import time
import uuid

# { download_id: {"data": bytes, "filename": str, "media_type": str, "created": float} }
_DOWNLOADS: dict[str, dict] = {}
TTL = 60 * 60  # 1 hour


def _gc():
    now = time.time()
    for did in [did for did, entry in _DOWNLOADS.items()
                if now - entry["created"] > TTL]:
        _DOWNLOADS.pop(did, None)


def put_download(data: bytes, filename: str, media_type: str) -> str:
    """Store a generated file's bytes and return its download_id."""
    _gc()
    did = uuid.uuid4().hex
    _DOWNLOADS[did] = {
        "data": data,
        "filename": filename,
        "media_type": media_type,
        "created": time.time(),
    }
    return did


def get_download(download_id: str) -> dict | None:
    """Look up a previously stored file by its download_id, or None."""
    _gc()
    return _DOWNLOADS.get(download_id)
