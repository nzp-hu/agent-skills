#!/usr/bin/env python
"""eol.py — offline end-of-life lookup for endoflife.date products.

Usage:
  eol.py list  [--grep PATTERN] [--limit N] [--offset N]
  eol.py get   <slug> [--full]
  eol.py check
  eol.py --help

Subcommands:
  list    List products as JSON lines: {"slug", "title", "aliases"}.
          --grep filters slug, title, and aliases (case-insensitive).
          --limit (default 100) and --offset paginate the full listing.
  get     Print the YAML frontmatter of products/<slug>.md (raw, unparsed).
          --full appends the markdown body.
  check   Validate every product file against the parsing conventions.

Data source: the products cache at SKILL_DIR/assets/products, overridable
with --products-dir. If the cache is empty, the script prints fetch
instructions (exit 4); it never touches the network itself.

Exit codes:
  0  success
  2  invalid arguments (argparse)
  3  slug not found, or no list matches
  4  cache empty — fetch instructions printed on stderr
  5  check found frontmatter drift (parser conventions no longer hold)

Data goes to stdout as JSON lines; diagnostics go to stderr.
"""
import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
TARBALL_URL = "https://codeload.github.com/endoflife-date/endoflife.date/tar.gz/refs/heads/master"


def fail(message: str, code: int) -> None:
    """Print a diagnostic to stderr and exit with a documented code."""
    print(message, file=sys.stderr)
    sys.exit(code)


def resolve_products(args) -> Path:
    products = Path(args.products_dir) if args.products_dir else SKILL_DIR / "assets" / "products"
    if not products.is_dir() or not any(products.glob("*.md")):
        fail(
            "Error: product cache is empty. Fetch the latest products/*.md "
            f"from the tarball\n{TARBALL_URL}\ninto "
            f"{SKILL_DIR / 'assets' / 'products'} (the directory containing "
            "SKILL.md), then re-run this command.",
            4,
        )  # exit 4
    return products


def frontmatter_block(text: str) -> list[str] | None:
    """Return the lines between the first two --- markers, or None."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            return lines[1:i]
    return None


def list_entry(path: Path) -> dict:
    """Extract slug, title, and aliases from a product file.

    Only two frontmatter shapes are parsed: a top-level scalar (title:)
    and a flat block list (alternate_urls: with '  - ' items). Everything
    else is ignored. Validated against all product files by `check`.
    """
    fm = frontmatter_block(path.read_text(encoding="utf-8"))
    entry = {"slug": path.stem, "title": None, "aliases": []}
    if fm is None:
        entry["error"] = "no frontmatter"
        return entry
    in_aliases = False
    for line in fm:
        s = line.strip()
        if s.startswith("title:"):
            entry["title"] = s[6:].strip().strip('"').strip("'")
            in_aliases = False
        elif s.startswith("alternate_urls:"):
            in_aliases = True
        elif in_aliases:
            if s.startswith("- "):
                entry["aliases"].append(s[2:].strip().lstrip("/"))
            elif s:  # any other key ends the list
                in_aliases = False
    return entry


def cmd_list(products_dir: Path, args) -> None:
    entries = [list_entry(p) for p in sorted(products_dir.glob("*.md"))]
    if args.grep:
        needle = args.grep.lower()
        entries = [
            e for e in entries
            if needle in e["slug"]
            or needle in (e["title"] or "").lower()
            or any(needle in a for a in e["aliases"])
        ]
    if not entries:
        fail(
            f"Error: no products match --grep {args.grep!r}. "
            "Try a shorter term, or the full list: list --limit 100",
            3,
        )  # exit 3
    page = entries[args.offset: args.offset + args.limit]
    for e in page:
        print(json.dumps(e))
    remaining = len(entries) - (args.offset + len(page))
    if remaining > 0:
        print(
            f"{remaining} more match(es); next page: --offset {args.offset + args.limit}",
            file=sys.stderr,
        )


def cmd_get(products_dir: Path, slug: str, full: bool) -> None:
    path = products_dir / f"{slug}.md"
    if not path.is_file():
        candidates = [p.stem for p in sorted(products_dir.glob("*.md"))
                      if slug[:4].lower() in p.stem.lower()][:5]
        hint = f" Close candidates: {candidates}." if candidates else ""
        fail(
            f"Error: slug {slug!r} not found.{hint} "
            "Run list --grep for the canonical set.",
            3,
        )  # exit 3
    parts = path.read_text(encoding="utf-8").split("---", 2)
    print("---" + parts[1] + "---")
    if full and len(parts) > 2:
        print(parts[2])


def cmd_check(products_dir: Path) -> None:
    problems = []
    files = sorted(products_dir.glob("*.md"))
    for p in files:
        entry = list_entry(p)
        if entry.get("error"):
            problems.append(f"{p.name}: {entry['error']}")
        elif not entry["title"]:
            problems.append(f"{p.name}: no title extracted")
        for a in entry["aliases"]:
            if not a or a.startswith("-"):
                problems.append(f"{p.name}: malformed alias {a!r}")
    print(f"checked {len(files)} products, {len(problems)} problem(s)")
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(
            "Parser conventions drifted: list is unreliable. Fall back to "
            "raw reads (grep title:/alternate_urls: in products/*.md) for "
            "matching; get answers remain valid.",
            file=sys.stderr,
        )
        sys.exit(5)  # frontmatter conventions drifted


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="eol.py",
        description="Offline end-of-life lookup for endoflife.date products.",
        epilog=__doc__,
    )
    parser.add_argument("--products-dir", help="override the products cache location")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list products (JSON lines)")
    p_list.add_argument("--grep", help="filter slug, title, aliases (case-insensitive)")
    p_list.add_argument("--limit", type=int, default=100)
    p_list.add_argument("--offset", type=int, default=0)

    p_get = sub.add_parser("get", help="print a product's frontmatter")
    p_get.add_argument("slug")
    p_get.add_argument("--full", action="store_true", help="include the markdown body")

    sub.add_parser("check", help="validate all product files against parser conventions")

    args = parser.parse_args()
    products_dir = resolve_products(args)

    if args.command == "list":
        cmd_list(products_dir, args)
    elif args.command == "get":
        cmd_get(products_dir, args.slug, args.full)
    elif args.command == "check":
        cmd_check(products_dir)


if __name__ == "__main__":
    main()
