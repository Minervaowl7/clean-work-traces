#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import BadZipFile, ZipFile


HIGH_TERMS = [
    "草稿", "工作稿", "工作底稿", "内部讨论", "仅供讨论", "不外发",
    "待复核", "待核实", "待补充", "AI生成", "AI撰写", "本字段含",
    "对应内容", "完整核验记录", "删除原表", "修改说明", "调整说明",
    "证据等级", "核验说明", "核验截至", "主表采用", "源CSV", "复现脚本",
    "统计规则", "数据源SHA-256", "TODO", "TBD", "TBC", "FIXME", "DRAFT",
]

REVIEW_TERMS = [
    "未查得", "暂无", "尚未", "仅针对", "不外推", "分期未知", "不填写", "不使用",
]

PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.I),
    re.compile(r"/Users/[^/\s]+", re.I),
    re.compile(r"file://", re.I),
    re.compile(r"(?:^|[\\/])(outputs?|scripts?|temp|tmp)(?:[\\/]|$)", re.I),
]

OPENXML_EXTS = {".docx", ".docm", ".pptx", ".pptm", ".xlsx", ".xlsm"}
LEGACY_EXTS = {".doc", ".ppt", ".xls"}
PDF_EXTS = {".pdf"}


def clean_xml_text(data: bytes) -> str:
    text = data.decode("utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def snippets(text: str, terms: list[str]) -> list[dict]:
    hits = []
    lowered = text.lower()
    for term in terms:
        start = 0
        needle = term.lower()
        while True:
            index = lowered.find(needle, start)
            if index < 0:
                break
            left = max(0, index - 45)
            right = min(len(text), index + len(term) + 45)
            hits.append({"term": term, "snippet": text[left:right]})
            start = index + len(term)
    return hits


def path_hits(text: str) -> list[str]:
    found = []
    for pattern in PATH_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if value not in found:
                found.append(value)
    return found


def is_clean_source_comment(text: str) -> bool:
    normalized = text.strip()
    if not (normalized.startswith("来源") or normalized.lower().startswith("source")):
        return False
    return not snippets(normalized, HIGH_TERMS) and bool(re.search(r"https?://|DOI|ISBN|GB/T|CN\d+", normalized, re.I))


def extract_comment_texts(data: bytes) -> list[str]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        text = clean_xml_text(data)
        return [text] if text else []
    comments = []
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        if local_name not in {"comment", "cm"}:
            continue
        text = " ".join(part.strip() for part in element.itertext() if part.strip())
        if text:
            comments.append(text)
    return comments


def relevant_parts(ext: str, names: list[str]) -> list[str]:
    if ext in {".docx", ".docm"}:
        prefixes = ("word/document.xml", "word/header", "word/footer", "word/footnotes", "word/endnotes", "word/comments")
    elif ext in {".pptx", ".pptm"}:
        prefixes = ("ppt/slides/", "ppt/notesSlides/", "ppt/comments/")
    else:
        prefixes = ("xl/worksheets/", "xl/sharedStrings.xml", "xl/comments")
    return [name for name in names if name.startswith(prefixes) and name.endswith(".xml")]


def scan_openxml(path: Path, allow_source_comments: bool) -> dict:
    ext = path.suffix.lower()
    report = {
        "path": str(path), "format": ext, "integrity": "ok", "high_hits": [],
        "review_hits": [], "path_hits": [], "annotations": {}, "structural": [],
        "metadata_hits": [], "errors": [],
    }
    try:
        with ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                report["integrity"] = f"bad member: {bad}"
                report["errors"].append(report["integrity"])
                return report
            names = archive.namelist()
            for name in relevant_parts(ext, names):
                text = clean_xml_text(archive.read(name))
                target = {"part": name}
                for hit in snippets(text, HIGH_TERMS):
                    report["high_hits"].append(target | hit)
                for hit in snippets(text, REVIEW_TERMS):
                    report["review_hits"].append(target | hit)
                for hit in path_hits(text):
                    report["path_hits"].append({"part": name, "value": hit})

            comment_parts = [
                name for name in names
                if name.endswith(".xml")
                and ("/comments/" in name or re.search(r"/comments?\d*\.xml$", name, re.I))
                and "commentAuthors" not in name
            ]
            total_comments = clean_sources = risky_comments = 0
            for name in comment_parts:
                for text in extract_comment_texts(archive.read(name)):
                    total_comments += 1
                    if is_clean_source_comment(text):
                        clean_sources += 1
                    else:
                        risky_comments += 1
            report["annotations"] = {
                "comment_parts": len(comment_parts), "comments": total_comments,
                "clean_source_comments": clean_sources, "risky_comments": risky_comments,
            }
            if risky_comments or (comment_parts and not allow_source_comments and clean_sources):
                report["structural"].append("comments/annotations present")
            if ext in {".docx", ".docm"}:
                for name in names:
                    if name.startswith("word/") and name.endswith(".xml"):
                        raw = archive.read(name).decode("utf-8", errors="ignore")
                        if re.search(r"<w:(?:ins|del|moveFrom|moveTo)\b|w:trackRevisions", raw):
                            report["structural"].append("tracked revisions")
                            break
                        if re.search(r"w:vanish", raw):
                            report["structural"].append("hidden text")
            if ext in {".pptx", ".pptm"}:
                if any(name.startswith("ppt/notesSlides/") for name in names):
                    report["structural"].append("speaker notes")
                if "ppt/presentation.xml" in names:
                    raw = archive.read("ppt/presentation.xml").decode("utf-8", errors="ignore")
                    if re.search(r"show=\"0\"", raw):
                        report["structural"].append("hidden slides")
            if ext in {".xlsx", ".xlsm"}:
                if "xl/workbook.xml" in names:
                    raw = archive.read("xl/workbook.xml").decode("utf-8", errors="ignore")
                    hidden = re.findall(r"<sheet[^>]+state=\"(hidden|veryHidden)\"", raw)
                    if hidden:
                        report["structural"].append(f"hidden sheets: {len(hidden)}")
                if any(name.startswith("xl/externalLinks/") for name in names):
                    report["structural"].append("external links")
                if "xl/connections.xml" in names or any(name.startswith("xl/queryTables/") for name in names):
                    report["structural"].append("data connections")

            for name in ("docProps/core.xml", "docProps/custom.xml"):
                if name in names:
                    text = clean_xml_text(archive.read(name))
                    paths = path_hits(text)
                    high = snippets(text, HIGH_TERMS)
                    if paths or high:
                        report["metadata_hits"].append({"part": name, "paths": paths, "terms": high})
    except (BadZipFile, OSError) as exc:
        report["integrity"] = "error"
        report["errors"].append(str(exc))
    report["structural"] = sorted(set(report["structural"]))
    return report


def extract_legacy_strings(data: bytes) -> str:
    ascii_strings = [m.group(0).decode("latin1", errors="ignore") for m in re.finditer(rb"[ -~]{5,}", data)]
    utf16_strings = []
    for match in re.finditer(rb"(?:[ -~]\x00){5,}", data):
        utf16_strings.append(match.group(0).decode("utf-16le", errors="ignore"))
    return " ".join(ascii_strings + utf16_strings)


def scan_legacy(path: Path) -> dict:
    report = {
        "path": str(path), "format": path.suffix.lower(), "integrity": "legacy OLE",
        "high_hits": [], "review_hits": [], "path_hits": [], "annotations": {},
        "structural": ["conversion required before reliable cleanup"], "metadata_hits": [], "errors": [],
    }
    try:
        text = extract_legacy_strings(path.read_bytes())
        report["high_hits"] = snippets(text, HIGH_TERMS)
        report["review_hits"] = snippets(text, REVIEW_TERMS)
        report["path_hits"] = [{"value": value} for value in path_hits(text)]
    except OSError as exc:
        report["errors"].append(str(exc))
    return report


def scan_pdf(path: Path) -> dict:
    report = {
        "path": str(path), "format": ".pdf", "integrity": "unknown",
        "high_hits": [], "review_hits": [], "path_hits": [], "annotations": {},
        "structural": [], "metadata_hits": [], "errors": [],
    }
    text = ""
    try:
        try:
            from pypdf import PdfReader

            reader = PdfReader(path)
            text = " ".join((page.extract_text() or "") for page in reader.pages)
            metadata = " ".join(f"{key}={value}" for key, value in (reader.metadata or {}).items())
            if metadata:
                report["metadata_hits"].append({"metadata": metadata})
            annotations = 0
            for page in reader.pages:
                annotations += len(page.get("/Annots", []) or [])
            report["annotations"] = {"pdf_annotations": annotations}
            if annotations:
                report["structural"].append(f"PDF annotations: {annotations}")
            report["integrity"] = "ok"
        except ImportError:
            text = extract_legacy_strings(path.read_bytes())
            report["integrity"] = "binary fallback"
            report["structural"].append("pypdf unavailable; used binary string scan")
        report["high_hits"] = snippets(text, HIGH_TERMS)
        report["review_hits"] = snippets(text, REVIEW_TERMS)
        report["path_hits"] = [{"value": value} for value in path_hits(text)]
    except Exception as exc:
        report["errors"].append(str(exc))
    return report


def scan_file(path: Path, allow_source_comments: bool) -> dict:
    if not path.exists() or not path.is_file():
        return {"path": str(path), "format": path.suffix.lower(), "errors": ["file not found"]}
    ext = path.suffix.lower()
    if ext in OPENXML_EXTS:
        return scan_openxml(path, allow_source_comments)
    if ext in LEGACY_EXTS:
        return scan_legacy(path)
    if ext in PDF_EXTS:
        return scan_pdf(path)
    return {"path": str(path), "format": ext, "errors": ["unsupported format"]}


def risky(report: dict) -> bool:
    return bool(report.get("errors") or report.get("high_hits") or report.get("path_hits") or report.get("structural"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Office deliverables for drafting and workpaper traces.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--json", type=Path, help="Write machine-readable report.")
    parser.add_argument("--allow-source-comments", action="store_true", help="Do not fail on pure source comments.")
    args = parser.parse_args()

    reports = [scan_file(path, args.allow_source_comments) for path in args.files]
    result = {"files": reports, "risky_files": sum(risky(report) for report in reports)}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered + "\n", encoding="utf-8")
    if any(report.get("errors") and report.get("errors") != [] for report in reports):
        return 2
    return 1 if result["risky_files"] else 0


if __name__ == "__main__":
    sys.exit(main())
