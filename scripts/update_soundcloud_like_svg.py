import os
import re
import random
import html as htmllib
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# local .env support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

USERNAME = os.environ["SOUNDCLOUD_USERNAME"]
POOL = int(os.environ.get("SOUNDCLOUD_POOL", "20"))      # sample from N most recent likes
SEED = os.environ.get("SOUNDCLOUD_SEED", "")             # optional deterministic randomness
SVG_PATH = os.environ.get("SVG_PATH", "assets/soundcloud-like.svg")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; github-readme-bot/1.0)"}


def fetch_likes_page(username: str) -> str:
    url = f"https://soundcloud.com/{username}/likes"
    r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return r.text


def extract_likes_from_html(page_html: str, limit: int):
    soup = BeautifulSoup(page_html, "lxml")
    tracks = []

    for article in soup.select("article"):
        title_a = article.select_one('h2[itemprop="name"] a[itemprop="url"]')
        if not title_a:
            continue

        rel_track = title_a.get("href", "").strip()
        title = htmllib.unescape(title_a.get_text(" ", strip=True))

        # "by <a>Artist</a>" is usually the next <a> inside the same <h2>
        h2 = title_a.find_parent("h2")
        artist_a = None
        if h2:
            for a in h2.find_all("a", href=True):
                if a is not title_a:
                    artist_a = a
                    break

        artist = htmllib.unescape(artist_a.get_text(" ", strip=True)) if artist_a else "Unknown"
        track_url = rel_track if rel_track.startswith("http") else f"https://soundcloud.com{rel_track}"

        tracks.append({"title": title, "artist": artist, "url": track_url})
        if len(tracks) >= limit:
            break

    return tracks


def pick_random_track(tracks):
    if not tracks:
        return None
    if SEED:
        random.seed(SEED)
    else:
        random.seed()
    return random.choice(tracks)


def xml_escape(s: str) -> str:
    # Escape for XML text nodes/attributes
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))


def truncate(s: str, max_chars: int) -> str:
    s = s.strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def make_svg_card(username: str, track: dict | None) -> str:
    # Card size
    W, H = 720, 190

    bg = "#0B0B0B"
    panel = "#111111"
    border = "#1F1F1F"
    text = "#F5F5F5"
    muted = "#B3B3B3"
    orange = "#FF5500"

    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    if track is None:
        title = "No public likes found"
        artist = f"@{username}"
        url = f"https://soundcloud.com/{username}/likes"
        subtitle = "Make sure your Likes page is public."
    else:
        title = truncate(track["title"], 48)
        artist = truncate(track["artist"], 36)
        url = track["url"]
        subtitle = f"Recently played"

    title_xml = xml_escape(title)
    artist_xml = xml_escape(artist)
    subtitle_xml = xml_escape(subtitle)
    url_xml = xml_escape(url)
    user_xml = xml_escape(username)
    stamp_xml = xml_escape(stamp)

    # simple “waveform” bars (static but looks SoundCloud-y)
    bars = []
    bar_x = 28
    heights = [10, 26, 14, 34, 18, 42, 22, 30, 12, 38, 16, 28, 20, 44, 14, 26, 10]
    for i, bh in enumerate(heights):
        x = bar_x + i * 10
        y = 34 + (44 - bh)
        bars.append(f'<rect x="{x}" y="{y}" width="6" height="{bh}" rx="3" fill="{orange}" opacity="0.75"/>')
    bars_svg = "\n        ".join(bars)

    # --- layout tuning knobs ---
    CONTENT_OFFSET = 10          # pushes title/artist down (try 6–16)
    HEADER_Y = 34                # baseline for "SOUNDCLOUD" + username
    TITLE_Y = 104 + CONTENT_OFFSET
    ARTIST_Y = 132 + CONTENT_OFFSET
    FOOTER_Y = H - 26            # anchors footer near bottom (kills empty bottom space)
    WAVEFORM_OFFSET_Y = 10   # try 8–16

    # Make whole card clickable via <a>
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="SoundCloud random recent like">
    <defs>
        <linearGradient id="bgGrad" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0" stop-color="{panel}"/>
        <stop offset="1" stop-color="{bg}"/>
        </linearGradient>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#000" flood-opacity="0.45"/>
        </filter>
    </defs>

    <a href="{url_xml}" target="_blank" rel="noopener noreferrer">
        <rect x="12" y="12" width="{W-24}" height="{H-24}" rx="18" fill="url(#bgGrad)" stroke="{border}" filter="url(#shadow)"/>

        <!-- Header -->
        <text x="28" y="{HEADER_Y}" fill="{orange}" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="14" font-weight="800" letter-spacing="0.2">
        SOUNDCLOUD
        </text>
        <text x="{W-28}" y="{HEADER_Y}" fill="{muted}" text-anchor="end" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="12" font-weight="600">
        @{user_xml}
        </text>

        <!-- Waveform accent -->
        <g transform="translate(0,{WAVEFORM_OFFSET_Y})">
        {bars_svg}
        </g>

        <!-- Title / Artist -->
        <text x="28" y="{TITLE_Y}" fill="{text}" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="22" font-weight="800">
        {title_xml}
        </text>
        <text x="28" y="{ARTIST_Y}" fill="{muted}" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="14" font-weight="650">
        {artist_xml}
        </text>

        <!-- Footer (anchored to bottom) -->
        <text x="28" y="{FOOTER_Y}" fill="{muted}" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="12">
        {subtitle_xml}
        </text>
        <text x="{W-28}" y="{FOOTER_Y}" fill="{muted}" text-anchor="end" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="12">
        Updated {stamp_xml}
        </text>

    </a>
    </svg>
    '''

    return svg


def main():
    # Ensure output directory exists
    os.makedirs(os.path.dirname(SVG_PATH) or ".", exist_ok=True)

    page = fetch_likes_page(USERNAME)
    tracks = extract_likes_from_html(page, POOL)
    track = pick_random_track(tracks)

    print(f"Extracted {len(tracks)} tracks from likes page.")

    svg = make_svg_card(USERNAME, track)
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Wrote SVG to {SVG_PATH}")


if __name__ == "__main__":
    main()
