#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

# Support both package and flat layouts
try:
    from . import __version__  # type: ignore
except Exception:  # pragma: no cover - flat layout
    try:
        from __init__ import __version__  # type: ignore
    except Exception:
        __version__ = "0.1.0"  # fallback

try:
    from .core import check, split, validate_tar  # type: ignore
except Exception:  # pragma: no cover - flat layout
    from core import check, split, validate_tar  # type: ignore


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="splitpub",
        description="Split an EPUB into per-TOC-entry EPUBs or check what would be split.",
    )
    p.add_argument("--mode", choices=["check", "split", "validate"], default="check", help="Operation mode")
    p.add_argument("--input", default="-", help="Path to EPUB or '-' for stdin (default)")
    p.add_argument("--out", default="-", help="Output directory or '-' to stream tar to stdout (split mode)")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format for check mode")
    p.add_argument(
        "--ignore-file",
        default=None,
        help="Path to ignore patterns file (default: .splitpub-ignore if present)",
    )
    p.add_argument(
        "--name-template",
        default="{index:02d} - {title}.epub",
        help="Filename template using {index} and {title}",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "check":
        return check(args.input, args.ignore_file, args.format)
    if args.mode == "split":
        return split(args.input, args.ignore_file, args.out, args.name_template)
    # validate: treat --input as tar path or '-' (stdin)
    return validate_tar(args.input)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
