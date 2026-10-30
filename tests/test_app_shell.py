import json
import time
import unittest

try:
    import aiohttp
    from aiohttp import web
except (ImportError, ModuleNotFoundError):
    aiohttp = None
    web = None

from troTHU import tron
from troTHU.app_shell import create_app_shell
from troTHU.app_shell_dashboard import (
    build_shell_dashboard_cards,
    build_shell_policy,
    format_shell_dashboard_cards,
    sanitize_shell_dashboard_value,
)
from troTHU.app_shell_polish import (
    build_shell_action_catalog,
    build_shell_drilldown,
    build_shell_ui_model,
    format_shell_ui_summary,
)
from pathlib import Path
import tempfile


def make_config():
    return tron.normalize_config(
        {
            "account": {"user": "u1", "passwd": ""},
            "accounts": {
                "current": "default",
                "profiles": {"default": {"user": "u1", "passwd": "", "label": ""}},
            },
            "radar": {
                "boundary_points": [
                    [24.181000, 120.600000],
                    [24.181000, 120.601000],
                    [24.182000, 120.601000],
                    [24.182000, 120.600000],
                ]
            },
            "webview": {
                "cookie_sync": {
                    "allowed_domains": ["ilearn.thu.edu.tw"],
                    "cookie_name_allowlist": ["session"],
                }
            },
        }
    )


class RunningApp:
    def __init__(self, app) -> None:
        self.app = app
        self.runner = None
        self.site = None
        self.base_url = ""

    async def __aenter__(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await self.site.start()
        port = self.site._server.sockets[0].getsockname()[1]
        self.base_url = "http://127.0.0.1:{}".format(port)
        return self

    async def __aexit__(self, _exc_type, _exc, _tb) -> None:
        await self.runner.cleanup()


@unittest.skipUnless(aiohttp is not None and web is not None, "aiohttp.web is required")
class AppShellTest(unittest.IsolatedAsyncioTestCase):
    async def test_app_html_contains_tabs_and_runtime_token_only(self) -> None:
        token = "local-token"
        async with RunningApp(create_app_shell(make_config(), token=token)) as app:
            async with aiohttp.ClientSession() as session:
                response = await session.get(app.base_url + "/app")
                text = await response.text()

        self.assertEqual(response.status, 200)
        for marker in (
            "Overview",
            "Dashboard Cards",
            "Accounts",
            "QR Preview",
            "Radar Assist",
            "WebView Sync",
            "Release Check",
            "Release Plan",
            "Shell Policy",
            "UI Model",
            "Action Catalog",
            "Logs",
            "Diagnostics",
        ):
            self.assertIn(marker, text)
        self.assertIn(token, text)
        self.assertNotIn("secret-placeholder", text)

    async def test_health_requires_valid_unexpired_token(self) -> None:
        async with RunningApp(
            create_app_shell(make_config(), token="good", token_expires_at=time.time() + 60)
        ) as app:
            async with aiohttp.ClientSession() as session:
                missing = await session.get(app.base_url + "/app/api/health")
                wrong = await session.get(app.base_url + "/app/api/health", headers={"X-Local-Token": "bad"})
                valid = await session.get(app.base_url + "/app/api/health", headers={"X-Local-Token": "good"})
                body = await valid.json()

        self.assertEqual(missing.status, 401)
        self.assertEqual(wrong.status, 401)
        self.assertEqual(valid.status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["read_only"])
        self.assertIn("qr_submit", body["disabled_mutations"])

        async with RunningApp(
            create_app_shell(make_config(), token="old", token_expires_at=time.time() - 1)
        ) as app:
            async with aiohttp.ClientSession() as session:
                expired = await session.get(app.base_url + "/app/api/health", headers={"X-Local-Token": "old"})
        self.assertEqual(expired.status, 401)

    async def test_read_only_routes_return_sanitized_injected_summaries(self) -> None:
        app_shell = create_app_shell(
            make_config(),
            token="good",
            snapshot_builder=lambda: {"active_profile": "default", "raw_body": "secret-value"},
            accounts_builder=lambda: {"profiles": ["default"], "cookie_value": "cookie-value"},
            log_summary_builder=lambda: {"events": {"ok": 1}, "message": "fine"},
            diagnostics_builder=lambda: {"checks": [{"name": "ok", "status": "ok"}], "token": "token-secret"},
            integrations_builder=lambda: {"bindings": 1, "authorization": "Bearer hidden"},
        )
        async with RunningApp(app_shell) as app:
            async with aiohttp.ClientSession(headers={"X-Local-Token": "good"}) as session:
                paths = [
                    "/app/api/snapshot",
                    "/app/api/accounts",
                    "/app/api/logs/summary",
                    "/app/api/diagnostics",
                    "/app/api/integrations/capabilities",
                    "/app/api/radar/assist",
                    "/app/api/dashboard/cards",
                    "/app/api/release/check",
                    "/app/api/release/plan",
                    "/app/api/shell/policy",
                    "/app/api/ui/model",
                    "/app/api/ui/drilldown/overview",
                    "/app/api/actions/catalog",
                ]
                texts = []
                for path in paths:
                    response = await session.get(app.base_url + path)
                    texts.append(await response.text())
                    self.assertEqual(response.status, 200)

        combined = "\n".join(texts)
        self.assertNotIn("secret-value", combined)
        self.assertNotIn("cookie-value", combined)
        self.assertNotIn("token-secret", combined)
        self.assertNotIn("Bearer hidden", combined)
        self.assertIn("default", combined)

    async def test_qr_preview_never_echoes_raw_payload(self) -> None:
        def fake_preview(raw):
            return {
                "ok": True,
                "rollcall_id": "qr-1",
                "raw": raw,
                "token": "token-secret",
                "nested": {"payload_value": raw},
            }

        async with RunningApp(create_app_shell(make_config(), token="good", qr_previewer=fake_preview)) as app:
            async with aiohttp.ClientSession(headers={"X-Local-Token": "good"}) as session:
                response = await session.post(
                    app.base_url + "/app/api/qr/preview",
                    json={"payload": "RAW-QR-SECRET"},
                )
                text = await response.text()
                body = json.loads(text)

        self.assertEqual(response.status, 200)
        self.assertEqual(body["preview"]["rollcall_id"], "qr-1")
        self.assertNotIn("RAW-QR-SECRET", text)
        self.assertNotIn("token-secret", text)

    async def test_webview_cookie_preview_never_echoes_cookie_value(self) -> None:
        async with RunningApp(create_app_shell(make_config(), token="good")) as app:
            async with aiohttp.ClientSession(headers={"X-Local-Token": "good"}) as session:
                response = await session.post(
                    app.base_url + "/app/api/webview/cookies/preview",
                    json={
                        "export": [
                            {
                                "name": "session",
                                "value": "session-secret",
                                "domain": "ilearn.thu.edu.tw",
                                "path": "/",
                            }
                        ]
                    },
                )
                text = await response.text()
                body = json.loads(text)

        self.assertEqual(response.status, 200)
        self.assertEqual(body["preview"]["accepted_count"], 1)
        self.assertNotIn("session-secret", text)

    async def test_new_safe_routes_require_token_and_return_summaries(self) -> None:
        app_shell = create_app_shell(
            make_config(),
            token="good",
            release_check_builder=lambda: {"status": "warn", "checks": []},
            release_plan_builder=lambda: {"version": "release-build-plan-v1", "executes_build": False},
        )
        async with RunningApp(app_shell) as app:
            async with aiohttp.ClientSession() as session:
                unauthorized = await session.get(app.base_url + "/app/api/release/check")
            async with aiohttp.ClientSession(headers={"X-Local-Token": "good"}) as session:
                release = await session.get(app.base_url + "/app/api/release/check")
                plan = await session.get(app.base_url + "/app/api/release/plan")
                policy = await session.get(app.base_url + "/app/api/shell/policy")
                ui = await session.get(app.base_url + "/app/api/ui/model")
                drilldown = await session.get(app.base_url + "/app/api/ui/drilldown/overview")
                actions = await session.get(app.base_url + "/app/api/actions/catalog")
                cards = await session.get(app.base_url + "/app/api/dashboard/cards")
                radar = await session.get(app.base_url + "/app/api/radar/validate?lat=24.1815&lon=120.6005")

                release_body = await release.json()
                plan_body = await plan.json()
                policy_body = await policy.json()
                ui_body = await ui.json()
                drilldown_body = await drilldown.json()
                actions_body = await actions.json()
                cards_body = await cards.json()
                radar_body = await radar.json()

        self.assertEqual(unauthorized.status, 401)
        self.assertEqual(release.status, 200)
        self.assertEqual(plan.status, 200)
        self.assertEqual(policy.status, 200)
        self.assertEqual(ui.status, 200)
        self.assertEqual(drilldown.status, 200)
        self.assertEqual(actions.status, 200)
        self.assertEqual(cards.status, 200)
        self.assertEqual(radar.status, 200)
        self.assertEqual(release_body["release"]["status"], "warn")
        self.assertFalse(plan_body["release_plan"]["executes_build"])
        self.assertTrue(policy_body["read_only"])
        self.assertIn("panels", ui_body["ui_model"])
        self.assertEqual(drilldown_body["drilldown"]["panel"], "overview")
        self.assertTrue(actions_body["actions"]["read_only"])
        self.assertIn("cards", cards_body["dashboard"])
        self.assertTrue(radar_body["validation"]["ok"])

    async def test_action_handoff_does_not_echo_payload_or_execute(self) -> None:
        async with RunningApp(create_app_shell(make_config(), token="good")) as app:
            async with aiohttp.ClientSession(headers={"X-Local-Token": "good"}) as session:
                response = await session.post(
                    app.base_url + "/app/api/actions/handoff",
                    json={"action": "qr_submit", "payload": "RAW-QR-SECRET", "cookie_value": "session-secret"},
                )
                text = await response.text()
                body = json.loads(text)

        self.assertEqual(response.status, 200)
        self.assertFalse(body["handoff"]["executes_command"])
        self.assertFalse(body["handoff"]["writes_state"])
        self.assertIn("qr paste", body["handoff"]["command_template"])
        self.assertNotIn("RAW-QR-SECRET", text)
        self.assertNotIn("session-secret", text)


class AppShellDashboardTest(unittest.TestCase):
    def test_dashboard_cards_aggregate_safe_local_state(self) -> None:
        model = build_shell_dashboard_cards(
            snapshot={
                "provider": {"key": "thu", "support_level": "ready", "daily_ready": True},
                "runtime_state": {"bot_state": "running", "last_check": "ok", "last_login": "ok"},
                "cookie": {"exists": True, "valid": True, "age_seconds": 3},
                "pending_qr": [{"rollcall_id": "r1"}],
                "logs": {"record_count": 9},
            },
            release_report={"status": "warn"},
            policy=build_shell_policy(route_count=18),
        )

        self.assertEqual(model["status"], "ok")
        self.assertTrue(model["read_only"])
        self.assertTrue(model["preview_only"])
        card_ids = {card["id"] for card in model["cards"]}
        self.assertIn("release", card_ids)
        self.assertIn("shell_policy", card_ids)

    def test_dashboard_sanitizer_removes_sensitive_values(self) -> None:
        value = sanitize_shell_dashboard_value(
            {
                "password": "secret-password",
                "nested": {"cookie_value": "cookie-secret", "message": "token-abc123"},
                "safe": "hello",
            }
        )
        encoded = json.dumps(value, ensure_ascii=False)

        self.assertEqual(value["safe"], "hello")
        self.assertNotIn("secret-password", encoded)
        self.assertNotIn("cookie-secret", encoded)
        self.assertNotIn("token-abc123", encoded)

    def test_policy_lists_disabled_mutations(self) -> None:
        policy = build_shell_policy(route_count=18)

        self.assertTrue(policy["local_only"])
        self.assertTrue(policy["read_only"])
        self.assertIn("qr_submit", policy["disabled_mutations"])
        self.assertIn("release_build", policy["disabled_mutations"])

    def test_formatter_outputs_short_card_lines(self) -> None:
        lines = format_shell_dashboard_cards(
            build_shell_dashboard_cards(
                snapshot={"provider": {"key": "thu", "daily_ready": True}},
                release_report={"status": "ok"},
                policy=build_shell_policy(route_count=18),
            )
        )
        text = "\n".join(lines)

        self.assertIn("App shell dashboard: ok", text)
        self.assertIn("Release", text)


class AppShellPolishTest(unittest.TestCase):
    def test_ui_model_contains_panels_badges_actions_and_safe_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = build_shell_ui_model(
                make_config(),
                base_dir=Path(temp_dir),
                reports={
                    "release_check": {"status": "ok", "token": "token-secret"},
                    "logs_summary": {"recent_events": {"errors": [{"raw_body": "secret"}]}},
                },
            )
            encoded = json.dumps(model, ensure_ascii=False).lower()

        self.assertEqual(model["status"], "ok")
        self.assertTrue(model["read_only"])
        self.assertTrue(model["preview_only"])
        self.assertEqual(model["badges"]["release"]["status"], "ok")
        self.assertIn("actions", model["action_catalog"])
        self.assertNotIn("token-secret", encoded)
        self.assertNotIn("secret", encoded)

    def test_drilldown_and_catalog_never_execute_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = make_config()
            catalog = build_shell_action_catalog(config)
            drilldown = build_shell_drilldown(
                "qr-preview",
                config=config,
                base_dir=Path(temp_dir),
                reports={"qr-preview": {"payload": "RAW-QR", "cookie_value": "cookie-secret"}},
            )
            encoded = json.dumps({"catalog": catalog, "drilldown": drilldown}, ensure_ascii=False)

        self.assertTrue(catalog["read_only"])
        self.assertTrue(catalog["preview_only"])
        self.assertTrue(all(not action["executes_in_shell"] for action in catalog["actions"]))
        self.assertIn("qr-preview", drilldown["panel"])
        self.assertNotIn("RAW-QR", encoded)
        self.assertNotIn("cookie-secret", encoded)

    def test_summary_formatter_is_stable(self) -> None:
        model = build_shell_ui_model(make_config(), base_dir=Path("."))
        text = "\n".join(format_shell_ui_summary(model))

        self.assertIn("App shell polish", text)
        self.assertIn("Read-only: yes", text)


if __name__ == "__main__":
    unittest.main()
