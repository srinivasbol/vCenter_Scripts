#!/usr/bin/env python3
"""Ingest IAM/storage/datacenter trend signals into a normalized JSON dataset."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import arxiv
import feedparser
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUERY = (
    '"identity and access management" OR "distributed storage" OR "datacenter engineering" '
    'OR "zero trust" OR "NVMe-oF" OR "CXL memory" OR "GPU thermal throttling"'
)

DEFAULT_FEEDS = [
    "https://blog.cloudflare.com/rss/",
    "https://netflixtechblog.com/feed",
    "https://engineering.fb.com/feed/",
    "https://security.googleblog.com/feeds/posts/default?alt=rss",
]


@dataclass
class TrendRecord:
    title: str
    summary: str
    url: str
    source: str
    published: str | None = None
    tags: list[str] | None = None


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_arxiv(query: str, max_results: int) -> list[TrendRecord]:
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )
    records: list[TrendRecord] = []
    for result in client.results(search):
        records.append(
            TrendRecord(
                title=result.title.strip(),
                summary=(result.summary or "").strip(),
                url=result.entry_id,
                source="arXiv",
                published=result.published.isoformat() if result.published else None,
                tags=[c for c in result.categories],
            )
        )
    return records


def fetch_rss(feeds: list[str], per_feed: int) -> list[TrendRecord]:
    records: list[TrendRecord] = []
    for feed_url in feeds:
        response = requests.get(feed_url, timeout=30)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        source = parsed.feed.get("title", feed_url)
        for entry in parsed.entries[:per_feed]:
            records.append(
                TrendRecord(
                    title=entry.get("title", "untitled"),
                    summary=(entry.get("summary", "") or entry.get("description", ""))[:1200],
                    url=entry.get("link", feed_url),
                    source=f"RSS:{source}",
                    published=entry.get("published"),
                    tags=[t.get("term", "") for t in entry.get("tags", []) if t.get("term")],
                )
            )
    return records


def fetch_reddit(query: str, limit: int) -> list[TrendRecord]:
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "research-fellow-trend-ingestor/1.0")

    if not (client_id and client_secret):
        return []

    token_resp = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": user_agent},
        timeout=30,
    )
    token_resp.raise_for_status()
    token = token_resp.json().get("access_token")
    if not token:
        return []
    auth_header = {"Authorization": "Bearer " + token, "User-Agent": user_agent}

    search_resp = requests.get(
        "https://oauth.reddit.com/search",
        headers=auth_header,
        params={"q": query, "sort": "new", "limit": limit, "type": "link"},
        timeout=30,
    )
    search_resp.raise_for_status()

    records: list[TrendRecord] = []
    for child in search_resp.json().get("data", {}).get("children", []):
        data = child.get("data", {})
        records.append(
            TrendRecord(
                title=data.get("title", "untitled"),
                summary=(data.get("selftext", "") or "")[:1200],
                url=f"https://reddit.com{data.get('permalink', '')}",
                source=f"Reddit:r/{data.get('subreddit', 'unknown')}",
                published=datetime.fromtimestamp(data.get("created_utc", 0), tz=timezone.utc).isoformat()
                if data.get("created_utc")
                else None,
                tags=["reddit", data.get("subreddit", "")],
            )
        )
    return records


def fetch_github_discussions(query: str, limit: int) -> list[TrendRecord]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return []
    headers = {"Authorization": "Bearer " + token}
    repo_list = [
        repo.strip()
        for repo in os.getenv(
            "GH_DISCUSSION_REPOS",
            "kubernetes/kubernetes,ceph/ceph,openzfs/zfs,hashicorp/terraform",
        ).split(",")
        if repo.strip() and "/" in repo
    ]
    keywords = [k.strip('"').lower() for k in query.replace("OR", " ").split() if len(k) > 3]

    records: list[TrendRecord] = []
    per_repo = max(1, min(limit, 50))
    graphql_query = """
        query($owner: String!, $name: String!, $limit: Int!) {
          repository(owner: $owner, name: $name) {
            discussions(first: $limit, orderBy: {field: UPDATED_AT, direction: DESC}) {
              nodes {
                title
                url
                bodyText
                createdAt
                category { name }
              }
            }
          }
        }
    """
    for repo in repo_list:
        owner, name = repo.split("/", 1)
        resp = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": graphql_query, "variables": {"owner": owner, "name": name, "limit": per_repo}},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()

        if payload.get("errors"):
            messages = "; ".join(
                err.get("message", "unknown GraphQL error") for err in payload.get("errors", [])
            )
            raise RuntimeError(f"GitHub GraphQL query failed for {repo}: {messages}")

        nodes = payload.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
        for node in nodes:
            text = f"{node.get('title', '')} {node.get('bodyText', '')}".lower()
            if keywords and not any(keyword in text for keyword in keywords):
                continue
            records.append(
                TrendRecord(
                    title=node.get("title", "untitled"),
                    summary=(node.get("bodyText", "") or "")[:1200],
                    url=node.get("url", ""),
                    source=f"GitHub Discussions:{repo}",
                    published=node.get("createdAt"),
                    tags=["github-discussion", node.get("category", {}).get("name", "")],
                )
            )
        if len(records) >= limit:
            break
    return records[:limit]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest infrastructure trend signals")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="search query for sources")
    parser.add_argument("--max-arxiv", type=int, default=12)
    parser.add_argument("--max-reddit", type=int, default=20)
    parser.add_argument("--max-github", type=int, default=20)
    parser.add_argument("--rss-per-feed", type=int, default=6)
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "output" / "trends.json"),
        help="output JSON file",
    )
    parser.add_argument(
        "--latest-copy",
        default=str(REPO_ROOT / "data" / "trends" / "latest.json"),
        help="path for optional latest trends copy (set empty to skip)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    arxiv_items = fetch_arxiv(args.query, args.max_arxiv)
    rss_items = fetch_rss(DEFAULT_FEEDS, args.rss_per_feed)
    reddit_items = fetch_reddit(args.query, args.max_reddit)
    github_items = fetch_github_discussions(args.query, args.max_github)

    payload = {
        "generated_at": _iso_now(),
        "query": args.query,
        "source_counts": {
            "arxiv": len(arxiv_items),
            "rss": len(rss_items),
            "reddit": len(reddit_items),
            "github_discussions": len(github_items),
        },
        "records": [asdict(item) for item in (arxiv_items + rss_items + reddit_items + github_items)],
    }

    output_path = Path(args.output)
    write_json(output_path, payload)

    if args.latest_copy:
        write_json(Path(args.latest_copy), payload)

    print(f"Trend ingestion complete: {output_path}")
    print(json.dumps(payload["source_counts"], indent=2))


if __name__ == "__main__":
    main()
