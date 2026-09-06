from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "scan_deliverable.py"
SPEC = importlib.util.spec_from_file_location("scan_deliverable", MODULE_PATH)
SCANNER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SCANNER)


def write_zip(path: Path, files: dict[str, str]) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


class ScanDeliverableTests(unittest.TestCase):
    def test_clean_xlsx_allows_source_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.xlsx"
            write_zip(
                path,
                {
                    "xl/worksheets/sheet1.xml": "<worksheet><sheetData><row><c><is><t>正式内容</t></is></c></row></sheetData></worksheet>",
                    "xl/comments/comment1.xml": (
                        "<comments><authors><author>source</author></authors><commentList>"
                        "<comment ref='A1' authorId='0'><text><t>来源：https://example.com/report</t></text></comment>"
                        "</commentList></comments>"
                    ),
                },
            )
            report = SCANNER.scan_file(path, True)
            self.assertFalse(SCANNER.risky(report))
            self.assertEqual(report["annotations"]["clean_source_comments"], 1)
            self.assertEqual(report["annotations"]["risky_comments"], 0)

    def test_source_comment_requires_explicit_allow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comment.xlsx"
            write_zip(
                path,
                {
                    "xl/worksheets/sheet1.xml": "<worksheet/>",
                    "xl/comments/comment1.xml": (
                        "<comments><commentList><comment ref='A1'><text>"
                        "<t>来源：https://example.com</t></text></comment></commentList></comments>"
                    ),
                },
            )
            report = SCANNER.scan_file(path, False)
            self.assertIn("comments/annotations present", report["structural"])

    def test_source_comment_url_identifier_is_still_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "comment-url-token.xlsx"
            write_zip(
                path,
                {
                    "xl/worksheets/sheet1.xml": "<worksheet/>",
                    "xl/comments/comment1.xml": (
                        "<comments><commentList><comment ref='A1'><text><t>来源：https://example.com/TODO/report</t></text></comment></commentList></comments>"
                    ),
                },
            )
            report = SCANNER.scan_file(path, True)
            self.assertEqual(report["annotations"]["clean_source_comments"], 1)
            self.assertEqual(report["annotations"]["risky_comments"], 0)

    def test_dirty_xlsx_detects_standalone_todo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dirty.xlsx"
            write_zip(
                path,
                {"xl/worksheets/sheet1.xml": "<worksheet><sheetData><row><c><is><t>TODO</t></is></c></row></sheetData></worksheet>"},
            )
            report = SCANNER.scan_file(path, True)
            self.assertTrue(SCANNER.risky(report))
            self.assertTrue(any(hit["term"] == "TODO" for hit in report["high_hits"]))

    def test_dirty_docx_detects_todo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dirty.docx"
            write_zip(path, {"word/document.xml": "<w:document><w:body><w:p><w:r><w:t>TODO</w:t></w:r></w:p></w:body></w:document>"})
            report = SCANNER.scan_file(path, False)
            self.assertTrue(any(hit["term"] == "TODO" for hit in report["high_hits"]))

    def test_todo_in_url_is_not_treated_as_draft_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "url.xlsx"
            write_zip(
                path,
                {
                    "xl/worksheets/sheet1.xml": (
                        "<worksheet><sheetData><row><c><is><t>来源：https://example.com/TODO/report</t></is></c></row></sheetData></worksheet>"
                    ),
                },
            )
            report = SCANNER.scan_file(path, True)
            self.assertFalse(any(hit["term"] == "TODO" for hit in report["high_hits"]))

    def test_uncertainty_is_review_not_high_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "uncertainty.xlsx"
            write_zip(
                path,
                {
                    "xl/worksheets/sheet1.xml": (
                        "<worksheet><sheetData><row><c><is><t>待核实；尚未上市；暂无同类产品</t></is></c></row></sheetData></worksheet>"
                    ),
                },
            )
            report = SCANNER.scan_file(path, True)
            self.assertFalse(report["high_hits"])
            self.assertEqual({hit["term"] for hit in report["review_hits"]}, {"待核实", "尚未", "暂无"})

    def test_dirty_pptx_detects_internal_discussion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dirty.pptx"
            write_zip(path, {"ppt/slides/slide1.xml": "<p:sld><a:t>仅供讨论</a:t></p:sld>"})
            report = SCANNER.scan_file(path, False)
            self.assertTrue(any(hit["term"] == "仅供讨论" for hit in report["high_hits"]))

    def test_legacy_format_requires_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.doc"
            path.write_bytes(b"DRAFT internal document")
            report = SCANNER.scan_file(path, False)
            self.assertIn("conversion required before reliable cleanup", report["structural"])


if __name__ == "__main__":
    unittest.main()
