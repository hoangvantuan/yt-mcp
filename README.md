# yt-mcp — YouTube MCP Server

MCP server quản lý kênh YouTube (Data API v3 + Analytics), kiến trúc **stateless
theo tinh thần Facebook MCP**: server **không lưu token người dùng**. Client giữ
refresh token, server đổi ra access token và cache RAM theo `sha256(refresh_token)`.

Xem thiết kế chi tiết + lý do từng quyết định: `2BRAIN/wiki/ai-cong-nghe/youtube-mcp-thiet-ke-oauth-stateless.md`.

## Kiến trúc

```
server.py       → khai báo tool @mcp.tool() (passthrough mỏng)
manager.py      → điều phối, ráp tham số
youtube_api.py  → gọi Data API v3 + Analytics (google-api-python-client)
auth.py         → refresh→access + cache theo hash(refresh token)
jobs.py         → upload async in-memory (job)
web.py          → route /auth, /auth/callback, /upload
config.py       → scope + hằng số
run_http.py     → streamable-http (stateless) + gắn route web
```

## Chuẩn bị Google Cloud (1 lần)

1. Tạo project ở Google Cloud Console (tài khoản `hoangtuanbka93@gmail.com`).
2. Bật **YouTube Data API v3** và **YouTube Analytics API**.
3. OAuth consent screen: **External** → **Publish app → In production** (chấp nhận
   "unverified"; nếu Testing thì refresh token chết sau 7 ngày).
4. Tạo **OAuth client ID** kiểu **Web application**. Thêm Authorized redirect URI:
   `https://<host>.<tailnet>.ts.net/auth/callback`.
5. Lấy `client_id` + `client_secret`.

## Cấu hình & chạy

Tạo file `.env` cạnh `compose.yaml`:

```dotenv
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
PUBLIC_BASE_URL=https://my-host.tailnet-name.ts.net
```

```bash
docker compose up -d --build
```

- Endpoint MCP: `https://<host>.<tailnet>.ts.net/mcp`
- Trang lấy token: `https://<host>.<tailnet>.ts.net/auth`
- Trang đẩy file: `https://<host>.<tailnet>.ts.net/upload`

## Lấy refresh token (1 lần)

Mở `https://<host>.<tailnet>.ts.net/auth` bằng browser → đồng ý (bấm qua cảnh báo
"unverified app" 1 lần) → trang hiện **refresh token** → copy.

## Khai báo ở MCP client

```jsonc
"yt-mcp": {
  "url": "https://<host>.<tailnet>.ts.net/mcp",
  "headers": { "x-youtube-refresh-token": "1//dán_refresh_token_ở_đây" }
}
```

Quản nhiều kênh = khai báo nhiều kết nối, mỗi cái một refresh token khác.

## Upload video

`source` của `youtube_video_upload` nhận 3 dạng:

| Nguồn | `source` | Cách đưa file lên |
|---|---|---|
| File trên laptop | id `up_xxx` | mở `/upload` kéo-thả, hoặc `curl -F file=@video.mp4 https://<host>/upload` |
| File có URL | `https://.../video.mp4` | server tự tải |
| File trên máy chủ | `/data/video.mp4` | bỏ vào thư mục `./data` (đã mount) |

Upload chạy nền → trả `job_id` → poll bằng `youtube_upload_status(job_id)`.

## Danh sách tool (~30)

- **Channel**: `youtube_channel_get` (bỏ trống = whoami), `youtube_channel_update`
- **Video**: `youtube_video_get`, `youtube_video_list_mine`, `youtube_video_update`,
  `youtube_video_delete`, `youtube_video_rate`, `youtube_video_set_privacy`
- **Upload**: `youtube_video_upload`, `youtube_upload_status`
- **Search**: `youtube_search`
- **Comment**: `youtube_comment_list`, `youtube_comment_thread_get`,
  `youtube_comment_reply`, `youtube_comment_moderate`, `youtube_comment_delete`
- **Playlist**: `youtube_playlist_create/list/get/update/delete`,
  `youtube_playlist_items`, `youtube_playlist_item_add/remove`
- **Analytics**: `youtube_analytics_video/channel/top_videos`

## Ràng buộc đã biết

- **Quota dùng chung**: 1 OAuth app = 10.000 unit/ngày cho mọi client (upload=1.600/lần).
  Chạm trần thì xin Google nâng quota.
- Upload file client-local luôn 2 bước (đẩy file → gọi tool).
- Job upload lưu in-memory → mất khi restart container.
