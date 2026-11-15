"""Clip studio command line. Run: python -m studio <step> --job NAME"""
import argparse

from . import buffer, doctor, fetch, join, plan, render, review, shots, tools, transcribe


def nums(text):
    return [int(x) for x in text.split(",") if x.strip()] if text else None


def main():
    p = argparse.ArgumentParser(prog="studio", description="Turn a long video into short clips and schedule them.")
    sub = p.add_subparsers(dest="step", required=True)

    a = sub.add_parser("fetch", help="download or copy the source video")
    a.add_argument("source", help="a YouTube link, a direct file link, or a file path")
    a.add_argument("--job", required=True)
    a.add_argument("--out", default="source.mp4", help="the file name in the job folder, such as sources/01.mp4 for a montage clip")

    a = sub.add_parser("join", help="join the parts listed in join.json into one video, for an edit job or a montage job")
    a.add_argument("--job", required=True)

    a = sub.add_parser("transcribe", help="write the transcript with word times")
    a.add_argument("--job", required=True)
    a.add_argument("--model", default="small", help="tiny, base, small or medium")
    a.add_argument("--language", default=None)

    a = sub.add_parser("cut", help="render the clips listed in clips.json")
    a.add_argument("--job", required=True)
    a.add_argument("--only", default="", help="clip numbers, for example 2,5")

    a = sub.add_parser("shots", help="list each clip's camera cuts and save one frame per shot")
    a.add_argument("--job", required=True)
    a.add_argument("--only", default="", help="clip numbers, for example 2,5")

    a = sub.add_parser("words", help="print the words between two source times, each with its start time")
    a.add_argument("--job", required=True)
    a.add_argument("--start", type=float, required=True)
    a.add_argument("--end", type=float, required=True)

    a = sub.add_parser("fix", help="correct misheard words in the transcript")
    a.add_argument("--job", required=True)
    a.add_argument("edits", nargs="+", help='"seconds|old|new" for the word that starts at that source time; an empty new deletes it')

    a = sub.add_parser("sheet", help="save a sheet of frames of each rendered clip, to check it by eye")
    a.add_argument("--job", required=True)
    a.add_argument("--only", default="", help="clip numbers, for example 2,5")

    a = sub.add_parser("schedule", help="give each rendered clip a publish time")
    a.add_argument("--job", required=True)
    a.add_argument("--start", required=True, help="first day, as YYYY-MM-DD")
    a.add_argument("--times", default="12:15,17:00")
    a.add_argument("--tz", default="America/Chicago")
    a.add_argument("--order", default="", help="clip numbers in posting order")
    a.add_argument("--flash-days", default="Tuesday,Friday", help="days whose clips carry the Noxi flash")

    a = sub.add_parser("texts", help="collect each clip's words and titles for the rules check")
    a.add_argument("--job", required=True)

    a = sub.add_parser("doctor", help="check what is installed, and say which features cannot run")
    a.add_argument("--json", action="store_true", help='print only {"ok", "missing", "cannot"} as JSON')

    login = argparse.ArgumentParser(add_help=False)
    login.add_argument("--buffer", default="", type=str.strip, metavar="LABEL",
                       help="the account's Buffer login. The key then comes from BUFFER_API_KEY_<LABEL>")

    sub.add_parser("channels", parents=[login], help="list the Buffer channels: id, service and name")
    sub.add_parser("queue", parents=[login], help="list every Buffer post with its status and live link")

    a = sub.add_parser("post", parents=[login], help="create the Buffer posts from posting.json")
    a.add_argument("--job", required=True)
    a.add_argument("--services", default="youtube,instagram")
    a.add_argument("--channels", default="", metavar="ID,ID",
                   help="post only to the Buffer channels with these ids, one channel per service")
    a.add_argument("--draft", action="store_true", help="save as drafts, not scheduled posts")
    a.add_argument("--only", default="")

    x = p.parse_args()
    if getattr(x, "buffer", ""):
        buffer.use_login(x.buffer)
    if x.step == "fetch":
        fetch.fetch(x.job, x.source, x.out)
    elif x.step == "join":
        join.join(x.job)
    elif x.step == "transcribe":
        transcribe.transcribe(x.job, x.model, x.language)
    elif x.step == "cut":
        render.render(x.job, nums(x.only))
    elif x.step == "shots":
        shots.shots(x.job, nums(x.only))
    elif x.step == "words":
        tools.words(x.job, x.start, x.end)
    elif x.step == "fix":
        tools.fix(x.job, x.edits)
    elif x.step == "sheet":
        tools.sheet(x.job, nums(x.only))
    elif x.step == "schedule":
        plan.schedule(x.job, x.start, x.times, x.tz, x.order, x.flash_days)
    elif x.step == "texts":
        review.texts(x.job)
    elif x.step == "doctor":
        doctor.doctor(x.json)
    elif x.step == "queue":
        for p in buffer.queue():
            first = (p["text"] or "").split("\n")[0][:60]
            err = f"  ERROR {p['error']['message']}" if p.get("error") else ""
            print(f"{p['id']}  {p['channelService']:<9} {p['status']:<9} {p['sentAt'] or p['dueAt'] or '-':<24} {p.get('externalLink') or '-'}  {first}{err}")
    elif x.step == "channels":
        for c in buffer.channels():
            # Both names when Buffer has two, so a session can match the channel name saved on the page.
            names = " / ".join(dict.fromkeys(n for n in (c.get("displayName"), c.get("name")) if n))
            print(f"{c['id']}  {c['service']:<10} {names}")
    elif x.step == "post":
        buffer.post(x.job, x.services, x.draft, nums(x.only), x.channels)


if __name__ == "__main__":
    main()
