#!/usr/bin/env python3
"""Pulls from the dead-letter subscription and reports what is in it.

The end-to-end run has to prove that a poison message reached `traces-dlq` rather than
being dropped quietly (architecture §3.4). The emulator has no metrics endpoint, so the
proof is a pull: whatever is retained on the dead-letter subscription is what was
dead-lettered.

Messages are pulled without acknowledgement, so the check does not drain what it measures
and can be re-run.
"""

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request

PROJECT = "plumbline-local"


def pull(base: str, subscription: str, max_messages: int) -> list[dict]:
    url = f"{base}/v1/projects/{PROJECT}/subscriptions/{subscription}:pull"
    request = urllib.request.Request(
        url,
        data=json.dumps({"maxMessages": max_messages, "returnImmediately": True}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode()).get("receivedMessages", [])
    except urllib.error.HTTPError as error:
        print(f"pull failed: HTTP {error.code}\n{error.read().decode()[:400]}", file=sys.stderr)
        raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pubsub", default="http://localhost:8085")
    parser.add_argument("--subscription", default="traces-dlq-pull")
    parser.add_argument("--expect", type=int, default=None,
                        help="require exactly this many distinct dead-lettered messages")
    parser.add_argument("--timeout", type=float, default=0,
                        help="seconds to keep pulling before giving up on --expect")
    args = parser.parse_args()

    # Messages are pulled and never acknowledged, so nothing this check observes is
    # consumed. The consequence is that a pulled message is *leased* — invisible to the
    # next pull until its ack deadline expires — so a second pull moments later sees
    # nothing. Distinct message ids are therefore accumulated across pulls rather than
    # counted per pull, and this runs once per end-to-end run instead of being called
    # twice and disagreeing with itself.
    seen: dict[str, dict] = {}
    deadline = time.monotonic() + args.timeout

    while True:
        for received in pull(args.pubsub, args.subscription, max_messages=100):
            message = received.get("message", {})
            seen[message.get("messageId", str(len(seen)))] = message

        if args.expect is None or len(seen) >= args.expect or time.monotonic() >= deadline:
            break

        time.sleep(2)

    print(f"  dead-lettered messages: {len(seen)}")
    for message in seen.values():
        attributes = message.get("attributes", {})
        size = len(base64.b64decode(message.get("data", "")))
        print(f"    api_key_id={attributes.get('api_key_id')} "
              f"dialect_hint={attributes.get('source_dialect')} payload={size}B")

    if args.expect is not None and len(seen) != args.expect:
        print(f"expected {args.expect} dead-lettered message(s), found {len(seen)}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
