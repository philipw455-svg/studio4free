"""Clip studio command line. Run: python -m studio <step> --job NAME"""
import argparse

from . import buffer, fetch, plan, render, review, shots, tools, transcribe


def nums(text):
    return [int(x) for x in text.split(",") if x.strip()] if text else None


def main():
    p = argparse.ArgumentParser(prog="studio", description="Turn a long video into short clips and schedule them.")
    sub = p.add_subparsers(dest="step", required=True)

    a = sub.add_parser("fetch", help="download or copy the source video")
    a.add_argument("source", help="a YouTube link, a direct file link, or a file path")
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

    sub.add_parser("channels", help="list the Buffer channels")

    a = sub.add_parser("post", help="create the Buffer posts from posting.json")
    a.add_argument("--job", required=True)
    a.add_argument("--services", default="youtube,instagram")
    a.add_argument("--draft", action="store_true", help="save as drafts, not scheduled posts")
    a.add_argument("--only", default="")

    x = p.parse_args()
    if x.step == "fetch":
        fetch.fetch(x.job, x.source)
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
    elif x.step == "channels":
        for c in buffer.channels():
            print(f"{c['service']:<10} {c.get('displayName') or c['name']}  ({c['id']})")
    elif x.step == "post":
        buffer.post(x.job, x.services, x.draft, nums(x.only))


if __name__ == "__main__":
    main()
