from __future__ import annotations

import io
import os
import re
import posixpath
import tarfile
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xhtml": "http://www.w3.org/1999/xhtml",
    "epub": "http://www.idpf.org/2007/ops",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
}


def _read_xml_bytes(data: bytes) -> ET.Element:
    return ET.fromstring(data)


def _read_xml_file(zf: zipfile.ZipFile, path: str) -> ET.Element:
    return _read_xml_bytes(zf.read(path))


def find_opf_path(zf: zipfile.ZipFile) -> str:
    root = _read_xml_file(zf, "META-INF/container.xml")
    rootfile = root.find("container:rootfiles/container:rootfile", NS)
    if rootfile is None:
        raise RuntimeError("Invalid EPUB: container.xml missing rootfile")
    full_path = rootfile.get("full-path")
    if not full_path:
        raise RuntimeError("Invalid EPUB: rootfile missing full-path")
    return full_path


def parse_opf(zf: zipfile.ZipFile, opf_path: str):
    opf_root = _read_xml_file(zf, opf_path)
    opf_dir = posixpath.dirname(opf_path)

    manifest_e = opf_root.find("opf:manifest", NS)
    spine_e = opf_root.find("opf:spine", NS)
    metadata_e = opf_root.find("opf:metadata", NS)
    if manifest_e is None or spine_e is None or metadata_e is None:
        raise RuntimeError("Invalid OPF: missing manifest/spine/metadata")

    manifest: Dict[str, Dict[str, Optional[str]]] = {}
    for item in manifest_e.findall("opf:item", NS):
        iid = item.get("id")
        href = item.get("href")
        mt = item.get("media-type")
        props = item.get("properties")
        if iid and href:
            manifest[iid] = {"href": href, "media-type": mt, "properties": props or ""}

    spine: List[str] = []
    for itemref in spine_e.findall("opf:itemref", NS):
        idref = itemref.get("idref")
        if idref:
            spine.append(idref)
    spine_toc_id = spine_e.get("toc")  # EPUB 2

    # Basic metadata
    title_el = metadata_e.find("dc:title", NS)
    title = (title_el.text or "").strip() if title_el is not None else "Untitled"
    lang_el = metadata_e.find("dc:language", NS)
    language = (lang_el.text or "").strip() if lang_el is not None else "en"
    creator_el = metadata_e.find("dc:creator", NS)
    creator = (creator_el.text or "").strip() if creator_el is not None else ""
    version = opf_root.get("version") or "3.0"

    return opf_root, opf_dir, manifest, spine, spine_toc_id, {"title": title, "language": language, "creator": creator, "version": version}


def resolve_path(base_dir: str, href: str) -> str:
    href_no_frag = href.split("#", 1)[0]
    return posixpath.normpath(posixpath.join(base_dir, href_no_frag))


def get_nav_entries_epub3(
    zf: zipfile.ZipFile, opf_dir: str, manifest: Dict[str, Dict[str, Optional[str]]]
) -> Optional[List[Tuple[str, str]]]:
    nav_href = None
    for item in manifest.values():
        props = (item.get("properties") or "").split()
        if "nav" in props:
            nav_href = resolve_path(opf_dir, item.get("href") or "")
            break
    if not nav_href:
        return None
    try:
        nav_root = _read_xml_file(zf, nav_href)
    except KeyError:
        return None

    nav_el = None
    for n in nav_root.findall(".//xhtml:nav", NS):
        epub_type = n.get(f"{{{NS['epub']}}}type") or n.get("type")
        if epub_type and "toc" in epub_type:
            nav_el = n
            break
    if nav_el is None:
        nav_el = nav_root.find(".//xhtml:nav", NS)
    if nav_el is None:
        return None
    ol = nav_el.find("xhtml:ol", NS)
    if ol is None:
        return None

    entries: List[Tuple[str, str]] = []
    for li in ol.findall("xhtml:li", NS):
        a = li.find("xhtml:a", NS)
        if a is None:
            continue
        title = "".join(a.itertext()).strip()
        href = a.get("href") or ""
        if not href:
            continue
        full_path = resolve_path(posixpath.dirname(nav_href), href)
        entries.append((title, full_path))
    return entries


def get_nav_entries_epub2(
    zf: zipfile.ZipFile,
    opf_dir: str,
    manifest: Dict[str, Dict[str, Optional[str]]],
    spine_toc_id: Optional[str],
) -> Optional[List[Tuple[str, str]]]:
    if not spine_toc_id:
        return None
    ncx_item = manifest.get(spine_toc_id)
    if not ncx_item:
        return None
    ncx_href = resolve_path(opf_dir, ncx_item.get("href") or "")
    try:
        ncx_root = _read_xml_file(zf, ncx_href)
    except KeyError:
        return None
    nav_map = ncx_root.find("ncx:navMap", NS)
    if nav_map is None:
        return None

    entries: List[Tuple[str, str]] = []
    for nav_point in nav_map.findall("ncx:navPoint", NS):
        nav_label = nav_point.find("ncx:navLabel/ncx:text", NS)
        title = (nav_label.text or "").strip() if nav_label is not None else ""
        content = nav_point.find("ncx:content", NS)
        src = content.get("src") if content is not None else None
        if not src:
            continue
        full_path = resolve_path(posixpath.dirname(ncx_href), src)
        entries.append((title or posixpath.basename(full_path), full_path))
    return entries


def list_top_level_parts(zf: zipfile.ZipFile) -> Tuple[List[Tuple[str, str]], str, str, Dict[str, Dict[str, Optional[str]]], List[str], Optional[str], Dict[str, str]]:
    opf_path = find_opf_path(zf)
    opf_root, opf_dir, manifest, spine, spine_toc_id, meta = parse_opf(zf, opf_path)
    entries = get_nav_entries_epub3(zf, opf_dir, manifest)
    if not entries:
        entries = get_nav_entries_epub2(zf, opf_dir, manifest, spine_toc_id) or []
    return entries, opf_dir, opf_path, manifest, spine, spine_toc_id, meta


def compile_ignore_patterns(lines: Iterable[str]) -> List[re.Pattern[str]]:
    pats: List[re.Pattern[str]] = []
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        pats.append(re.compile(s, re.IGNORECASE))
    return pats


def load_ignore_file(path: Optional[str]) -> List[re.Pattern[str]]:
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return compile_ignore_patterns(f.readlines())
    if os.path.isfile(".splitpub-ignore"):
        with open(".splitpub-ignore", "r", encoding="utf-8") as f:
            return compile_ignore_patterns(f.readlines())
    return []


def filter_entries(entries: Sequence[Tuple[str, str]], patterns: Sequence[re.Pattern[str]]) -> List[Tuple[str, str]]:
    if not patterns:
        return list(entries)
    out: List[Tuple[str, str]] = []
    for title, path in entries:
        if any(p.search(title) for p in patterns):
            continue
        out.append((title, path))
    return out


def sanitize_filename(name: str) -> str:
    name = name.strip()
    # collapse whitespace
    name = re.sub(r"[\s\u2000-\u206F\u2E00-\u2E7F]+", " ", name)
    name = name.replace("/", "-")
    name = re.sub(r"[^\w\-\. ]+", "", name, flags=re.UNICODE)
    name = name.strip().strip(".-")
    return name or "part"


def write_single_epub(
    zf_src: zipfile.ZipFile,
    out_path: str,
    opf_dir: str,
    manifest: Dict[str, Dict[str, Optional[str]]],
    meta: Dict[str, str],
    chapter_title: str,
    chapter_full_path: str,
) -> None:
    # Locate chapter item
    chapter_item_id = None
    chapter_href_rel = None
    for iid, item in manifest.items():
        href = item.get("href") or ""
        if resolve_path(opf_dir, href) == chapter_full_path:
            chapter_item_id = iid
            chapter_href_rel = href
            break
    if chapter_item_id is None or chapter_href_rel is None:
        raise RuntimeError(f"Chapter file not found in manifest: {chapter_full_path}")

    include_ids: List[str] = [chapter_item_id]
    for iid, item in manifest.items():
        if iid == chapter_item_id:
            continue
        mt = (item.get("media-type") or "").lower()
        if mt.startswith("image/") or mt in {
            "text/css",
            "application/javascript",
            "text/javascript",
            "application/font-woff",
            "font/woff",
            "font/woff2",
            "application/font-woff2",
            "application/vnd.ms-opentype",
            "application/x-font-ttf",
            "font/ttf",
            "image/svg+xml",
        }:
            include_ids.append(iid)

    new_title = f"{meta.get('title','Untitled')} — {chapter_title.strip()}"
    language = meta.get("language", "en")
    creator = meta.get("creator", "")
    version = meta.get("version", "3.0")

    with zipfile.ZipFile(out_path, "w") as zfw:
        # mimetype uncompressed
        zinfo = zipfile.ZipInfo("mimetype")
        zinfo.compress_type = zipfile.ZIP_STORED
        zfw.writestr(zinfo, "application/epub+zip")
        # container
        container_xml = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\">"
            "<rootfiles>"
            "<rootfile full-path=\"OEBPS/content.opf\" media-type=\"application/oebps-package+xml\"/>"
            "</rootfiles>"
            "</container>"
        )
        zfw.writestr("META-INF/container.xml", container_xml)

        # Copy resources
        for iid in include_ids:
            item = manifest[iid]
            href = item.get("href") or ""
            src_full = resolve_path(opf_dir, href)
            dst_path = posixpath.normpath(posixpath.join("OEBPS", posixpath.relpath(src_full, opf_dir)))
            zfw.writestr(dst_path, zf_src.read(src_full))

        # OPF
        chapter_media_type = manifest[chapter_item_id].get("media-type") or "application/xhtml+xml"
        chapter_href_out = posixpath.relpath(resolve_path(opf_dir, chapter_href_rel), opf_dir)

        manifest_items_xml = []
        spine_refs_xml = []
        manifest_items_xml.append(
            f"<item id=\"item_chapter\" href=\"{escape_xml(chapter_href_out)}\" media-type=\"{escape_xml(chapter_media_type)}\"/>"
        )
        res_idx = 0
        for iid in include_ids:
            if iid == chapter_item_id:
                continue
            itm = manifest[iid]
            href = itm.get("href") or ""
            href_out = posixpath.relpath(resolve_path(opf_dir, href), opf_dir)
            mt = itm.get("media-type") or ""
            manifest_items_xml.append(
                f"<item id=\"res{res_idx}\" href=\"{escape_xml(href_out)}\" media-type=\"{escape_xml(mt)}\"/>"
            )
            res_idx += 1
        spine_refs_xml.append("<itemref idref=\"item_chapter\"/>")

        metadata_xml = [
            "<metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\" xmlns:opf=\"http://www.idpf.org/2007/opf\">",
            f"<dc:title>{escape_xml(new_title)}</dc:title>",
            f"<dc:language>{escape_xml(language)}</dc:language>",
        ]
        if creator:
            metadata_xml.append(f"<dc:creator>{escape_xml(creator)}</dc:creator>")
        metadata_xml.append("</metadata>")

        package_xml = (
            f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            f"<package version=\"{escape_xml(version)}\" xmlns=\"http://www.idpf.org/2007/opf\" unique-identifier=\"BookId\">"
            f"{''.join(metadata_xml)}"
            f"<manifest>{''.join(manifest_items_xml)}</manifest>"
            f"<spine>{''.join(spine_refs_xml)}</spine>"
            f"</package>"
        )
        zfw.writestr("OEBPS/content.opf", package_xml)


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def open_input_as_tempfile(path: Optional[str]) -> str:
    """Return a filesystem path to the EPUB. If path is None or '-', read stdin to temp file."""
    if not path or path == "-":
        data = sys.stdin.buffer.read()
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".epub")
        with tf:
            tf.write(data)
        return tf.name
    return path


# Delay sys import until needed to avoid circulars for typing
import sys  # noqa: E402


def check(epub_path: Optional[str], ignore_file: Optional[str], output_format: str = "text") -> int:
    src_path = open_input_as_tempfile(epub_path)
    try:
        with zipfile.ZipFile(src_path, "r") as zf:
            entries, opf_dir, opf_path, manifest, spine, spine_toc_id, meta = list_top_level_parts(zf)
            patterns = load_ignore_file(ignore_file)
            selected = filter_entries(entries, patterns)
    except zipfile.BadZipFile:
        print("ERROR: Not a valid EPUB (zip)")
        return 1

    if output_format == "json":
        import json

        out = {
            "count": len(entries),
            "selected_count": len(selected),
            "entries": [
                {"index": i + 1, "title": t, "path": p, "selected": (t, p) in selected}
                for i, (t, p) in enumerate(entries)
            ],
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    else:
        for i, (title, path) in enumerate(entries, start=1):
            mark = "[x]" if (title, path) in selected else "[ ]"
            sys.stdout.write(f"{i:02d}. {mark} {title} -> {path}\n")
    return 0


def split(
    epub_path: Optional[str],
    ignore_file: Optional[str],
    out_dir: Optional[str],
    name_template: str = "{index:02d} - {title}.epub",
) -> int:
    src_path = open_input_as_tempfile(epub_path)
    patterns = load_ignore_file(ignore_file)
    try:
        with zipfile.ZipFile(src_path, "r") as zf:
            entries, opf_dir, opf_path, manifest, spine, spine_toc_id, meta = list_top_level_parts(zf)
            selected = filter_entries(entries, patterns)
            if not selected:
                print("No chapters selected (consider adjusting ignore rules).")
                return 1

            # Decide output mode
            if not out_dir or out_dir == "-":
                # Write into temp dir then tar to stdout
                with tempfile.TemporaryDirectory() as tmpdir:
                    written: List[str] = []
                    for idx, (title, path) in enumerate(selected, start=1):
                        filename = name_template.format(index=idx, title=sanitize_filename(title))
                        out_path = os.path.join(tmpdir, filename)
                        write_single_epub(zf, out_path, opf_dir, manifest, meta, title, path)
                        written.append(out_path)
                    # Tar to stdout
                    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as tf:
                        for f in written:
                            arcname = os.path.basename(f)
                            tf.add(f, arcname=arcname)
            else:
                os.makedirs(out_dir, exist_ok=True)
                for idx, (title, path) in enumerate(selected, start=1):
                    filename = name_template.format(index=idx, title=sanitize_filename(title))
                    out_path = os.path.join(out_dir, filename)
                    write_single_epub(zf, out_path, opf_dir, manifest, meta, title, path)
                    print(f"Wrote: {out_path}")
    except zipfile.BadZipFile:
        print("ERROR: Not a valid EPUB (zip)")
        return 1
    return 0


def validate_tar(tar_path: Optional[str]) -> int:
    """Validate a tar stream of EPUB files. Reads from stdin if tar_path is '-' or None.
    Prints a simple report: filename and size, and whether each EPUB is a valid ZIP.
    Returns non-zero if any entry fails to validate.
    """
    # Read tar from file or stdin streaming
    if not tar_path or tar_path == "-":
        fileobj = sys.stdin.buffer
        close_needed = False
    else:
        fileobj = open(tar_path, "rb")
        close_needed = True
    bad = 0
    total = 0
    try:
        with tarfile.open(fileobj=fileobj, mode="r|") as tf:
            for m in tf:
                if not m.isfile():
                    continue
                total += 1
                name = m.name
                f = tf.extractfile(m)
                if f is None:
                    print(f"WARN: cannot read {name}")
                    bad += 1
                    continue
                data = f.read()
                size = len(data)
                ok = True
                try:
                    zipfile.ZipFile(io.BytesIO(data)).close()
                except zipfile.BadZipFile:
                    ok = False
                    bad += 1
                status = "OK" if ok else "BAD"
                print(f"{name}\t{size} bytes\t{status}")
    finally:
        if close_needed:
            fileobj.close()
    if total == 0:
        print("No files found in tar.")
        return 1
    return 0 if bad == 0 else 1
