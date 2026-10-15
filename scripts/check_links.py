#!/usr/bin/env python3
"""Crawl the static site for dead links (ticket 07).

Checks, without any dependency:
  - every #fragment href has a matching id in index.html
  - every relative href/src resolves to a file under site/
  - every absolute https URL from config.js (repo, site) plus the
    repo-file and issue-template links app.js builds at runtime
    returns HTTP 200 (skipped with a warning if there is no network)

Usage:  python3 scripts/check_links.py           # checks site/ as built
Exit nonzero if any local link is dead or any remote link fails.
"""
from __future__ import annotations

import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(HERE, "site")

INDEX = open(os.path.join(SITE, "index.html")).read()
APPJS = open(os.path.join(SITE, "app.js")).read()
CONFIG = open(os.path.join(SITE, "config.js")).read()
RULESJS = open(os.path.join(SITE, "rules.js")).read()

failures: list[str] = []
warnings: list[str] = []


def check_url(url: str) -> bool | None:
    """True = alive, False = dead, None = could not reach (no network)."""
    for attempt in (0, 1):  # one retry: hosts occasionally 404 a lone HEAD
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "thesis-er-linkcheck"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status < 400
        except Exception as e:  # noqa: BLE001 - any failure mode reported the same way
            if "URLError" in type(e).__name__:
                return None
            if attempt == 0:
                time.sleep(3)
                continue
            return False
    return False


def main() -> int:
    ids = set(re.findall(r'id="([^"]+)"', INDEX))

    # 1. fragments
    for frag in sorted(set(re.findall(r'href="#([^"]*)"', INDEX))):
        if frag and frag not in ids:
            failures.append(f"fragment #{frag} has no matching id")

    # 2. relative links (href/src to files)
    for url in sorted(set(re.findall(r'(?:href|src)="([^"#]+?)"', INDEX))):
        if re.match(r"https?:|mailto:|data:", url) or url.startswith("#") or url == "":
            continue
        if not os.path.isfile(os.path.join(SITE, url.lstrip("/"))):
            failures.append(f"relative link {url} resolves to no file under site/")

    # 3. remote links: config URLs + everything app.js builds at runtime
    repo = re.search(r'REPO_URL\s*=\s*"([^"]+)"', CONFIG).group(1)
    remote = {repo, repo + "/issues/new?template=rule-correction.md",
              repo + "/issues/new?template=university-request.md",
              repo + "/blob/main/RULES.md", repo + "/blob/main/README.md",
              repo + "/blob/main/CONTRIBUTING.md",
              repo + "/blob/main/universities/README.md",
              "https://portfolio-sepia-six-18.vercel.app",
              "https://github.com/mogiiee"}
    site_url = re.search(r'SITE_URL\s*=\s*"([^"]+)"', CONFIG)
    if site_url and site_url.group(1):
        remote.add(site_url.group(1))
    for url in sorted(remote):
        alive = check_url(url)
        if alive is None:
            warnings.append(f"no network: could not verify {url}")
        elif not alive:
            failures.append(f"remote link dead: {url}")
        else:
            print(f"  ok {url}")

    # 4. rules.js must parse and agree with RULES.md
    n_rules_md = len(re.findall(r"^- \*\*", open(os.path.join(HERE, "RULES.md")).read(),
                                re.M))
    m = re.search(r"RULE_COUNT = (\d+)", RULESJS)
    if not m or int(m.group(1)) != n_rules_md:
        failures.append("site/rules.js RULE_COUNT disagrees with RULES.md")
    if 'data-rule-count' not in INDEX:
        failures.append("index.html has no data-rule-count fallbacks")

    for w in warnings:
        print(f"warning: {w}")
    if failures:
        print("DEAD LINKS:")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print("check_links: all site links alive" +
          (" (remote checks skipped: no network)" if warnings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
