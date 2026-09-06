from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "suggest_clean_name.py"
SPEC = importlib.util.spec_from_file_location("suggest_clean_name", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SuggestCleanNameTests(unittest.TestCase):
    def test_preserves_prefix_and_appends_date(self) -> None:
        source = Path("【筛选企业库】匹配过程(20260904)-二级分类-宽口径-785行起-复核版-clean-final.xlsx")
        result = MODULE.suggest_name(source, "宽口径", "20260906")
        self.assertEqual(result.name, "【筛选企业库】匹配过程(20260904)-二级分类-宽口径-20260906.xlsx")

    def test_keeps_extension(self) -> None:
        result = MODULE.suggest_name(Path("report.xlsm"), "report", "20261231")
        self.assertEqual(result.name, "report-20261231.xlsm")

    def test_missing_marker_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.suggest_name(Path("report.xlsx"), "宽口径", "20260906")


if __name__ == "__main__":
    unittest.main()
