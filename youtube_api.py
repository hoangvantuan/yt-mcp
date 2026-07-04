"""Ruột gọi YouTube Data API v3 + Analytics API v2 qua google-api-python-client.

Mỗi method dựng service từ refresh token trong header request hiện tại (auth.py).
Upload KHÔNG ở đây — chạy async qua jobs.py (manager điều phối).
"""
from typing import Any, Optional

import auth


class YouTubeAPI:
    def _yt(self):
        return auth.get_data_service()

    def _yt_analytics(self):
        return auth.get_analytics_service()

    # ---------------- CHANNEL ----------------
    def get_channel(self, channel_id: Optional[str] = None, mine: bool = False) -> dict[str, Any]:
        params: dict[str, Any] = {
            "part": "snippet,statistics,brandingSettings,contentDetails,status"
        }
        if channel_id:
            params["id"] = channel_id
        else:
            params["mine"] = True  # mặc định "kênh của tôi" (whoami)
        return self._yt().channels().list(**params).execute()

    def update_channel(
        self, channel_id: str, description: Optional[str] = None,
        keywords: Optional[str] = None, country: Optional[str] = None,
    ) -> dict[str, Any]:
        branding: dict[str, Any] = {"channel": {}}
        if description is not None:
            branding["channel"]["description"] = description
        if keywords is not None:
            branding["channel"]["keywords"] = keywords
        if country is not None:
            branding["channel"]["country"] = country
        body = {"id": channel_id, "brandingSettings": branding}
        return self._yt().channels().update(part="brandingSettings", body=body).execute()

    # ---------------- VIDEO ----------------
    def get_video(self, video_id: str) -> dict[str, Any]:
        return self._yt().videos().list(
            part="snippet,status,statistics,contentDetails", id=video_id
        ).execute()

    def list_my_videos(self, max_results: int = 25) -> dict[str, Any]:
        yt = self._yt()
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        items = ch.get("items", [])
        if not items:
            return {"items": []}
        uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        return yt.playlistItems().list(
            part="snippet,contentDetails", playlistId=uploads, maxResults=max_results
        ).execute()

    def update_video(
        self, video_id: str, title: Optional[str] = None,
        description: Optional[str] = None, tags: Optional[list[str]] = None,
        category_id: Optional[str] = None,
    ) -> dict[str, Any]:
        yt = self._yt()
        cur = yt.videos().list(part="snippet", id=video_id).execute()
        if not cur.get("items"):
            raise ValueError(f"Không tìm thấy video '{video_id}'")
        snippet = cur["items"][0]["snippet"]
        if title is not None:
            snippet["title"] = title
        if description is not None:
            snippet["description"] = description
        if tags is not None:
            snippet["tags"] = tags
        if category_id is not None:
            snippet["categoryId"] = category_id
        body = {"id": video_id, "snippet": snippet}
        return yt.videos().update(part="snippet", body=body).execute()

    def delete_video(self, video_id: str) -> dict[str, Any]:
        self._yt().videos().delete(id=video_id).execute()
        return {"deleted": video_id}

    def rate_video(self, video_id: str, rating: str) -> dict[str, Any]:
        self._yt().videos().rate(id=video_id, rating=rating).execute()
        return {"video_id": video_id, "rating": rating}

    def set_privacy(
        self, video_id: str, privacy: str, publish_at: Optional[str] = None
    ) -> dict[str, Any]:
        status: dict[str, Any] = {"privacyStatus": privacy}
        if publish_at is not None:
            status["privacyStatus"] = "private"  # publishAt đòi private
            status["publishAt"] = publish_at
        body = {"id": video_id, "status": status}
        return self._yt().videos().update(part="status", body=body).execute()

    # ---------------- SEARCH ----------------
    def search(self, q: str, max_results: int = 25, kind: str = "video") -> dict[str, Any]:
        return self._yt().search().list(
            part="snippet", q=q, maxResults=max_results, type=kind
        ).execute()

    # ---------------- COMMENTS ----------------
    def list_comments(self, video_id: str, max_results: int = 50) -> dict[str, Any]:
        return self._yt().commentThreads().list(
            part="snippet,replies", videoId=video_id, maxResults=max_results,
            order="time", textFormat="plainText",
        ).execute()

    def get_comment_thread(self, thread_id: str) -> dict[str, Any]:
        return self._yt().commentThreads().list(
            part="snippet,replies", id=thread_id, textFormat="plainText"
        ).execute()

    def reply_comment(self, parent_id: str, text: str) -> dict[str, Any]:
        body = {"snippet": {"parentId": parent_id, "textOriginal": text}}
        return self._yt().comments().insert(part="snippet", body=body).execute()

    def moderate_comment(
        self, comment_id: str, status: str, ban_author: bool = False
    ) -> dict[str, Any]:
        self._yt().comments().setModerationStatus(
            id=comment_id, moderationStatus=status, banAuthor=ban_author
        ).execute()
        return {"comment_id": comment_id, "moderationStatus": status}

    def delete_comment(self, comment_id: str) -> dict[str, Any]:
        self._yt().comments().delete(id=comment_id).execute()
        return {"deleted": comment_id}

    # ---------------- PLAYLIST ----------------
    def create_playlist(
        self, title: str, description: str = "", privacy: str = "private"
    ) -> dict[str, Any]:
        body = {
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": privacy},
        }
        return self._yt().playlists().insert(part="snippet,status", body=body).execute()

    def list_playlists(self, max_results: int = 25) -> dict[str, Any]:
        return self._yt().playlists().list(
            part="snippet,contentDetails,status", mine=True, maxResults=max_results
        ).execute()

    def get_playlist(self, playlist_id: str) -> dict[str, Any]:
        return self._yt().playlists().list(
            part="snippet,contentDetails,status", id=playlist_id
        ).execute()

    def update_playlist(
        self, playlist_id: str, title: Optional[str] = None,
        description: Optional[str] = None, privacy: Optional[str] = None,
    ) -> dict[str, Any]:
        yt = self._yt()
        cur = yt.playlists().list(part="snippet,status", id=playlist_id).execute()
        if not cur.get("items"):
            raise ValueError(f"Không tìm thấy playlist '{playlist_id}'")
        item = cur["items"][0]
        snippet = item["snippet"]
        status = item.get("status", {})
        if title is not None:
            snippet["title"] = title
        if description is not None:
            snippet["description"] = description
        if privacy is not None:
            status["privacyStatus"] = privacy
        body = {"id": playlist_id, "snippet": snippet, "status": status}
        return yt.playlists().update(part="snippet,status", body=body).execute()

    def delete_playlist(self, playlist_id: str) -> dict[str, Any]:
        self._yt().playlists().delete(id=playlist_id).execute()
        return {"deleted": playlist_id}

    def list_playlist_items(self, playlist_id: str, max_results: int = 50) -> dict[str, Any]:
        return self._yt().playlistItems().list(
            part="snippet,contentDetails", playlistId=playlist_id, maxResults=max_results
        ).execute()

    def add_playlist_item(self, playlist_id: str, video_id: str) -> dict[str, Any]:
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        }
        return self._yt().playlistItems().insert(part="snippet", body=body).execute()

    def remove_playlist_item(self, item_id: str) -> dict[str, Any]:
        self._yt().playlistItems().delete(id=item_id).execute()
        return {"deleted": item_id}

    # ---------------- ANALYTICS ----------------
    def video_metrics(
        self, video_id: str, start_date: str, end_date: str,
        metrics: str = "views,estimatedMinutesWatched,averageViewDuration,likes,comments",
    ) -> dict[str, Any]:
        return self._yt_analytics().reports().query(
            ids="channel==MINE", startDate=start_date, endDate=end_date,
            metrics=metrics, filters=f"video=={video_id}",
        ).execute()

    def channel_metrics(
        self, start_date: str, end_date: str,
        metrics: str = "views,estimatedMinutesWatched,subscribersGained,subscribersLost",
        dimensions: Optional[str] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "ids": "channel==MINE", "startDate": start_date,
            "endDate": end_date, "metrics": metrics,
        }
        if dimensions:
            params["dimensions"] = dimensions
        return self._yt_analytics().reports().query(**params).execute()

    def top_videos(
        self, start_date: str, end_date: str, max_results: int = 10
    ) -> dict[str, Any]:
        return self._yt_analytics().reports().query(
            ids="channel==MINE", startDate=start_date, endDate=end_date,
            metrics="views,estimatedMinutesWatched", dimensions="video",
            sort="-views", maxResults=max_results,
        ).execute()
