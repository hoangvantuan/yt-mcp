"""Khai báo tool MCP cho YouTube. Mỗi tool là passthrough mỏng xuống manager.

Lỗi được bọc thành dict có cấu trúc (structured errors) để agent tự sửa được,
thay vì ném exception thô.
"""
import functools
from typing import Any, Optional

from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

from manager import Manager

mcp = FastMCP("YouTubeMCP")
manager = Manager()


def tool_safe(fn):
    """Bọc tool: bắt lỗi -> trả dict có cấu trúc kèm gợi ý."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except HttpError as e:
            status = getattr(e, "status_code", None) or getattr(e.resp, "status", None)
            hint = ""
            if status == 401:
                hint = "Refresh token sai/hết hiệu lực. Lấy lại ở /auth."
            elif status == 403:
                hint = "Thiếu scope, không có quyền, hoặc hết quota ngày (10.000 unit/app)."
            elif status == 404:
                hint = "Không tìm thấy tài nguyên (id sai?)."
            return {"error": True, "http_status": status,
                    "reason": str(e), "hint": hint}
        except (ValueError, RuntimeError, FileNotFoundError) as e:
            return {"error": True, "type": type(e).__name__, "reason": str(e)}
    return wrapper


# ==================== CHANNEL ====================
@mcp.tool()
@tool_safe
def youtube_channel_get(channel_id: Optional[str] = None) -> dict[str, Any]:
    """Lấy thông tin kênh. Bỏ trống channel_id = kênh của token hiện tại (whoami).
    Input: channel_id (str, tùy chọn)
    Output: dict channel (snippet, statistics, branding)
    """
    return manager.get_channel(channel_id)


@mcp.tool()
@tool_safe
def youtube_channel_update(channel_id: str, description: Optional[str] = None,
                           keywords: Optional[str] = None,
                           country: Optional[str] = None) -> dict[str, Any]:
    """Cập nhật branding kênh (mô tả, keywords, quốc gia)."""
    return manager.update_channel(channel_id, description, keywords, country)


# ==================== VIDEO ====================
@mcp.tool()
@tool_safe
def youtube_video_get(video_id: str) -> dict[str, Any]:
    """Lấy chi tiết 1 video (snippet, status, statistics, contentDetails)."""
    return manager.get_video(video_id)


@mcp.tool()
@tool_safe
def youtube_video_list_mine(max_results: int = 25) -> dict[str, Any]:
    """Liệt kê video mới nhất của kênh hiện tại (từ playlist uploads)."""
    return manager.list_my_videos(max_results)


@mcp.tool()
@tool_safe
def youtube_video_update(video_id: str, title: Optional[str] = None,
                         description: Optional[str] = None,
                         tags: Optional[list[str]] = None,
                         category_id: Optional[str] = None) -> dict[str, Any]:
    """Sửa metadata video (tiêu đề, mô tả, tags, category)."""
    return manager.update_video(video_id, title, description, tags, category_id)


@mcp.tool()
@tool_safe
def youtube_video_delete(video_id: str) -> dict[str, Any]:
    """Xoá 1 video. Không hoàn tác."""
    return manager.delete_video(video_id)


@mcp.tool()
@tool_safe
def youtube_video_rate(video_id: str, rating: str) -> dict[str, Any]:
    """Đánh giá video. rating: like | dislike | none."""
    return manager.rate_video(video_id, rating)


@mcp.tool()
@tool_safe
def youtube_video_set_privacy(video_id: str, privacy: str,
                              publish_at: Optional[str] = None) -> dict[str, Any]:
    """Đổi quyền riêng tư (public|unlisted|private). publish_at (ISO8601)=hẹn công khai."""
    return manager.set_privacy(video_id, privacy, publish_at)


# ==================== UPLOAD (async) ====================
@mcp.tool()
@tool_safe
def youtube_video_upload(source: str, title: str, description: str = "",
                         tags: Optional[list[str]] = None, category_id: str = "22",
                         privacy: str = "private",
                         publish_at: Optional[str] = None) -> dict[str, Any]:
    """Upload video (chạy nền, trả job_id).
    source: id (từ /upload) | URL | đường dẫn file trên máy chủ (mount).
    Poll tiến độ bằng youtube_upload_status(job_id).
    """
    return manager.upload_video(source, title, description, tags,
                                category_id, privacy, publish_at)


@mcp.tool()
@tool_safe
def youtube_upload_status(job_id: str) -> dict[str, Any]:
    """Trạng thái job upload: pending|resolving|uploading|done|error + progress + video_id."""
    return manager.upload_status(job_id)


# ==================== SEARCH ====================
@mcp.tool()
@tool_safe
def youtube_search(q: str, max_results: int = 25, kind: str = "video") -> dict[str, Any]:
    """Tìm kiếm công khai. kind: video | channel | playlist."""
    return manager.search(q, max_results, kind)


# ==================== COMMENTS ====================
@mcp.tool()
@tool_safe
def youtube_comment_list(video_id: str, max_results: int = 50) -> dict[str, Any]:
    """Liệt kê comment (thread) của 1 video."""
    return manager.list_comments(video_id, max_results)


@mcp.tool()
@tool_safe
def youtube_comment_thread_get(thread_id: str) -> dict[str, Any]:
    """Lấy 1 thread comment kèm reply."""
    return manager.get_comment_thread(thread_id)


@mcp.tool()
@tool_safe
def youtube_comment_reply(parent_id: str, text: str) -> dict[str, Any]:
    """Trả lời 1 comment (parent_id = id comment gốc hoặc thread top-level)."""
    return manager.reply_comment(parent_id, text)


@mcp.tool()
@tool_safe
def youtube_comment_moderate(comment_id: str, status: str,
                             ban_author: bool = False) -> dict[str, Any]:
    """Kiểm duyệt comment. status: published | heldForReview | rejected."""
    return manager.moderate_comment(comment_id, status, ban_author)


@mcp.tool()
@tool_safe
def youtube_comment_delete(comment_id: str) -> dict[str, Any]:
    """Xoá 1 comment của mình."""
    return manager.delete_comment(comment_id)


# ==================== PLAYLIST ====================
@mcp.tool()
@tool_safe
def youtube_playlist_create(title: str, description: str = "",
                            privacy: str = "private") -> dict[str, Any]:
    """Tạo playlist mới."""
    return manager.create_playlist(title, description, privacy)


@mcp.tool()
@tool_safe
def youtube_playlist_list(max_results: int = 25) -> dict[str, Any]:
    """Liệt kê playlist của kênh hiện tại."""
    return manager.list_playlists(max_results)


@mcp.tool()
@tool_safe
def youtube_playlist_get(playlist_id: str) -> dict[str, Any]:
    """Lấy chi tiết 1 playlist."""
    return manager.get_playlist(playlist_id)


@mcp.tool()
@tool_safe
def youtube_playlist_update(playlist_id: str, title: Optional[str] = None,
                            description: Optional[str] = None,
                            privacy: Optional[str] = None) -> dict[str, Any]:
    """Sửa playlist (tiêu đề, mô tả, quyền riêng tư)."""
    return manager.update_playlist(playlist_id, title, description, privacy)


@mcp.tool()
@tool_safe
def youtube_playlist_delete(playlist_id: str) -> dict[str, Any]:
    """Xoá playlist."""
    return manager.delete_playlist(playlist_id)


@mcp.tool()
@tool_safe
def youtube_playlist_items(playlist_id: str, max_results: int = 50) -> dict[str, Any]:
    """Liệt kê video trong playlist."""
    return manager.list_playlist_items(playlist_id, max_results)


@mcp.tool()
@tool_safe
def youtube_playlist_item_add(playlist_id: str, video_id: str) -> dict[str, Any]:
    """Thêm video vào playlist."""
    return manager.add_playlist_item(playlist_id, video_id)


@mcp.tool()
@tool_safe
def youtube_playlist_item_remove(item_id: str) -> dict[str, Any]:
    """Xoá 1 mục khỏi playlist (item_id = id playlistItem, không phải video_id)."""
    return manager.remove_playlist_item(item_id)


# ==================== ANALYTICS ====================
@mcp.tool()
@tool_safe
def youtube_analytics_video(video_id: str, start_date: str, end_date: str,
                            metrics: Optional[str] = None) -> dict[str, Any]:
    """Analytics 1 video. date định dạng YYYY-MM-DD. metrics phân tách bằng dấu phẩy."""
    return manager.video_metrics(video_id, start_date, end_date, metrics)


@mcp.tool()
@tool_safe
def youtube_analytics_channel(start_date: str, end_date: str,
                              metrics: Optional[str] = None,
                              dimensions: Optional[str] = None) -> dict[str, Any]:
    """Analytics toàn kênh. date YYYY-MM-DD. dimensions vd 'day' để tách theo ngày."""
    return manager.channel_metrics(start_date, end_date, metrics, dimensions)


@mcp.tool()
@tool_safe
def youtube_analytics_top_videos(start_date: str, end_date: str,
                                 max_results: int = 10) -> dict[str, Any]:
    """Top video theo lượt xem trong khoảng ngày."""
    return manager.top_videos(start_date, end_date, max_results)
