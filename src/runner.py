import json
from youtube_comment_scraper.extractors.youtube_parser import parse_youtube_comments
from youtube_comment_scraper.outputs.exporters import export_comments

def main():
    video_url = "https://www.youtube.com/watch?v=example_video"
    comments = parse_youtube_comments(video_url, limit=10, include_replies=True)
    export_comments(comments, output_format='json')

if __name__ == "__main__":
    main()