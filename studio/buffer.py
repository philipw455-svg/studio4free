"""Step 6: put clips into Buffer as scheduled posts or drafts.

Buffer has no upload endpoint. Each video needs a public, direct, stable URL.
The key comes from BUFFER_API_KEY. In a Claude cloud session the network adds
the saved key by itself, so the variable can stay unset there.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from .common import job_dir, read_json, write_json

API = "https://api.buffer.com"


def gql(query: str, variables: dict | None = None) -> dict:
    key = os.environ.get("BUFFER_API_KEY", "set-by-network")
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "clip-studio/1.0"})
    try:
        with urllib.request.urlopen(req) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.exit("Buffer refused the key. Save a Buffer API key for api.buffer.com, or set BUFFER_API_KEY.")
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


CREATE = """mutation($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess { post { id text } }
    ... on MutationError { message }
  }
}"""


def create_post(channel: dict, text: str, video_url: str, due_at: str, title: str, draft: bool) -> str:
    inp = {"channelId": channel["id"], "text": text, "schedulingType": "automatic", "mode": "customScheduled",
           "dueAt": datetime.fromisoformat(due_at).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
           "assets": [{"video": {"url": video_url}}], "aiAssisted": True}
    if draft:
        inp["saveToDraft"] = True
    if channel["service"] == "youtube":
        inp["metadata"] = {"youtube": {"title": title[:100], "categoryId": "22"}}
    res = gql(CREATE, {"input": inp})["createPost"]
    if res.get("message"):
        raise RuntimeError(res["message"])
    return res["post"]["id"]


def post(job: str, services: str, draft: bool, only: list | None = None) -> None:
    """Read posting.json and create one Buffer post per clip and channel.

    Every item needs: publishAt, title, description and url (the public video link).
    """
    d = job_dir(job)
    plan = read_json(d / "posting.json")
    want = [s.strip().lower() for s in services.split(",")]
    chans = [c for c in channels() if c["service"].lower() in want]
    if not chans:
        sys.exit(f"Buffer has no channel for: {services}")
    for it in plan["items"]:
        if only and it["clip"] not in only:
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
                                                it["publishAt"], it["title"], draft)
                it["status"] = "draft in Buffer" if draft else "scheduled in Buffer"
                print(f"Clip {it['clip']}: {svc} {it['status']} for {it['publishAt']}")
            except RuntimeError as e:
                it["status"] = f"Buffer refused {svc}: {e}"
                print(f"Clip {it['clip']}: {it['status']}")
        write_json(d / "posting.json", plan)
