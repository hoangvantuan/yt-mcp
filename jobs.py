"""Quản upload async in-memory.

Upload file lớn mất nhiều phút -> không chạy đồng bộ trong 1 lời gọi MCP (timeout).
Tool trả job_id ngay, upload chạy ở thread nền, poll bằng youtube_upload_status.
Bảng job là trạng thái TẠM (mất khi restart), không phải secret.
"""
import glob
import os
import threading
import uuid
from typing import Any, Optional

import requests
from googleapiclient.http import MediaFileUpload

import auth
import config

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _set(job_id: str, **fields: Any) -> None:
    with _jobs_lock:
        _jobs.setdefault(job_id, {}).update(fields)


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def resolve_source(source: str) -> tuple[str, bool]:
    """source -> (đường dẫn file cục bộ server, có phải file tạm cần xoá không).

    3 dạng: id (đẩy qua /upload) | URL (tải về) | path mount (đọc thẳng).
    """
    # 1) path có thật trên máy chủ (mount)
    if os.path.exists(source):
        return source, False
    # 2) URL -> tải về thư mục tạm
    if source.startswith("http://") or source.startswith("https://"):
        os.makedirs(config.UPLOAD_TMP_DIR, exist_ok=True)
        dest = os.path.join(config.UPLOAD_TMP_DIR, f"dl_{uuid.uuid4().hex}")
        with requests.get(source, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
        return dest, True
    # 3) id từ /upload -> tìm file <id>__* trong thư mục tạm
    matches = glob.glob(os.path.join(config.UPLOAD_TMP_DIR, f"{source}__*"))
    if matches:
        return matches[0], True
    raise FileNotFoundError(
        f"Không resolve được source '{source}'. Cần: id (từ /upload), URL, hoặc path mount có thật."
    )


def _run_upload(job_id: str, refresh_token: str, source: str, body: dict[str, Any]) -> None:
    path = None
    is_tmp = False
    try:
        _set(job_id, status="resolving")
        path, is_tmp = resolve_source(source)

        _set(job_id, status="uploading", progress=0)
        youtube = auth.build_service_from_refresh("youtube", "v3", refresh_token)
        media = MediaFileUpload(path, chunksize=8 * 1024 * 1024, resumable=True)
        request = youtube.videos().insert(
            part=",".join(body.keys()), body=body, media_body=media
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                _set(job_id, progress=int(status.progress() * 100))
        _set(job_id, status="done", progress=100, video_id=response.get("id"), result=response)
    except Exception as exc:  # noqa: BLE001 — báo lỗi tường minh cho agent
        _set(job_id, status="error", error=f"{type(exc).__name__}: {exc}")
    finally:
        if is_tmp and path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def submit_upload(refresh_token: str, source: str, body: dict[str, Any]) -> str:
    job_id = f"job_{uuid.uuid4().hex}"
    _set(job_id, id=job_id, status="pending", progress=0)
    t = threading.Thread(
        target=_run_upload, args=(job_id, refresh_token, source, body), daemon=True
    )
    t.start()
    return job_id
