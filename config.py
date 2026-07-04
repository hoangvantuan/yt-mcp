"""Cấu hình YouTube MCP.

Bí mật mức-người-dùng (refresh token) KHÔNG nằm ở đây — client gửi qua header
`x-youtube-refresh-token` mỗi request (xem auth.py). Server chỉ giữ bí mật
mức-ứng-dụng (client_id/secret của OAuth app) qua biến môi trường.
"""
import os

# --- OAuth app (mức ứng dụng, đặt trong env server) ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# URL gốc công khai của server (Tailscale HTTPS), dùng dựng redirect_uri OAuth.
# Ví dụ: https://my-host.tailnet-name.ts.net
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

TOKEN_URI = "https://oauth2.googleapis.com/token"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"

# --- Header client gửi credentials theo từng request ---
REFRESH_TOKEN_HEADER = "x-youtube-refresh-token"

# --- Scope xin 1 lần, đủ mọi tính năng (đọc + ghi + upload + analytics) ---
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]

# --- Thư mục lưu file upload tạm (client-local đẩy lên qua /upload) ---
UPLOAD_TMP_DIR = os.environ.get("UPLOAD_TMP_DIR", "/data/uploads_tmp")
UPLOAD_TTL_SECONDS = int(os.environ.get("UPLOAD_TTL_SECONDS", "86400"))  # 24h

# Cache access token: refresh sớm trước hạn thật (Google cấp 3600s).
ACCESS_TOKEN_TTL_SECONDS = 3000
