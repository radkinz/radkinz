import os
import re
import random
import html as htmllib
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# Optional local .env support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

USERNAME = os.environ["SOUNDCLOUD_USERNAME"]
POOL = int(os.environ.get("SOUNDCLOUD_POOL", "20"))      # sample from N most recent likes
SEED = os.environ.get("SOUNDCLOUD_SEED", "")             # optional deterministic randomness
README_PATH = os.environ.get("README_PATH", "README.md")
SVG_PATH = os.environ.get("SVG_PATH", "assets/soundcloud-like.svg")

START_MARKER = "<!-- SC_LIKES:START -->"
END_MARKER = "<!-- SC_LIKES:END -->"

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
    W, H = 720, 160

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
        subtitle = f"Random pick from your last {min(POOL, 999)} likes"

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
        bars.append(f'<rect x="{x}" y="{y}" width="6" height="{bh}" rx="3" fill="{orange}" opacity="0.95"/>')
    bars_svg = "\n        ".join(bars)

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

  <a href="{url_xml}" target="_blank">
    <rect x="12" y="12" width="{W-24}" height="{H-24}" rx="18" fill="url(#bgGrad)" stroke="{border}" filter="url(#shadow)"/>

    <!-- Header -->
    <text x="28" y="34" fill="{orange}" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="14" font-weight="800" letter-spacing="0.2">
      SOUNDCLOUD
    </text>
    <text x="{W-28}" y="34" fill="{muted}" text-anchor="end" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="12" font-weight="600">
      @{user_xml}
    </text>

    <!-- Waveform accent -->
    <g transform="translate(0,0)">
      {bars_svg}
    </g>

    <!-- Title / Artist -->
    <text x="28" y="92" fill="{text}" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="22" font-weight="800">
      {title_xml}
    </text>
    <text x="28" y="118" fill="{muted}" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="14" font-weight="650">
      {artist_xml}
    </text>

    <!-- Footer -->
    <text x="28" y="142" fill="{muted}" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="12">
      {subtitle_xml}
    </text>
    <text x="{W-28}" y="142" fill="{muted}" text-anchor="end" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="12">
      Updated {stamp_xml}
    </text>

    <!-- Orange corner tag -->
    <path d="M{W-70} 24 L{W-24} 24 L{W-24} 70 Z" fill="{orange}" opacity="0.9"/>
    <text x="{W-34}" y="46" fill="#111" text-anchor="end" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" font-size="12" font-weight="900">♥</text>
  </a>
</svg>
'''
    return svg


def replace_readme_block(readme_text: str, svg_rel_path: str) -> str:
    content = f"![SoundCloud]({svg_rel_path})"
    pattern = re.compile(re.escape(START_MARKER) + r"[\s\S]*?" + re.escape(END_MARKER))
    if not pattern.search(readme_text):
        raise RuntimeError(f"README markers not found: {START_MARKER} ... {END_MARKER}")
    return pattern.sub(f"{START_MARKER}\n{content}\n{END_MARKER}", readme_text)


def main():
    # Ensure assets dir exists
    os.makedirs(os.path.dirname(SVG_PATH) or ".", exist_ok=True)

    page = fetch_likes_page(USERNAME)
    tracks = extract_likes_from_html(page, POOL)
    track = pick_random_track(tracks)

    svg = make_svg_card(USERNAME, track)
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(svg)

    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    # Use a relative path for README embed
    svg_rel = "./" + SVG_PATH.replace("\\", "/").lstrip("./")
    updated = replace_readme_block(readme, svg_rel)

    if updated != readme:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated)

    print(f"Wrote SVG: {SVG_PATH}")
    print("README block ensured.")


if __name__ == "__main__":
    main()
