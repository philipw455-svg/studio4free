"""Step 6: put clips into Buffer as scheduled posts or drafts.

Buffer has no upload endpoint. Each video needs a public, direct, stable URL.
The key comes from BUFFER_API_KEY. In a Claude cloud session the network adds
the saved key by itself, so the variable can stay unset there.
An account with its own Buffer login names it with --buffer=<label>. Then the key
comes from BUFFER_API_KEY_<LABEL> and from nowhere else.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from .common import job_dir, read_json, write_json

API = "https://api.buffer.com"
KEY_VAR = "BUFFER_API_KEY"  # the variable that holds the key. use_login() points it at another Buffer login.


def key_var(label: str) -> str:
    """The environment variable that holds the key of the Buffer login with this label."""
    return "BUFFER_API_KEY_" + re.sub(r"[^A-Z0-9]", "_", label.upper())


def use_login(label: str) -> None:
    """Send every later call with the key of this Buffer login. Stops when that key is not set."""
    global KEY_VAR
    var = key_var(label)
    if not os.environ.get(var):
        # Never fall back to BUFFER_API_KEY here: it would post to the wrong account.
        sys.exit(f"{var} is not set. Set it to the Buffer API key of the \"{label}\" login, then run this again.")
    KEY_VAR = var


def pick_channels(chans: list, services: str, ids: str = "") -> list:
    """The channels to post to: those of the named services, and with ids, only the channels with those ids."""
    want = [s.strip().lower() for s in services.split(",")]
    left = [c for c in chans if c["service"].lower() in want]
    if not left:
        raise ValueError(f"Buffer has no channel for: {services}")
    only = [i.strip() for i in ids.split(",") if i.strip()]
    if ids.strip() and not only:
        raise ValueError("--channels has no channel id in it.")
    if only:
        # Every id must be used. A dropped id would leave one service without a post, and nothing would say so.
        missing = [i for i in only if i not in {c["id"] for c in left}]
        if missing:
            raise ValueError(f"--channels has ids that are not a channel of this Buffer login for {services}: "
                             f"{', '.join(missing)}. Run: python -m studio channels")
        left = [c for c in left if c["id"] in only]
        svcs = [c["service"].lower() for c in left]
        if len(set(svcs)) < len(svcs):
            # posting.json saves one Buffer post id per service, so a second channel would be skipped without a word.
            raise ValueError("--channels must name one channel per service. Two of these ids are the same service.")
    return left


def gql(query: str, variables: dict | None = None) -> dict:
    key = os.environ.get(KEY_VAR, "set-by-network")
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "clip-studio/1.0"})
    try:
        with urllib.request.urlopen(req) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.exit(f"Buffer refused the key. Save a Buffer API key for api.buffer.com, or set {KEY_VAR}.")
        sys.exit(f"Buffer answered {e.code}: {e.read().decode()[:300]}")
    if out.get("errors"):
        sys.exit("Buffer reported: " + "; ".join(x.get("message", "") for x in out["errors"]))
    return out["data"]


def channels() -> list:
    orgs = gql("query { account { organizations { id name } } }")["account"]["organizations"]
    found = []
    for o in orgs:
        q = "query($id: OrganizationId!) { channels(input: {organizationId: $id}) { id name displayName service isQueuePaused } }"
        for c in gql(q, {"id": o["id"]})["channels"]:
            found.append({**c, "organization": o["name"]})
    return found


def queue() -> list:
    """Every post in Buffer, oldest first: what is posted, what is scheduled, and where each one is live."""
    org = gql("query { account { organizations { id } } }")["account"]["organizations"][0]["id"]
    q = """query($org: OrganizationId!, $after: String) { posts(first: 100, after: $after, input: {organizationId: $org, sort: [{field: dueAt, direction: asc}]}) {
      pageInfo { hasNextPage endCursor } edges { node { id status dueAt sentAt channelService externalLink text error { message } } } } }"""
    posts, after = [], None
    while True:
        r = gql(q, {"org": org, "after": after})["posts"]
        posts += [e["node"] for e in r["edges"]]
        if not r["pageInfo"]["hasNextPage"]:
            return posts
        after = r["pageInfo"]["endCursor"]


CREATE = """mutation($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id text } }
    ... on MutationError { message }
  }
}"""


def create_post(channel: dict, text: str, video_url: str, due_at: str, title: str, draft: bool, comment: str = "") -> str:
    inp = {"channelId": channel["id"], "text": text, "schedulingType": "automatic", "mode": "customScheduled",
           "dueAt": datetime.fromisoformat(due_at).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
           "assets": [{"video": {"url": video_url}}], "aiAssisted": True}
    if draft:
        inp["saveToDraft"] = True
    if channel["service"] == "youtube":
        inp["metadata"] = {"youtube": {"title": title[:100], "categoryId": "22"}}
    elif channel["service"] == "instagram":
        inp["metadata"] = {"instagram": {"type": "reel", "shouldShareToFeed": True}}
        if comment:
            # Buffer posts this as the first comment under the reel. Buffer has no such field for YouTube.
            inp["metadata"]["instagram"]["firstComment"] = comment
    res = gql(CREATE, {"input": inp})["createPost"]
    if res.get("message"):
        raise RuntimeError(res["message"])
    return res["post"]["id"]


def post(job: str, services: str, draft: bool, only: list | None = None, channel_ids: str = "") -> None:
    """Read posting.json and create one Buffer post per clip and channel.

    Every item needs: publishAt, title, description and url (the public video link).
    An item with "hold": true is skipped. Set it for clips the rules check marked as a risk.
    With channel_ids, only the channels with those Buffer ids get a post.
    """
    d = job_dir(job)
    plan = read_json(d / "posting.json")
    try:
        chans = pick_channels(channels(), services, channel_ids)
    except ValueError as e:
        sys.exit(str(e))
    for it in plan["items"]:
        if only and it["clip"] not in only:
            continue
        if it.get("hold"):
            print(f"Clip {it['clip']}: held back by the rules check.")
            continue
        if not it.get("url"):
            print(f"Clip {it['clip']}: skipped, it has no public video link yet.")
            continue
        it.setdefault("buffer", {})
        for c in chans:
            svc = c["service"].lower()
            if it["buffer"].get(svc):
                continue
            try:
                it["buffer"][svc] = create_post(c, it.get("description") or it["title"], it["url"],
                                                it["publishAt"], it["title"], draft, it.get("comment", ""))
                it["status"] = "draft in Buffer" if draft else "scheduled in Buffer"
                print(f"Clip {it['clip']}: {svc} {it['status']} for {it['publishAt']}")
            except RuntimeError as e:
                it["status"] = f"Buffer refused {svc}: {e}"
                print(f"Clip {it['clip']}: {it['status']}")
        write_json(d / "posting.json", plan)
