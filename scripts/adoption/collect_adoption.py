#!/usr/bin/env python3
"""Collect aggregate public GHCR counters; never pull images or infer users."""
import datetime as dt
import json
import os
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

REPO = "CaneTLOTW/ha-codex"
PACKAGES = ("ha-codex", "amd64-ha-codex", "aarch64-ha-codex")
ROOT = Path("stats/adoption")
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:-dev\.\d+)?$")
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
COUNT = re.compile(r"(?<![\w.,])(\d[\d,]*)\s+Version downloads\b", re.I)

class Node:
    def __init__(self, tag="", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def text(self):
        return " ".join(c.text() if isinstance(c, Node) else c for c in self.children)
    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.walk()

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)
    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break
    def handle_data(self, data):
        if data.strip():
            self.stack[-1].children.append(data.strip())

def parse(html):
    p = Parser()
    p.feed(html)
    nodes = list(p.root.walk())
    total = set()
    daily = {}
    versions = {}
    for n in nodes:
        if n.attrs.get("data-date") and n.attrs.get("data-merge-count"):
            date = n.attrs["data-date"]
            count = n.attrs["data-merge-count"]
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) and count.isdigit():
                if date in daily and daily[date] != int(count):
                    raise ValueError("conflicting chart values")
                daily[date] = int(count)
        if n.tag == "div" and "lh-condensed" in n.attrs.get("class", "").split():
            spans = [a for a in n.walk() if a.tag == "span" and a.text().strip() == "Total downloads"]
            headings = [a.attrs.get("title", "") for a in n.walk() if a.tag == "h3"]
            if spans:
                for h in headings:
                    if re.fullmatch(r"\d[\d,]*", h):
                        total.add(int(h.replace(",", "")))
    # Smallest enclosing element containing a single count, digest and version-tag anchor.
    for n in reversed(nodes):
        if n.tag not in ("div", "li", "tr"):
            continue
        s = n.text()
        if len(s) > 3500:
            continue
        counts = COUNT.findall(s)
        digests = set(DIGEST.findall(s))
        tags = sorted({a.text().strip() for a in n.walk()
                       if a.tag == "a" and VERSION.fullmatch(a.text().strip())})
        if len(counts) != 1 or len(digests) != 1 or not tags:
            continue
        digest = next(iter(digests))
        count = int(counts[0].replace(",", ""))
        if digest in versions and versions[digest]["downloads"] != count:
            raise ValueError("conflicting version counts")
        row = versions.setdefault(digest, {"tags": [], "downloads": count})
        row["tags"] = sorted(set(row["tags"] + tags))
    if len(total) > 1:
        raise ValueError("conflicting total downloads")
    return {"total": next(iter(total), None), "daily": daily, "versions": versions}

def get(url, token=None):
    headers = {"User-Agent": "HA-Codex-adoption-stats/1.0"}
    if token:
        headers.update({"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as res:
        return res.read(8_000_001).decode("utf-8")

def fetch_package(name):
    url = f"https://github.com/{REPO}/pkgs/container/{name}"
    result = {"total": None, "daily": {}, "versions": {}, "errors": []}
    for target in (url, url + "/versions?filters%5Bversion_type%5D=tagged",
                   url + "/versions?filters%5Bversion_type%5D=tagged&page=2"):
        try:
            data = parse(get(target))
            if target == url:
                result["total"] = data["total"]
                result["daily"] = data["daily"]
                if data["total"] is None:
                    result["errors"].append("total unavailable")
            result["versions"].update(data["versions"])
        except Exception as exc:
            result["errors"].append(type(exc).__name__ + " collecting " + ("overview" if target == url else "versions"))
    if not result["versions"]:
        result["errors"].append("no tagged version counts parsed")
    return result

def api(path):
    return json.loads(get("https://api.github.com/repos/" + REPO + path, os.getenv("GH_TOKEN")))

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def show(x):
    return "unavailable" if x is None else f"{x:,}"

def delta(current, prior):
    if current is None or prior is None or current < prior:
        return None
    return current - prior

def main():
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    snap = {"collected_at": now.isoformat(), "packages": {n: fetch_package(n) for n in PACKAGES}}
    try:
        r = api("")
        snap["repo"] = {"stars": r["stargazers_count"], "forks": r["forks_count"]}
    except Exception as exc:
        snap["repo"] = {"error": type(exc).__name__}
    # Aggregate daily traffic only; never retain IPs, referrers, paths or credentials.
    for key in ("views", "clones"):
        try:
            r = api("/traffic/" + key)
            snap[key] = {"days": r[key], "count": r["count"], "uniques": r["uniques"]}
        except Exception as exc:
            snap[key] = {"error": type(exc).__name__}
    save(ROOT / "snapshots" / (str(today) + ".json"), snap)
    save(ROOT / "latest.json", snap)
    lines = ["# HA-Codex adoption statistics", "", "Collected (UTC): " + snap["collected_at"], "",
             "**Registry download events, not unique users or installations.** Stable and Developer share packages.",
             "", "| Package | Total | 7-day change | 30-day change | 90-day change |", "|---|---:|---:|---:|---:|"]
    for name, data in snap["packages"].items():
        values = [show(data["total"])]
        for days in (7, 30, 90):
            path = ROOT / "snapshots" / (str(today - dt.timedelta(days=days)) + ".json")
            prior = json.loads(path.read_text())["packages"][name]["total"] if path.exists() else None
            values.append(show(delta(data["total"], prior)))
        lines.append("| " + name + " | " + " | ".join(values) + " |")
    lines += ["", "Architecture packages are shown separately; never sum them with the multiarch package.",
              "", "## Recent version counters (first two tagged pages, grouped by digest)", "",
              "| Package | Channel | Version tags | Downloads |", "|---|---|---|---:|"]
    for name, data in snap["packages"].items():
        for digest, row in sorted(data["versions"].items(), key=lambda item: tuple(int(x) for x in re.findall(r"\d+", item[1]["tags"][0])), reverse=True):
            channels = {"Developer" if "-dev." in tag else "Stable" for tag in row["tags"]}
            lines.append(f"| {name} | {' / '.join(sorted(channels))} | {', '.join(row['tags'])} | {show(row['downloads'])} |")
    lines += ["", "## Repository", "", "Stars: " + show(snap["repo"].get("stars")) + "; forks: " + show(snap["repo"].get("forks")) + "."]
    for key in ("views", "clones"):
        lines.append(f"- {key} (GitHub rolling window): {show(snap[key].get('count'))}, unique within window: {show(snap[key].get('uniques'))}.")
    lines += ["", "## Data quality", "", "Missing/failed counters are unavailable, never zero. GitHub counts can lag or reset; a zero change is not evidence of zero users. Historical changes need exact dated snapshots. Version coverage is limited; aliases share digests."]
    for name, data in snap["packages"].items():
        if data["errors"]:
            lines.append("- " + name + ": " + "; ".join(data["errors"]))
    lines += ["", "[Methodology](../../docs/ADOPTION_STATISTICS.md)", ""]
    (ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    total = snap["packages"]["ha-codex"]["total"]
    save(ROOT / "badge.json", {"schemaVersion": 1, "label": "GHCR downloads", "message": show(total), "color": "blue" if total is not None else "lightgrey"})
    print("\n".join(lines))

if __name__ == "__main__":
    main()
