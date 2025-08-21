# SplitPub

[![CI](https://github.com/pedromatosonv/splitpub/actions/workflows/ci.yml/badge.svg)](https://github.com/pedromatosonv/splitpub/actions/workflows/ci.yml)

**SplitPub is a lightweight Python utility for splitting EPUB files into per-chapter EPUBs for use with LLMs and related text analysis pipelines.**

It is designed for situations where entire books are too large to process at once — leading to exceeded context limits or the "needle-in-a-haystack" problem in large bodies of text. By extracting chapters as standalone EPUBs, you can more easily feed smaller, focused segments of content to an LLM, enabling more relevant analysis and discussion.

While the tool produces valid EPUBs that can be read in standard apps, its primary purpose is to prepare book content for machine consumption rather than polished human reading.

## Features

- **Chapter-based splitting**: Split an EPUB into per-chapter EPUBs based on top-level TOC entries
- **Streaming I/O**: Read EPUB from stdin, write tar of EPUBs to stdout, or write files to a directory
- **Flexible ignore rules**: Optional ignore patterns via `.splitpub-ignore` or `--ignore-file`
- **Memory efficient**: Streaming I/O with no buffering of entire tar in memory
- **Minimal dependencies**: Simple, dependency-free Python (stdlib only) and minimal Docker image

## Quick Start

### Docker

```bash
# Build the image
docker build -t splitpub:latest .

# Check TOC structure (JSON format)
docker run --rm -i splitpub:latest --mode check --format json < book.epub

# Split to tar archive
docker run --rm -i splitpub:latest --mode split < book.epub > out.tar

# Validate tar from stdin
docker run --rm -i splitpub:latest --mode validate --input - < out.tar

# Split to directory
docker run --rm -i -v "$PWD/out":/out splitpub:latest --mode split --out /out < book.epub
```

### Local Usage

```bash
# Check TOC structure
python3 cli.py --mode check --input book.epub --format text

# Apply ignore patterns
python3 cli.py --mode check --input book.epub --ignore-file ignore.txt

# Split to tar archive
python3 cli.py --mode split --input book.epub > out.tar

# Split to directory
python3 cli.py --mode split --input book.epub --out outdir

# Validate tar archive
python3 cli.py --mode validate --input out.tar
```

## CLI Reference

### Options

| Option | Values | Description |
|--------|--------|-------------|
| `--mode` | `check`, `split`, `validate` | Operation mode (default: `check`) |
| `--input` | `PATH` or `-` | EPUB path or `-` for stdin (default: `-`) |
| `--out` | `DIR` or `-` | Output directory for split mode; `-` streams tar to stdout (default: `-`) |
| `--format` | `text`, `json` | Output format for check mode (default: `text`) |
| `--ignore-file` | `PATH` | Path to ignore patterns file; uses `.splitpub-ignore` when present |
| `--name-template` | `TEMPLATE` | Output filename template (default: `{index:02d} - {title}.epub`) |

## Ignore Rules

Create a `.splitpub-ignore` file or specify a custom ignore file to exclude certain TOC entries:

- Case-insensitive regex patterns, one per line
- Blank lines and `#` comments are ignored
- Any TOC entry whose title matches a pattern is excluded

### Example ignore file

```
# Common sections to exclude
^cover$
^title page$
^table of contents$
^acknowledgments$
^about the author$
```

## Makefile Shortcuts

For convenient development and testing:

```bash
# Build Docker image
make build

# Check EPUB structure
make check IN=book.epub

# Split to tar archive
make split-tar IN=book.epub

# Split to directory with ignore file
make split-dir IN=book.epub OUTDIR=out IGNORE=.splitpub-ignore

# Validate existing tar
make validate
```

## How It Works

- **Chapter extraction**: Generated EPUBs contain the selected chapter XHTML and shared assets (CSS, images, fonts, JS)
- **Metadata preservation**: Basic metadata is preserved; output title becomes `Original Title — Chapter Title`
- **Simplified structure**: No nav/NCX is added to outputs; most readers handle a single-file spine
- **Asset sharing**: Other XHTML files are not bundled to keep outputs focused

## Limitations

- Only top-level TOC splitting is supported
- Linked external XHTML (e.g., footnotes pages) is not included
- Designed primarily for machine consumption rather than polished human reading

## Development

### Testing

```bash
# Run compile check
python3 -m py_compile cli.py core.py __init__.py
```

CI runs smoke tests across Python 3.9–3.12 and Docker workflows.

### Releases

**Automatic releases from tags:**
```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

**Manual releases:**
- Run the Manual Release workflow from the Actions UI
- Enter tag and optional release notes
- See `CHANGELOG.md` for curated notes; release automation uses that when available

A GitHub Release is created automatically from tags. Release notes are auto-generated but can be edited on GitHub if needed.

## License

MIT — see the [LICENSE](LICENSE) file for full text.