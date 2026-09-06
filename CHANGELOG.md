# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed

- Treat factual uncertainty terms such as `待核实`、`待补充`、`尚未` and `暂无` as review items instead of automatic high-risk draft hits.
- Ignore `TBD/TBC/TODO/FIXME` when the token appears inside a URL, while retaining detection for standalone visible text.
- Add `suggest_clean_name.py` for safe, preview-only dated filename simplification.
- Add regression tests and document the filename and ambiguity-preservation rules.

## [0.1.0] - 2026-08-25

### Added

- `clean-work-traces` Skill workflow and format-specific reference.
- Local scanner for DOCX/DOCM, PPTX/PPTM, XLSX/XLSM, legacy DOC/PPT/XLS and PDF.
- Detection of drafting terms, review terms, local paths, comments, revisions, notes, hidden content, external links and data connections.
- Recognition of clean source-only comments.
- Standard-library unit tests and GitHub Actions CI.
