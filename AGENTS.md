# Agents Guide

This repository contains a small CLI tool to split an EPUB into per‑chapter EPUBs. This guide is for AI/code assistants working on the project to implement changes safely and verify behavior end‑to‑end.

## Project Summary
- CLI: `splitpub` with modes `check`, `split`, and `validate`.
- Input: EPUB file via `--input PATH` or stdin (`-`, default).
- Output:
  - `check`: lists TOC entries (text or JSON) to stdout.
  - `split`: writes a tar stream of per‑chapter EPUBs to stdout (default) or files to a directory via `--out`.
  - `validate`: reads a tar (file or stdin) and reports sizes/ZIP validity of each entry.
- TOC: Uses EPUB3 `nav` or EPUB2 `ncx`; splits at top‑level only.
- Exclusions: No defaults. Optional ignore rules via `.splitpub-ignore` or `--ignore-file` (case‑insensitive regexes, one per line).

## Repo Layout (flat)
- `core.py`: Core logic (EPUB parsing, filtering, splitting, validation).
- `cli.py`: CLI argument parsing and command dispatch.
- `__init__.py`: Version info.
- `Dockerfile`: Runtime image for streaming usage.
- `Makefile`: Convenience targets for Docker build/run flows.
- `README.md`: User documentation.
- `.splitpub-ignore.example`: Example ignore rules.

## What To Preserve
- Streaming I/O by default:
  - Read EPUB from stdin when `--input` is `-` or omitted.
  - In `split` mode, tar results to stdout when `--out -` (default).
- No default exclusions; only exclude when rules are present.
- Split at top‑level TOC only (no nested merge or link‑following unless explicitly added behind flags).

## How To Validate Changes
- Local (no Docker):
  - List TOC: `python3 cli.py --mode check --input book.epub --format text`
  - Apply ignores: `python3 cli.py --mode check --input book.epub --ignore-file ignore.txt`
  - Split to tar: `python3 cli.py --mode split --input book.epub > out.tar`
  - Validate tar: `python3 cli.py --mode validate --input out.tar`
- Docker:
  - Build: `docker build -t splitpub:latest .`
  - Check: `docker run --rm -i splitpub:latest --mode check --format json < book.epub`
  - Split to tar: `docker run --rm -i splitpub:latest --mode split < book.epub > out.tar`
  - Validate tar from stdin: `docker run --rm -i splitpub:latest --mode validate --input - < out.tar`
  - Split to directory: `docker run --rm -i -v "$PWD/out":/out splitpub:latest --mode split --out /out < book.epub`
- Makefile shortcuts:
  - `make build`
  - `make check IN=book.epub`
  - `make split-tar IN=book.epub`
  - `make split-dir IN=book.epub OUTDIR=out IGNORE=.splitpub-ignore`
  - `make validate`

## Coding Guidelines
- Keep changes minimal and focused; retain current interfaces and defaults.
- Avoid adding networked dependencies. Use standard library only.
- Ensure `py_compile` passes: `python3 -m py_compile cli.py core.py __init__.py`.
- Maintain streaming behavior: avoid buffering entire tars in memory when possible (we currently stream tar creation/consumption).
- EPUB XML parsing: stick to `xml.etree.ElementTree`; don’t introduce heavy parsers.
- File reads: keep within the provided EPUB zip; avoid reading arbitrary files.

## Backlog / Optional Enhancements
- Flag to include linked XHTML (e.g., footnotes) per chapter.
- Minimal `nav.xhtml`/NCX generation for outputs.
- Optional JSON output for `validate`.
- Packaging as a `pip`-installable module while keeping Docker UX unchanged.

## When To Ask For Clarification
- Changing defaults (e.g., adding auto‑exclusions) or behavior of streaming I/O.
- Altering the TOC level or including content beyond a single top‑level entry.
- Introducing dependencies or non‑standard readers/parsers.

## Definition of Done
- CLI modes work: `check`, `split`, and `validate`.
- Docker image builds and can run the three flows per README.
- Ignore rules respected; no implicit exclusions.
- Local smoke tests succeed on a representative EPUB (TOC detected; split produces valid EPUBs; validate reports OK).
