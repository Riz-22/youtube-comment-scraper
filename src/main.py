import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

# Ensure local src imports work when running from project root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from extractors.youtube_parser import YoutubeCommentScraper  # type: ignore
from outputs.data_exporter import export_all  # type: ignore
from extractors.comment_utils import validate_youtube_url  # type: ignore

def load_settings(config_path: str) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        settings = json.load(f)

    # Basic validation and sensible defaults
    settings.setdefault("youtubeApiKey", "")
    settings.setdefault("maxCommentsPerVideo", 200)
    settings.setdefault("logLevel", "INFO")
    settings.setdefault("outputDirectory", "data")
    settings.setdefault("outputFormats", ["json", "csv", "xlsx"])
    settings.setdefault("requestTimeoutSeconds", 10)
    settings.setdefault("concurrentRequests", 1)

    return settings

def load_input_urls(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input URLs file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "urls" in data:
        urls = data["urls"]
    elif isinstance(data, list):
        urls = data
    else:
        raise ValueError(
            "Input URLs file must be a JSON array of URLs or an object with a 'urls' key."
        )

    if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
        raise ValueError("All URLs must be strings.")

    valid_urls = [u for u in urls if validate_youtube_url(u)]
    invalid_count = len(urls) - len(valid_urls)
    if invalid_count:
        logging.warning("Skipped %d invalid YouTube URL(s).", invalid_count)

    return valid_urls

def configure_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="YouTube Comment Scraper - scrape comments from multiple videos."
    )
    default_config = os.path.join(CURRENT_DIR, "config", "settings.example.json")
    default_input = os.path.join(os.path.dirname(CURRENT_DIR), "data", "input_urls.sample.json")

    parser.add_argument(
        "--config",
        "-c",
        default=default_config,
        help=f"Path to settings JSON file (default: {default_config})",
    )
    parser.add_argument(
        "--input",
        "-i",
        default=default_input,
        help=f"Path to JSON file with input URLs (default: {default_input})",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="Override output directory defined in config.",
    )
    parser.add_argument(
        "--max-comments",
        "-m",
        type=int,
        default=None,
        help="Override max comments per video defined in config.",
    )

    return parser.parse_args()

def main() -> None:
    args = parse_args()

    settings = load_settings(args.config)
    configure_logging(settings.get("logLevel", "INFO"))

    logger = logging.getLogger("main")

    if not settings.get("youtubeApiKey"):
        logger.error(
            "YouTube API key is missing in settings. Please set 'youtubeApiKey' in the config file."
        )
        sys.exit(1)

    max_comments = args.max_comments or settings.get("maxCommentsPerVideo", 200)
    output_dir = args.output_dir or settings.get("outputDirectory", "data")
    output_formats = settings.get("outputFormats", ["json", "csv", "xlsx"])
    request_timeout = settings.get("requestTimeoutSeconds", 10)

    try:
        urls = load_input_urls(args.input)
    except Exception as e:
        logger.exception("Failed to load input URLs: %s", e)
        sys.exit(1)

    if not urls:
        logger.error("No valid YouTube URLs provided. Exiting.")
        sys.exit(1)

    logger.info("Loaded %d URL(s) to scrape.", len(urls))

    scraper = YoutubeCommentScraper(
        api_key=settings["youtubeApiKey"],
        max_comments_per_video=max_comments,
        request_timeout=request_timeout,
        logger=logging.getLogger("YoutubeCommentScraper"),
    )

    all_comments: List[Dict[str, Any]] = []

    for url in urls:
        logger.info("Scraping comments for: %s", url)
        try:
            comments = scraper.fetch_comments_for_url(url)
            logger.info("Fetched %d comments from %s", len(comments), url)
            all_comments.extend(comments)
        except Exception as e:
            logger.exception("Failed to scrape comments for %s: %s", url, e)

    if not all_comments:
        logger.warning("No comments were scraped. Nothing to export.")
        return

    os.makedirs(output_dir, exist_ok=True)
    base_filename = "youtube_comments"

    try:
        export_all(
            output_dir=output_dir,
            base_filename=base_filename,
            comments=all_comments,
            formats=output_formats,
        )
        logger.info(
            "Export complete. Generated formats: %s in directory: %s",
            ", ".join(output_formats),
            output_dir,
        )
    except Exception as e:
        logger.exception("Failed to export data: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()