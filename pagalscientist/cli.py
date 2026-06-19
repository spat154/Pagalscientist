"""Command-line control for the Made in India desk.

Examples:
    python -m pagalscientist.cli run            # sense -> cluster -> verify -> draft
    python -m pagalscientist.cli queue          # list stories awaiting review
    python -m pagalscientist.cli show <id>      # print a draft
    python -m pagalscientist.cli approve <id>
    python -m pagalscientist.cli publish <id>   # the "publish everywhere" button
    python -m pagalscientist.cli patterns       # what's trending across stories
"""
from __future__ import annotations

import argparse
import logging
import sys

from .cluster import pattern_summary
from .config import load_settings, load_sources
from .models import StoryStatus
from .pipeline import Pipeline
from .publish import available_targets
from .publish.console import ConsolePublisher
from .review import approve, edit_story, publish_story, reject
from .store import Store


def _store(args) -> Store:
    settings = load_settings()
    return Store(args.db or settings.db_path)


def cmd_run(args):
    settings = load_settings()
    store = Store(args.db or settings.db_path)
    pipe = Pipeline(store, settings=settings, sources=load_sources())
    summary = pipe.run(limit_per_source=args.limit, max_stories=args.max_stories)
    print("Pipeline run complete:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    if summary["drafts_created"]:
        print("\nReview them with: python -m pagalscientist.cli queue")
    store.close()


def cmd_queue(args):
    store = _store(args)
    stories = store.stories_by_status(StoryStatus.NEEDS_REVIEW)
    if not stories:
        print("No stories awaiting review.")
    for s in stories:
        cred = s.credibility or {}
        print(f"- {s.id}  [{cred.get('score', '?')}/100 · "
              f"{cred.get('recommendation', '?')}]  {s.headline}")
        if cred.get("flags"):
            print(f"    flags: {', '.join(cred['flags'])}")
    store.close()


def cmd_show(args):
    store = _store(args)
    story = store.get_story(args.id)
    if not story:
        print(f"No story {args.id}", file=sys.stderr)
        sys.exit(1)
    print(ConsolePublisher().render(story))
    if story.editor_notes:
        print(f"\n_Editor notes:_ {story.editor_notes}")
    print(f"\n_Status:_ {story.status}")
    store.close()


def cmd_patterns(args):
    store = _store(args)
    patterns = pattern_summary(store.all_clusters())
    if not patterns:
        print("No cross-story patterns yet.")
    for p in patterns:
        print(f"- {p['term']}: appears across {p['story_count']} stories")
    store.close()


def cmd_edit(args):
    store = _store(args)
    edit_story(store, args.id, headline=args.headline, dek=args.dek,
               editor_notes=args.notes)
    print(f"Updated {args.id}")
    store.close()


def cmd_approve(args):
    store = _store(args)
    approve(store, args.id)
    print(f"Approved {args.id}. Publish with: "
          f"python -m pagalscientist.cli publish {args.id}")
    store.close()


def cmd_reject(args):
    store = _store(args)
    reject(store, args.id)
    print(f"Rejected {args.id}")
    store.close()


def cmd_publish(args):
    settings = load_settings()
    store = Store(args.db or settings.db_path)
    targets = args.targets.split(",") if args.targets else None
    results = publish_story(store, args.id, settings, targets=targets,
                            force=args.force)
    print("Publish results:")
    for r in results:
        mark = "OK" if r.ok else "FAIL"
        print(f"  [{mark}] {r.target}: {r.ref or r.detail}")
    store.close()


def build_parser() -> argparse.ArgumentParser:
    # Shared options accepted both before and after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", help="SQLite path (overrides config/env)")
    common.add_argument("-v", "--verbose", action="store_true")

    p = argparse.ArgumentParser(prog="pagalscientist", description=__doc__,
                                parents=[common])
    sub = p.add_subparsers(dest="command", required=True, parser_class=lambda **kw:
                           argparse.ArgumentParser(parents=[common], **kw))

    r = sub.add_parser("run", help="ingest -> cluster -> verify -> draft")
    r.add_argument("--limit", type=int, default=25, help="items per source")
    r.add_argument("--max-stories", type=int, default=None)
    r.set_defaults(func=cmd_run)

    sub.add_parser("queue", help="list stories awaiting review").set_defaults(func=cmd_queue)
    sub.add_parser("patterns", help="trending cross-story themes").set_defaults(func=cmd_patterns)

    s = sub.add_parser("show", help="print a story"); s.add_argument("id"); s.set_defaults(func=cmd_show)

    e = sub.add_parser("edit", help="edit a story")
    e.add_argument("id")
    e.add_argument("--headline"); e.add_argument("--dek"); e.add_argument("--notes")
    e.set_defaults(func=cmd_edit)

    a = sub.add_parser("approve"); a.add_argument("id"); a.set_defaults(func=cmd_approve)
    j = sub.add_parser("reject"); j.add_argument("id"); j.set_defaults(func=cmd_reject)

    pub = sub.add_parser("publish", help=f"publish everywhere ({', '.join(available_targets())})")
    pub.add_argument("id")
    pub.add_argument("--targets", help="comma-separated targets (default from config)")
    pub.add_argument("--force", action="store_true", help="skip the approved check")
    pub.set_defaults(func=cmd_publish)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    args.func(args)


if __name__ == "__main__":
    main()
