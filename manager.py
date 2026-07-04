"""Điều phối: ráp tham số, gọi youtube_api, quản upload async qua jobs."""
from typing import Any, Optional

import auth
import jobs
from youtube_api import YouTubeAPI


class Manager:
    def __init__(self) -> None:
        self.api = YouTubeAPI()

    # CHANNEL
    def get_channel(self, channel_id=None):
        return self.api.get_channel(channel_id=channel_id)

    def update_channel(self, channel_id, description=None, keywords=None, country=None):
        return self.api.update_channel(channel_id, description, keywords, country)

    # VIDEO
    def get_video(self, video_id):
        return self.api.get_video(video_id)

    def list_my_videos(self, max_results=25):
        return self.api.list_my_videos(max_results)

    def update_video(self, video_id, title=None, description=None, tags=None, category_id=None):
        return self.api.update_video(video_id, title, description, tags, category_id)

    def delete_video(self, video_id):
        return self.api.delete_video(video_id)

    def rate_video(self, video_id, rating):
        return self.api.rate_video(video_id, rating)

    def set_privacy(self, video_id, privacy, publish_at=None):
        return self.api.set_privacy(video_id, privacy, publish_at)

    # UPLOAD (async)
    def upload_video(
        self, source: str, title: str, description: str = "",
        tags: Optional[list[str]] = None, category_id: str = "22",
        privacy: str = "private", publish_at: Optional[str] = None,
    ) -> dict[str, Any]:
        snippet: dict[str, Any] = {"title": title, "description": description,
                                   "categoryId": category_id}
        if tags:
            snippet["tags"] = tags
        status: dict[str, Any] = {"privacyStatus": privacy}
        if publish_at:
            status["privacyStatus"] = "private"
            status["publishAt"] = publish_at
        body = {"snippet": snippet, "status": status}
        refresh_token = auth.current_refresh_token()  # bắt trong request context
        job_id = jobs.submit_upload(refresh_token, source, body)
        return {"job_id": job_id, "status": "pending",
                "hint": "poll bằng youtube_upload_status(job_id)"}

    def upload_status(self, job_id: str) -> dict[str, Any]:
        job = jobs.get_job(job_id)
        if job is None:
            return {"error": f"không có job '{job_id}'"}
        return job

    # SEARCH
    def search(self, q, max_results=25, kind="video"):
        return self.api.search(q, max_results, kind)

    # COMMENTS
    def list_comments(self, video_id, max_results=50):
        return self.api.list_comments(video_id, max_results)

    def get_comment_thread(self, thread_id):
        return self.api.get_comment_thread(thread_id)

    def reply_comment(self, parent_id, text):
        return self.api.reply_comment(parent_id, text)

    def moderate_comment(self, comment_id, status, ban_author=False):
        return self.api.moderate_comment(comment_id, status, ban_author)

    def delete_comment(self, comment_id):
        return self.api.delete_comment(comment_id)

    # PLAYLIST
    def create_playlist(self, title, description="", privacy="private"):
        return self.api.create_playlist(title, description, privacy)

    def list_playlists(self, max_results=25):
        return self.api.list_playlists(max_results)

    def get_playlist(self, playlist_id):
        return self.api.get_playlist(playlist_id)

    def update_playlist(self, playlist_id, title=None, description=None, privacy=None):
        return self.api.update_playlist(playlist_id, title, description, privacy)

    def delete_playlist(self, playlist_id):
        return self.api.delete_playlist(playlist_id)

    def list_playlist_items(self, playlist_id, max_results=50):
        return self.api.list_playlist_items(playlist_id, max_results)

    def add_playlist_item(self, playlist_id, video_id):
        return self.api.add_playlist_item(playlist_id, video_id)

    def remove_playlist_item(self, item_id):
        return self.api.remove_playlist_item(item_id)

    # ANALYTICS
    def video_metrics(self, video_id, start_date, end_date, metrics=None):
        if metrics:
            return self.api.video_metrics(video_id, start_date, end_date, metrics)
        return self.api.video_metrics(video_id, start_date, end_date)

    def channel_metrics(self, start_date, end_date, metrics=None, dimensions=None):
        if metrics:
            return self.api.channel_metrics(start_date, end_date, metrics, dimensions)
        return self.api.channel_metrics(start_date, end_date, dimensions=dimensions)

    def top_videos(self, start_date, end_date, max_results=10):
        return self.api.top_videos(start_date, end_date, max_results)
