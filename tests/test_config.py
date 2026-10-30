import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from troTHU import tron
from troTHU.config_editor import LEGACY_NOTEPAD_PATH
from troTHU.config_view import (
    build_user_config,
    config_doctor_report,
    config_view_summary,
    render_compact_config,
    write_compact_config,
)

SAMPLE_SIMPLE_CONFIG = """now:class A

account:
  user:S1
  passwd:P1
  school:THU

  user:S2
  passwd:P2
  school:tku

grop:
  class:A
    school:THU
    user:S1
    user:S2

operating:
  0:
    enable:true
    range:
    - 09:10
    - 12:00
  1:
    enable:false
    range:
    - 00:00
    - 00:00
"""


class ConfigEditorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_config = tron.copy.deepcopy(tron.CONFIG)
        self.original_last_login_result = tron.LAST_LOGIN_RESULT

    def tearDown(self) -> None:
        tron.CONFIG.clear()
        tron.CONFIG.update(tron.copy.deepcopy(self.original_config))
        tron.LAST_LOGIN_RESULT = self.original_last_login_result

    def test_open_config_uses_system32_notepad(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            process = Mock()
            process.wait = Mock()
            with patch("pathlib.Path.exists", return_value=True), patch("subprocess.Popen", return_value=process) as popen:
                result = tron.open_config_in_legacy_notepad(path, wait=True)

        self.assertTrue(result["ok"])
        self.assertEqual(Path(result["editor"]), LEGACY_NOTEPAD_PATH)
        popen.assert_called_once_with([str(LEGACY_NOTEPAD_PATH), str(path)])
        process.wait.assert_called_once()

    def test_missing_system32_notepad_returns_safe_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.exists", return_value=False):
                result = tron.open_config_in_legacy_notepad(Path(temp_dir) / "config.yaml")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "legacy_notepad_missing")

    def test_ensure_now_opens_editor_when_now_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            tron.CONFIG.clear()
            tron.CONFIG.update(tron.normalize_config(tron.merge_simple_and_advanced_config({"now": "", "accounts": [], "groups": [], "operating": {}}, {})))
            with (
                patch.object(tron, "open_config_in_legacy_notepad", return_value={"ok": True, "status": "opened"}),
                patch.object(tron, "reload_config_after_editor", return_value={"ok": True, "status": "reloaded", "now": ""}),
            ):
                result = tron.ensure_config_now_or_open_editor(path)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "now_empty")

    def test_ensure_now_uses_single_account_without_editor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            simple = {
                "now": "",
                "accounts": [{"user": "SINGLE", "passwd": "SECRET", "school": "thu"}],
                "groups": [],
                "operating": {},
            }
            tron.CONFIG.clear()
            tron.CONFIG.update(tron.normalize_config(tron.merge_simple_and_advanced_config(simple, {})))
            with patch.object(tron, "open_config_in_legacy_notepad") as opener:
                result = tron.ensure_config_now_or_open_editor(path)

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "inferred_single_account")
        self.assertEqual(result["effective_now"], "SINGLE")
        opener.assert_not_called()


class ConfigViewTest(unittest.TestCase):
    def test_compact_config_omits_default_heavy_sections(self) -> None:
        config = tron.normalize_config(copy.deepcopy(tron.DEFAULT_CONFIG))
        text = render_compact_config(config)
        self.assertIn("now:", text)
        self.assertIn("account:", text)
        self.assertIn("group:", text)
        self.assertIn("school:TKU", text)
        self.assertIn("school:TRONCLASS", text)
        self.assertNotIn("school:FJU", text)
        self.assertNotIn("LEGACY CONFIG", text)
        self.assertNotIn("user-agent", text)
        self.assertNotIn("final_grid_step_meters", text)
        self.assertNotIn("research:", text)

    def test_advanced_override_is_preserved(self) -> None:
        config = tron.normalize_config(copy.deepcopy(tron.DEFAULT_CONFIG))
        config["number"]["concurrency"] = 7
        user_config = build_user_config(config)
        self.assertIn("advanced", user_config)
        self.assertEqual(user_config["advanced"]["number"]["concurrency"], 7)
        reloaded = tron.normalize_config(tron.merge_simple_and_advanced_config(user_config["simple"], user_config["advanced"]))
        self.assertEqual(reloaded["number"]["concurrency"], 7)

    def test_write_compact_config_backs_up_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text("account:\n  user: old\n", encoding="utf-8")
            report = write_compact_config(path, tron.DEFAULT_CONFIG, backup_existing=True)
            self.assertEqual(report["status"], "ok")
            self.assertTrue(Path(report["backup_path"]).exists())
            self.assertIn("now:", path.read_text(encoding="utf-8"))

    def test_summary_and_doctor_are_safe(self) -> None:
        config = tron.normalize_config(
            {
                "account": {"user": "  user1  ", "passwd": "  secret  "},
                "provider": {"current": " thu "},
            }
        )
        summary = config_view_summary(config)
        report = config_doctor_report(config)
        text = json.dumps({"summary": summary, "report": report}, ensure_ascii=False)
        self.assertIn("active_profile", summary)
        self.assertNotIn("secret", text)


class SimpleConfigTest(unittest.TestCase):
    def test_parse_simple_config_accepts_group_alias_and_sunday_first_schedule(self) -> None:
        parsed = tron.parse_simple_config_text(SAMPLE_SIMPLE_CONFIG)

        self.assertEqual(parsed["now"], "class A")
        self.assertEqual(len(parsed["accounts"]), 2)
        self.assertEqual(parsed["accounts"][1]["school"], "tku")
        self.assertEqual(parsed["groups"][0]["users"], ["S1", "S2"])
        self.assertEqual(parsed["operating"][0]["range"], ["09:10", "12:00"])

    def test_merge_normalizes_class_target_and_provider(self) -> None:
        parsed = tron.parse_simple_config_text(SAMPLE_SIMPLE_CONFIG)
        config = tron.normalize_config(tron.merge_simple_and_advanced_config(parsed, {}))

        self.assertEqual(config["account"]["user"], "S1")
        self.assertEqual(config["provider"]["current"], "thu")
        self.assertEqual(config["operating"][6]["range"], ["09:10", "12:00"])

    def test_advanced_monitor_ignore_gate_is_preserved(self) -> None:
        original = copy.deepcopy(tron.CONFIG)
        try:
            config = tron.normalize_config({"monitor": {"ignore_attendance_rate_gate": True}})
            tron.CONFIG.clear()
            tron.CONFIG.update(config)

            self.assertTrue(config["monitor"]["ignore_attendance_rate_gate"])
            self.assertTrue(tron.get_ignore_attendance_rate_gate())
            self.assertFalse(tron.get_ignore_attendance_rate_gate(False))
        finally:
            tron.CONFIG.clear()
            tron.CONFIG.update(original)
        self.assertTrue(config["operating"][0]["enable"])

    def test_placeholders_are_empty_and_rendered_without_comments(self) -> None:
        parsed = tron.parse_simple_config_text("now:(填帳號或 class A)\naccount:\n  user:(帳號1)\n  passwd:(密碼1)\n  school:THU\n")
        config = tron.normalize_config(tron.merge_simple_and_advanced_config(parsed, {}))
        simple, advanced = tron.split_normalized_config(config)
        rendered = tron.render_simple_config(simple)

        self.assertEqual(config["account"]["user"], "")
        self.assertEqual(advanced, {})
        self.assertIn("now:(填帳號或 class A)", rendered)
        self.assertNotIn("#", rendered)
        self.assertNotIn("//", rendered)

    def test_blank_now_uses_only_real_account(self) -> None:
        parsed = tron.parse_simple_config_text(
            "now:\naccount:\n  user:SINGLE\n  passwd:SECRET\n  school:THU\n"
        )
        config = tron.normalize_config(tron.merge_simple_and_advanced_config(parsed, {}))

        self.assertEqual(tron.infer_single_account_now(parsed), "SINGLE")
        self.assertEqual(config["account"]["user"], "SINGLE")
        self.assertEqual(config["accounts"]["current"], "SINGLE")

    def test_blank_now_with_multiple_accounts_does_not_guess(self) -> None:
        parsed = tron.parse_simple_config_text(
            "now:\naccount:\n  user:S1\n  passwd:P1\n  school:THU\n\n  user:S2\n  passwd:P2\n  school:THU\n"
        )
        config = tron.normalize_config(tron.merge_simple_and_advanced_config(parsed, {}))

        self.assertEqual(tron.infer_single_account_now(parsed), "")
        self.assertEqual(config["account"]["user"], "")
        self.assertEqual(config["accounts"]["current"], "unset")

    def test_teacher_block_round_trips_in_simple_config(self) -> None:
        parsed = tron.parse_simple_config_text(
            "now:S1\n"
            "account:\n"
            "  user:S1\n"
            "  passwd:P1\n"
            "  school:THU\n"
            "\n"
            "teacher:\n"
            "  user:T1\n"
            "  passwd:TP1\n"
            "  school:TRONCLASS\n"
            "  course:\n"
            "\n"
            "operating:\n"
            "  0:\n"
            "    enable:true\n"
            "    range:\n"
            "    - 00:00 - 00:00\n"
        )
        config = tron.normalize_config(tron.merge_simple_and_advanced_config(parsed, {}))
        simple, advanced = tron.split_normalized_config(config)
        rendered = tron.render_simple_config(simple)
        reparsed = tron.parse_simple_config_text(rendered)

        self.assertEqual(config["teacher"], {"user": "T1", "passwd": "TP1", "school": "tronclass", "course": ""})
        self.assertEqual(advanced, {})
        self.assertIn("teacher:", rendered)
        self.assertIn("  user:T1", rendered)
        self.assertEqual(reparsed["teacher"]["school"], "tronclass")
        self.assertEqual(reparsed["teacher"]["course"], "")


if __name__ == "__main__":
    unittest.main()
