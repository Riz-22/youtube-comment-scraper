import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

YOUTUBE_URL_PATTERNS = [
    # Standard watch URL
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&/?#]+)",
    # Short URL
    r"(?:https?://)?youtu\.be/([^&/?#]+)",
    # Shorts URL
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([^&/?#]+)",
    # Live
    r"(?:https?://)?(?:www\.)?youtube\.com/live/([^&/?#]+)",
]

def parse_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract a YouTube video ID from various URL formats.
    Returns None if no valid ID is found.
    """
    if not isinstance(url, str):
        return None

    for pattern in YOUTUBE_URL_PATTERNS:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            logger.debug("Extracted video ID %s from URL %s", video_id, url)
            return video_id

    logger.warning("Could not extract video ID from URL: %s", url)
    return None

def validate_youtube_url(url: str) -> bool:
    """
    Quick validation check that a string looks like a YouTube URL with a video ID.
    """
    return parse_youtube_video_id(url) is not None

def _safe_get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Safely navigate nested dictionaries using a dot-separated path.
    """
    current: Any = d
    for part in path.split("."):
        if not isinstance(current, dict):
            return default
        current = current.get(part, default)
    return current

def _format_like_count(value: Any) -> Any:
    """
    Convert integer like count to a compact human-readable form (e.g., 5300 -> '5.3K').
    If conversion fails, the original value is returned.
    """
    try:
        num = int(value)
    except (TypeError, ValueError):
        return value

    thresholds = [
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    ]
    for threshold, suffix in thresholds:
        if num >= threshold:
            formatted = f"{num / threshold:.1f}{suffix}"
            # Strip trailing .0 for nicer output
            return formatted.replace(".0", "")
    return num

def _derive_heart_tooltip(snippet: Dict[str, Any]) -> Optional[str]:
    """
    Approximate whether the comment has been hearted by the creator.
    The YouTube Data API exposes a 'viewerRating' field, but creator hearts
    are not perfectly represented, so this is an approximation.
    """
    viewer_rating = snippet.get("viewerRating")
    if viewer_rating and viewer_rating.lower() != "none":
        return "Creator reacted"
    # Some APIs expose 'moderationStatus' or 'canRate'; we keep this simple.
    return None

def build_comment_record(
    snippet: Dict[str, Any],
    comment_id: str,
    reply_level: int,
    reply_count: int,
    input_url: str,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Normalize a raw YouTube API comment snippet into the schema documented
    in the project README.
    """
    author_channel_id = _safe_get(snippet, "authorChannelId.value")
    display_name = snippet.get("authorDisplayName")
    avatar_url = snippet.get("authorProfileImageUrl")
    is_verified = bool(snippet.get("authorChannelIsVerified"))

    like_count = _format_like_count(snippet.get("likeCount"))
    published_at = snippet.get("publishedAt") or snippet.get("updatedAt")

    heart_tooltip = _derive_heart_tooltip(snippet)

    record: Dict[str, Any] = {
        "commentText": snippet.get("textDisplay") or snippet.get("textOriginal"),
        "author": {
            "channelId": author_channel_id,
            "displayName": display_name,
            "avatarThumbnailUrl": avatar_url,
            "isVerified": is_verified,
        },
        "commentId": comment_id,
        "publishedTime": published_at,
        "replyLevel": reply_level,
        "likeCountLiked": like_count,
        "replyCount": reply_count,
        "heartActiveTooltip": heart_tooltip,
        "inputUrl": input_url,
    }

    if thread_id:
        record["threadId"] = thread_id

    return record