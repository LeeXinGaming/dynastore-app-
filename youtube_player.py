from __future__ import annotations

import sys
import urllib.parse

import webview


def valid_youtube_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").casefold()
    return parsed.scheme == "https" and host in {
        "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    }


def main() -> int:
    if len(sys.argv) != 2 or not valid_youtube_url(sys.argv[1]):
        return 2
    webview.create_window(
        "DYNA-STORE YouTube Player",
        url=sys.argv[1],
        width=1100,
        height=700,
        min_size=(720, 480),
        background_color="#080808",
        text_select=False,
    )
    webview.start(gui="edgechromium", private_mode=False, storage_path=".quickplay_webview")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
