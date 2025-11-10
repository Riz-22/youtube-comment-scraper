import logging
from typing import Any, Dict, List, Optional

import requests

from .comment_utils import (
    build_comment_record,
    parse_youtube_video_id,
)

YOUTUBE_COMMENTS_API_URL = "https://www.googleapis.com/youtube/v3/commentThreads"

class YoutubeCommentScraper:
    """
    Scrapes comments from YouTube videos using the YouTube Data API v3.
    Requires a valid API key with access to the YouTube Data API.
    """

    def __init__(
        self,
        api_key: str,
        max_comments_per_video: int = 200,
        request_timeout: int = 10,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.api_key = api_key
        self.max_comments_per_video = max_comments_per_video
        self.request_timeout = request_timeout
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def fetch_comments_for_url(self, url: str) -> List[Dict[str, Any]]:
        """
        Fetch all comments (top-level + first-level replies) for a given YouTube video URL.
        """
        video_id = parse_youtube_video_id(url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL, could not extract video ID: {url}")

        comments: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None
        fetched_count = 0

        while True:
            remaining = self.max_comments_per_video - fetched_count
            if remaining <= 0:
                break

            batch_size = min(100, remaining)

            params = {
                "part": "snippet,replies",
                "videoId": video_id,
                "maxResults": batch_size,
                "textFormat": "plainText",
                "key": self.api_key,
            }
            if next_page_token:
                params["pageToken"] = next_page_token

            try:
                resp = requests.get(
                    YOUTUBE_COMMENTS_API_URL,
                    params=params,
                    timeout=self.request_timeout,
                )
            except requests.RequestException as e:
                self.logger.error("Network error while calling YouTube API: %s", e)
                break

            if resp.status_code != 200:
                self.logger.error(
                    "YouTube API error (%s): %s",
                    resp.status_code,
                    resp.text,
                )
                break

            payload = resp.json()

            items = payload.get("items", [])
            if not items:
                break

            for item in items:
                thread_id = item.get("id")
                snippet = (item.get("snippet") or {}).get("topLevelComment", {}).get(
                    "snippet", {}
                )
                top_comment_id = (item.get("snippet") or {}).get(
                    "topLevelComment", {}
                ).get("id")

                if snippet and top_comment_id:
                    comments.append(
                        build_comment_record(
                            snippet=snippet,
                            comment_id=top_comment_id,
                            reply_level=0,
                            reply_count=(item.get("snippet") or {}).get(
                                "totalReplyCount", 0
                            ),
                            input_url=url,
                            thread_id=thread_id,
                        )
                    )
                    fetched_count += 1

                # Process first-level replies if present
                replies_block = item.get("replies", {})
                reply_items = replies_block.get("comments", []) or []

                for reply in reply_items:
                    if fetched_count >= self.max_comments_per_video:
                        break

                    reply_snippet = reply.get("snippet", {})
                    reply_comment_id = reply.get("id")
                    if not reply_snippet or not reply_comment_id:
                        continue

                    comments.append(
                        build_comment_record(
                            snippet=reply_snippet,
                            comment_id=reply_comment_id,
                            reply_level=1,
                            reply_count=0,
                            input_url=url,
                            thread_id=thread_id,
                        )
                    )
                    fetched_count += 1

            next_page_token = payload.get("nextPageToken")
            if not next_page_token:
                break

        self.logger.debug(
            "Fetched %d comment(s) for video %s (%s)", fetched_count, video_id, url
        )
        return comments