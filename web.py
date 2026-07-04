"""Route web gắn cùng tiến trình MCP.

- /auth, /auth/callback: OAuth consent 1 lần -> HIỂN THỊ refresh token cho user
  copy vào config client. Server KHÔNG lưu.
- /upload: nhận file client-local (kéo-thả browser hoặc curl -F) -> trả id để
  dùng làm `source` cho youtube_video_upload. File lưu tạm + TTL, tự xoá sau upload.
"""
import glob
import html
import os
import time
import uuid

from google_auth_oauthlib.flow import Flow
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

import config


def _client_config() -> dict:
    return {
        "web": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": config.AUTH_URI,
            "token_uri": config.TOKEN_URI,
        }
    }


def _redirect_uri() -> str:
    return f"{config.PUBLIC_BASE_URL}/auth/callback"


async def auth_start(request: Request) -> RedirectResponse:
    """Bắt đầu consent: chuyển hướng tới Google."""
    if not config.PUBLIC_BASE_URL:
        return HTMLResponse("Chưa cấu hình PUBLIC_BASE_URL trong env server.", status_code=500)
    flow = Flow.from_client_config(_client_config(), scopes=config.SCOPES)
    flow.redirect_uri = _redirect_uri()
    auth_url, _ = flow.authorization_url(
        access_type="offline",  # để nhận refresh token
        prompt="consent",       # ép cấp refresh token mỗi lần
        include_granted_scopes="true",
    )
    return RedirectResponse(auth_url)


async def auth_callback(request: Request) -> HTMLResponse:
    """Google gọi lại kèm code -> đổi lấy refresh token -> hiển thị."""
    error = request.query_params.get("error")
    if error:
        return HTMLResponse(f"OAuth lỗi: {html.escape(error)}", status_code=400)
    code = request.query_params.get("code")
    if not code:
        return HTMLResponse("Thiếu 'code' trong callback.", status_code=400)

    flow = Flow.from_client_config(_client_config(), scopes=config.SCOPES)
    flow.redirect_uri = _redirect_uri()
    flow.fetch_token(code=code)
    refresh_token = flow.credentials.refresh_token
    if not refresh_token:
        return HTMLResponse(
            "Không nhận được refresh token. Thử thu hồi quyền ở "
            "myaccount.google.com/permissions rồi consent lại.",
            status_code=400,
        )

    rt = html.escape(refresh_token)
    body = f"""
    <h2>Refresh token của bạn</h2>
    <p>Dán giá trị này vào header <code>{config.REFRESH_TOKEN_HEADER}</code> trong config MCP client.
       Server KHÔNG lưu nó.</p>
    <textarea rows="3" style="width:100%;font-family:monospace" readonly>{rt}</textarea>
    <p style="color:#a00">Giữ bí mật như mật khẩu. Ai có nó thao tác được kênh của bạn.</p>
    """
    return HTMLResponse(f"<html><body style='max-width:720px;margin:40px auto'>{body}</body></html>")


async def upload_form(request: Request) -> HTMLResponse:
    """Trang kéo-thả file (zero-install)."""
    page = """
    <html><body style="max-width:720px;margin:40px auto;font-family:sans-serif">
    <h2>Đẩy video lên server</h2>
    <p>Chọn file -> nhận <code>id</code> -> dùng làm <code>source</code> cho tool
       <code>youtube_video_upload</code>.</p>
    <form method="post" enctype="multipart/form-data" action="/upload">
      <input type="file" name="file" required>
      <button type="submit">Tải lên</button>
    </form>
    <p>Hoặc: <code>curl -F file=@video.mp4 ${location.origin}/upload</code></p>
    </body></html>
    """
    return HTMLResponse(page)


async def upload_receive(request: Request) -> JSONResponse:
    """Nhận multipart -> lưu tạm -> trả id."""
    form = await request.form()
    upload = form.get("file")
    if upload is None:
        return JSONResponse({"error": "thiếu field 'file'"}, status_code=400)

    os.makedirs(config.UPLOAD_TMP_DIR, exist_ok=True)
    _cleanup_expired()
    file_id = f"up_{uuid.uuid4().hex}"
    safe_name = os.path.basename(getattr(upload, "filename", "") or "video")
    dest = os.path.join(config.UPLOAD_TMP_DIR, f"{file_id}__{safe_name}")
    with open(dest, "wb") as f:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return JSONResponse({"id": file_id, "filename": safe_name})


async def upload_dispatch(request: Request):
    """GET -> form; POST -> nhận file."""
    if request.method == "GET":
        return await upload_form(request)
    return await upload_receive(request)


def _cleanup_expired() -> None:
    now = time.time()
    for path in glob.glob(os.path.join(config.UPLOAD_TMP_DIR, "*")):
        try:
            if now - os.path.getmtime(path) > config.UPLOAD_TTL_SECONDS:
                os.remove(path)
        except OSError:
            pass
