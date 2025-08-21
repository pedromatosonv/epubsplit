SplitPub — Split EPUBs by TOC

[![CI](https://github.com/pedromatosonv/splitpub/actions/workflows/ci.yml/badge.svg)](https://github.com/pedromatosonv/splitpub/actions/workflows/ci.yml)

Purpose
- Split an EPUB into per‑chapter EPUBs based on top‑level TOC entries.
- Stream by default: read EPUB from stdin, write tar of EPUBs to stdout, or write files to a directory.

Features
- Top‑level TOC only (EPUB3 `nav` or EPUB2 `ncx`).
- No default exclusions; optional ignore rules via `.splitpub-ignore` or `--ignore-file`.
- Streaming I/O (no buffering entire tar in memory).
- Simple, dependency‑free Python (stdlib only) and a minimal Docker image.

Quick Start (Docker)
- Build: `docker build -t splitpub:latest .`
- Check (JSON): `docker run --rm -i splitpub:latest --mode check --format json < book.epub`
- Split to tar: `docker run --rm -i splitpub:latest --mode split < book.epub > out.tar`
- Validate tar from stdin: `docker run --rm -i splitpub:latest --mode validate --input - < out.tar`
- Split to directory: `docker run --rm -i -v "$PWD/out":/out splitpub:latest --mode split --out /out < book.epub`

Local Usage
- Check TOC: `python3 cli.py --mode check --input book.epub --format text`
- Apply ignores: `python3 cli.py --mode check --input book.epub --ignore-file ignore.txt`
- Split to tar: `python3 cli.py --mode split --input book.epub > out.tar`
- Split to directory: `python3 cli.py --mode split --input book.epub --out outdir`
- Validate tar: `python3 cli.py --mode validate --input out.tar`

CLI Options
- `--mode {check,split,validate}`: Operation mode. Default: `check`.
- `--input PATH|-`: EPUB path or `-` for stdin (default).
- `--out DIR|-`: Output directory for split mode; `-` (default) streams a tar to stdout.
- `--format {text,json}`: Output format for check mode. Default: `text`.
- `--ignore-file PATH`: Path to ignore patterns file; if omitted, uses `.splitpub-ignore` when present.
- `--name-template TEMPLATE`: Output filename template; default: `{index:02d} - {title}.epub`.

Ignore Rules
- Case‑insensitive regexes, one per line. Blank lines and `#` comments are ignored.
- Any TOC entry whose title matches a pattern is excluded.
- Example:
  - `^cover$`
  - `^title page$`
  - `^table of contents$`

Makefile Shortcuts
- `make build`
- `make check IN=book.epub`
- `make split-tar IN=book.epub`
- `make split-dir IN=book.epub OUTDIR=out IGNORE=.splitpub-ignore`
- `make validate`

Notes
- Generated EPUBs contain the selected chapter XHTML and shared assets (CSS, images, fonts, JS); other XHTML files are not bundled.
- Basic metadata preserved; output title becomes `Original Title — Chapter Title`.
- No nav/NCX is added to outputs; most readers handle a single‑file spine.

Limitations
- Only top‑level TOC splitting is supported.
- Linked external XHTML (e.g., footnotes pages) is not included.

Contributing
- Run compile check: `python3 -m py_compile cli.py core.py __init__.py`.
- CI runs smoke tests across Python 3.9–3.12 and Docker flows.

Releases
- Tag a version: `git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`.
- A GitHub Release is created automatically from tags via workflow.
- Release notes are auto‑generated; edit on GitHub if needed.
 - Or run from Actions UI: Manual Release workflow (enter tag, optional notes).
 - See CHANGELOG.md for curated notes; release automation uses that when available.

License
- MIT — see the LICENSE file for full text.
