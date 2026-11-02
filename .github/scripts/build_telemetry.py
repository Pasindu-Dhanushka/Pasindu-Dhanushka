#!/usr/bin/env python3
"""Build self-hosted SVG telemetry cards for a GitHub profile README.

Only GitHub's official REST API is used. No pip dependencies, third-party
card hosts, or repository secrets beyond the workflow GITHUB_TOKEN are needed.
"""
import html
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen

USERNAME = "Pasindu-Dhanushka"
DEST = Path("assets/telemetry")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
STAMP = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")


def api(path):
    url = "https://api.github.com" + path
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-telemetry-github-action",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def esc(value):
    return html.escape(str(value), quote=True)


def svg_begin(width, height, title, description):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(title)}</title>',
        f'<desc id="desc">{esc(description)}</desc>',
        '<defs><linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0B1528"/><stop offset="1" stop-color="#123047"/></linearGradient></defs>',
        f'<rect width="{width}" height="{height}" rx="18" fill="url(#panel)"/>',
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="17" stroke="#2D536C" stroke-width="2" fill="none"/>',
        f'<rect x="1" y="1" width="{width-2}" height="5" rx="3" fill="#20BED0"/>',
    ]


def text(x, y, value, size=18, fill="#D9ECF8", weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial,sans-serif" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'fill="{fill}">{esc(value)}</text>')


def save(name, elements):
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / name).write_text("\n".join(elements + ["</svg>", ""]), encoding="utf-8")
    print("Created", DEST / name)


def get_repositories():
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{quote(USERNAME)}/repos?per_page=100&page={page}&type=owner")
        repos.extend(batch)
        if len(batch) < 100 or page >= 10:
            break
        page += 1
    return repos


def build_overview(profile, repos):
    own_repos = [repo for repo in repos if not repo.get("fork")]
    stars = sum(int(repo.get("stargazers_count") or 0) for repo in own_repos)
    cards = [
        ("PUBLIC REPOS", profile.get("public_repos", 0), "Visible repositories"),
        ("REPO STARS", stars, "Non-fork public repos"),
        ("FOLLOWERS", profile.get("followers", 0), "GitHub community"),
    ]
    a = svg_begin(920, 252, "Pasindu Dhanushka GitHub profile stats",
                  "Public repository count, stars on original repositories, and follower count.")
    a += [text(33, 43, "GITHUB // PUBLIC TELEMETRY", 17, "#5DE3ED", 700),
          text(33, 70, "Automatically updated using GitHub's official API", 14, "#A8C1D3")]
    for index, (label, number, note) in enumerate(cards):
        x = 32 + index * 297
        a.append(f'<rect x="{x}" y="93" width="277" height="121" rx="12" fill="#13273B" stroke="#2E5D77"/>')
        a.append(text(x+20, 119, label, 13, "#83AFC6", 700))
        a.append(text(x+20, 167, f"{number:,}", 41, "#F1FCFF", 750))
        a.append(text(x+20, 191, note, 12, "#9DBED0"))
    a.append(text(33, 237, "Last refreshed: " + STAMP, 12, "#759AAF"))
    save("overview.svg", a)


def build_languages(repos):
    total = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        if repo.get("size", 0) <= 0:
            continue
        languages = api(f"/repos/{quote(USERNAME)}/{quote(repo['name'])}/languages")
        for lang, count in languages.items():
            total[lang] = total.get(lang, 0) + int(count)
    ranked = sorted(total.items(), key=lambda item: item[1], reverse=True)[:6]
    grand_total = sum(total.values())
    n = max(1, len(ranked))
    height = 123 + n * 47 + 31
    a = svg_begin(920, height, "Languages across Pasindu's public repositories",
                  "GitHub language byte totals for non-fork public repositories.")
    a += [text(33, 43, "LANGUAGES // REPOSITORY CODE", 17, "#5DE3ED", 700),
          text(33, 70, "Source: GitHub language byte counts in public, non-fork repositories", 14, "#A8C1D3")]
    if not ranked:
        a.append(text(35, 126, "No public language data is available yet.", 18))
    for i, (lang, byte_count) in enumerate(ranked):
        y = 111 + i * 47
        pct = byte_count * 100 / grand_total if grand_total else 0
        a += [text(36, y + 4, lang, 16, "#E8F7FF", 600),
              text(880, y + 4, f"{pct:.1f}%", 15, "#A7D6EB", 600, "end"),
              f'<rect x="226" y="{y-12}" rx="6" width="545" height="15" fill="#203A50"/>',
              f'<rect x="226" y="{y-12}" rx="6" width="{max(2, round(545*pct/100))}" height="15" fill="#26C8D9"/>']
    a.append(text(33, height-18, "Last refreshed: " + STAMP + "  |  Not a measurement of proficiency", 12, "#759AAF"))
    save("languages.svg", a)


def main():
    profile = api(f"/users/{quote(USERNAME)}")
    repos = get_repositories()
    build_overview(profile, repos)
    build_languages(repos)
    print("Processed", len(repos), "public repositories")


if __name__ == "__main__":
    main()
