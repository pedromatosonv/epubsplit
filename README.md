EPUBSplit — Split EPUBs by TOC

Overview
- Splits an EPUB into multiple EPUBs, one per top‑level TOC entry.
- Two modes: check (dry‑run listing) and split (produce per‑chapter EPUBs).
- Designed for streaming I/O in Docker: read EPUB from stdin, write a tar of EPUBs to stdout, or write directly to a mounted directory.

Quick Start
- Build: `docker build -t ourtool:latest .`
- Check (JSON): `docker run --rm -i ourtool:latest --mode check --format json < book.epub`
- Split to tar stream: `docker run --rm -i ourtool:latest --mode split < book.epub > out.tar`
- Validate tar: `docker run --rm -i ourtool:latest --mode validate --input - < out.tar`
- Extract results: `mkdir outdir && tar -xf out.tar -C outdir`
- Split directly into directory: `docker run --rm -i -v "$PWD/outdir":/out ourtool:latest --mode split --out /out < book.epub`

CLI
- `--mode {check,split,validate}`: Operation mode. Default: `check`.
- `--input PATH|-`: EPUB path or `-` for stdin (default).
- `--out DIR|-`: Output directory path for split mode; `-` (default) streams a tar to stdout.
- `--format {text,json}`: Output format for check mode. Default: `text`.
- `--ignore-file PATH`: Optional path to an ignore patterns file (see below). If omitted, the tool looks for `.epubsplit-ignore` in the working directory.
- `--name-template TEMPLATE`: Filename template; default: `{index:02d} - {title}.epub`.

Ignore Rules
- Provide a file of case‑insensitive regular expressions, one per line. Blank lines and lines starting with `#` are ignored.
- Any TOC entry whose title matches any pattern is excluded from splitting.
- Example `.epubsplit-ignore`:
  - `^cover$`
  - `^title page$`
  - `^table of contents$`
  - `^copyright page$`
  - `^backcover$`

Notes
- TOC Depth: Splits at top‑level TOC entries (EPUB3 nav or EPUB2 NCX). Nested chapters are not merged.
- Assets: Each generated EPUB contains the selected chapter XHTML and shared assets (CSS, images, fonts, JS). Other XHTML files are not bundled to keep splits minimal.
- Metadata: Preserves basic metadata and sets the title to `Original Title — Chapter Title`.
- Nav/NCX: Generated EPUBs do not include a navigation document; many readers handle single‑file spines without it.

Exit Codes
- `0`: Success.
- `1`: Error (e.g., invalid EPUB) or nothing to split after applying ignore rules.
- `2`: CLI usage error.

Advanced Examples
- Check with ignore file: `docker run --rm -i -v "$PWD":/work -w /work ourtool:latest --mode check --ignore-file /work/.epubsplit-ignore < book.epub`
- Split with custom names: `docker run --rm -i ourtool:latest --mode split --name-template "{index:03d}_{title}.epub" < book.epub > chapters.tar`
- Validate locally (non-Docker): `python3 cli.py --mode validate --input out.tar`

Non‑Docker Local Usage (optional)
- Check: `python3 cli.py --mode check --input book.epub`
- Split to directory: `python3 cli.py --mode split --input book.epub --out outdir`
- Validate tar: `python3 cli.py --mode validate --input out.tar`

Limitations
- Only top‑level TOC splitting is supported currently.
- If chapters reference external XHTML (e.g., footnotes pages), those are not copied.
