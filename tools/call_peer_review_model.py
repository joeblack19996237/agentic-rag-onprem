#!/usr/bin/env python3
"""Call an OpenAI-compatible chat completions endpoint to get a structured,
independent code review of a diff from a model outside the Claude family.

Exit codes are the contract this skill relies on:
  0 - success, --out contains {"issues": [...], "summary": "..."}
  1 - the call was attempted and failed (network error, timeout, non-200,
      or a response that wasn't valid JSON despite requesting JSON mode).
      The skill treats this as "peer review unavailable" - a hard BLOCK,
      not a soft warning, and never falls back to guessing at partial output.
  2 - PEER_REVIEW_API_KEY is not set. Not attempted at all.

Uses only the standard library so it runs anywhere Python 3 does, with no
extra dependency to install first.

Backend defaults to DeepSeek's public API, but every part of it is
configurable via --model/--endpoint or the PEER_REVIEW_MODEL /
PEER_REVIEW_API_BASE env vars, so a different non-Claude vendor can be
swapped in without touching this file.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 120


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_payload(rubric, diff, context, model):
    user_parts = []
    if context:
        user_parts.append("## Spec / requirement context\n\n" + context)
    user_parts.append("## Diff to review\n\n" + diff)
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": rubric},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diff-file", required=True)
    parser.add_argument("--rubric-file", required=True)
    parser.add_argument("--context-file", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default=os.environ.get("PEER_REVIEW_MODEL", DEFAULT_MODEL))
    parser.add_argument("--endpoint", default=os.environ.get("PEER_REVIEW_API_BASE", DEFAULT_ENDPOINT))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the request payload and write it to --out without calling the network "
        "or requiring an API key. Use this to validate payload construction offline.",
    )
    args = parser.parse_args()

    rubric = read_file(args.rubric_file)
    diff = read_file(args.diff_file)
    context = read_file(args.context_file) if args.context_file else None

    payload = build_payload(rubric, diff, context, args.model)

    if args.dry_run:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"DRY RUN: wrote request payload to {args.out} (no network call made)")
        return 0

    api_key = os.environ.get("PEER_REVIEW_API_KEY")
    if not api_key:
        print(
            "PEER_REVIEW_API_KEY is not set - peer review cannot call the configured model. "
            "This is not attempted as a partial/best-effort call.",
            file=sys.stderr,
        )
        return 2

    request = urllib.request.Request(
        args.endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            raw_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Peer-review API returned HTTP {e.code}: {body}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"Peer-review API call failed: {e}", file=sys.stderr)
        return 1

    try:
        transport = json.loads(raw_body)
        content = transport["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        print(f"Peer-review API response had an unexpected shape: {e}\nRaw body: {raw_body}", file=sys.stderr)
        return 1

    try:
        review = json.loads(content)
    except json.JSONDecodeError as e:
        print(
            f"Peer-review model did not return valid JSON content despite json_object mode "
            f"({e}) - treating as a failed call rather than guessing at a parse.\n"
            f"Raw content: {content}",
            file=sys.stderr,
        )
        return 1

    if "issues" not in review or "summary" not in review or not isinstance(review["issues"], list):
        print(f"Peer-review model's JSON is missing required keys (issues/summary): {review}", file=sys.stderr)
        return 1

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(review, f, indent=2)
    print(f"OK: wrote {len(review['issues'])} issue(s) to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
