from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="goldfish", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("serve", help="run the goldfish MCP server (stdio)")
    sub.add_parser("status", help="print health across all three memory tiers")

    from memory_notes.store import MEMORY_TYPES

    remember_p = sub.add_parser("remember", help="write a curated memory note")
    remember_p.add_argument("name")
    remember_p.add_argument("description")
    remember_p.add_argument("--type", choices=MEMORY_TYPES, required=True)
    remember_p.add_argument("--content", required=True, help="note body (markdown)")

    recall_p = sub.add_parser("recall", help="read or search curated memory notes")
    recall_p.add_argument("name", nargs="?")
    recall_p.add_argument("--query")
    recall_p.add_argument("--type", choices=MEMORY_TYPES)

    reflect_p = sub.add_parser("reflect", help="gather raw cited evidence of recurring language (no synthesis)")
    reflect_p.add_argument("--focus", help="one specific angle; omit for the default battery")
    reflect_p.add_argument("--limit-per-query", type=int, default=5)

    sub.add_parser("persona", help="print the cumulative persona file (all insight notes, aggregated)")

    args = parser.parse_args(argv)

    if args.command == "serve":
        from .server import main as serve_main
        serve_main()
        return

    if args.command == "status":
        from .server import goldfish_status
        print(json.dumps(goldfish_status(), indent=2, default=str))
        return

    if args.command == "remember":
        from .server import goldfish_remember
        print(json.dumps(goldfish_remember(args.name, args.description, args.type, args.content), indent=2))
        return

    if args.command == "recall":
        from .server import goldfish_recall
        print(json.dumps(goldfish_recall(name=args.name, query=args.query, type=args.type), indent=2))
        return

    if args.command == "reflect":
        from .server import goldfish_reflect
        print(json.dumps(goldfish_reflect(focus=args.focus, limit_per_query=args.limit_per_query), indent=2))
        return

    if args.command == "persona":
        from .server import goldfish_persona
        result = goldfish_persona()
        print(result["content"] if result.get("available") else result.get("reason", "unavailable"))
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
