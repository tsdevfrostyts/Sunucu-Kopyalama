import copy
import io
import json
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from copier import ApiError, Cancelled, CopyError, DiscordAPI, NoRedirect, execute, preview


SOURCE = "111111111111111111"
TARGET = "222222222222222222"
OWNER = "333333333333333333"
MEMBER = "444444444444444444"
SOURCE_ROLE = "111111111111111112"
SOURCE_CATEGORY = "111111111111111121"
SOURCE_TEXT = "111111111111111122"
SOURCE_VOICE = "111111111111111123"
TARGET_ROLE = "222222222222222223"
MANAGED_ROLE = "222222222222222224"
OLD_CATEGORY = "222222222222222231"
OLD_CHANNEL = "222222222222222232"


def role(rid, name, position, permissions="0", managed=False):
    return {"id": rid, "name": name, "position": position, "permissions": permissions,
            "managed": managed, "color": 0x654321, "hoist": False, "mentionable": False}


def fixture():
    overwrites = [{"id": SOURCE, "type": 0, "allow": "0", "deny": "1024"},
                  {"id": SOURCE_ROLE, "type": 0, "allow": "1024", "deny": "0"},
                  {"id": MEMBER, "type": 1, "allow": "2048", "deny": "0"}]
    return {
        SOURCE: {"guild": {"id": SOURCE, "name": "Kaynak", "owner_id": OWNER, "features": [], "premium_tier": 0},
                 "roles": [role(SOURCE_ROLE, "Ekip", 3, "3072"), role(SOURCE, "@everyone", 0, "1024")],
                 "channels": [
                     {"id": SOURCE_TEXT, "name": "sohbet", "type": 0, "position": 1,
                      "parent_id": SOURCE_CATEGORY, "topic": "Konu", "rate_limit_per_user": 7,
                      "permission_overwrites": copy.deepcopy(overwrites)},
                     {"id": SOURCE_CATEGORY, "name": "Genel", "type": 4, "position": 2,
                      "permission_overwrites": copy.deepcopy(overwrites)},
                     {"id": SOURCE_VOICE, "name": "Ses", "type": 2, "position": 0,
                      "parent_id": SOURCE_CATEGORY, "bitrate": 96000, "user_limit": 5,
                      "permission_overwrites": []}]},
        TARGET: {"guild": {"id": TARGET, "name": "Hedef", "owner_id": OWNER, "features": [], "premium_tier": 0},
                 "roles": [role(TARGET, "@everyone", 0), role(TARGET_ROLE, "Eski", 1),
                           role(MANAGED_ROLE, "Entegrasyon", 8, managed=True)],
                 "channels": [
                     {"id": OLD_CATEGORY, "name": "Eski kategori", "type": 4, "position": 0, "permission_overwrites": []},
                     {"id": OLD_CHANNEL, "name": "eski-sohbet", "type": 0, "position": 0,
                      "parent_id": OLD_CATEGORY, "permission_overwrites": []}]}}


class MemoryAPI:
    """An isolated server model: it cannot make network requests or hold credentials."""

    def __init__(self):
        self.states = fixture()
        self.user = {"id": OWNER, "bot": False}
        self.members = {MEMBER}
        self.member_roles = {OWNER: [TARGET_ROLE]}
        self.calls = []
        self.cancel = threading.Event()
        self.before_write = None
        self.fail_write = None
        self.cancel_after_writes = None
        self.ignore_channel_positions = False
        self.drop_channel_topics = False
        self.next_id = 900000000000000000

    @property
    def writes(self):
        return [call for call in self.calls if call[0] != "GET"]

    def request(self, method, path, data=None):
        if self.cancel.is_set():
            raise Cancelled("Durduruldu")
        if method != "GET":
            if self.before_write:
                self.before_write(method, path, data)
            if self.fail_write and self.fail_write(method, path, data):
                raise ApiError(403)
        self.calls.append((method, path, copy.deepcopy(data)))
        result = self._request(method, path, data)
        if method != "GET" and self.cancel_after_writes == len(self.writes):
            self.cancel.set()
        return copy.deepcopy(result)

    def _request(self, method, path, data):
        if method == "GET" and path == "/users/@me":
            return self.user
        parts = path.strip("/").split("/")
        if parts[0] == "channels" and method == "DELETE":
            for state in self.states.values():
                for channel in state["channels"]:
                    if channel["id"] == parts[1]:
                        if "COMMUNITY" in state["guild"].get("features", []) and channel["id"] in {
                                state["guild"].get("rules_channel_id"), state["guild"].get("public_updates_channel_id")}:
                            raise ApiError(400)
                        state["channels"].remove(channel)
                        return None
            raise ApiError(404)
        if parts[0] != "guilds" or parts[1] not in self.states:
            raise AssertionError((method, path, data))
        state = self.states[parts[1]]
        if method == "PATCH" and len(parts) == 2:
            for key, channel_id in data.items():
                if key in ("rules_channel_id", "public_updates_channel_id"):
                    if not any(item["id"] == channel_id and item["type"] in (0, 5) for item in state["channels"]):
                        raise ApiError(400)
            state["guild"].update(copy.deepcopy(data))
            return state["guild"]
        if method == "GET":
            if len(parts) == 2:
                return state["guild"]
            if parts[2] == "members":
                if parts[3] not in self.members and parts[3] not in self.member_roles:
                    raise ApiError(404)
                return {"user": {"id": parts[3]}, "roles": self.member_roles.get(parts[3], [])}
            return state[parts[2]]
        collection = state[parts[2]]
        if method == "DELETE":
            existing = next(item for item in collection if item["id"] == parts[3])
            if existing.get("managed") or existing["id"] == parts[1]:
                raise AssertionError("Cannot delete managed or everyone role")
            collection.remove(existing)
            return None
        if method == "POST":
            self.next_id += 1
            item = {"id": str(self.next_id), "position": 0, **copy.deepcopy(data)}
            if parts[2] == "roles":
                item["managed"] = False
            if self.drop_channel_topics and parts[2] == "channels":
                item.pop("topic", None)
            collection.append(item)
            return item
        if method == "PATCH":
            if len(parts) == 4:
                item = next(item for item in collection if item["id"] == parts[3])
                item.update(copy.deepcopy(data))
                return item
            if self.ignore_channel_positions and parts[2] == "channels":
                for item in collection:
                    item["position"] = 1000 - int(item["id"])
                return collection
            for patch in data:
                next(item for item in collection if item["id"] == patch["id"]).update(copy.deepcopy(patch))
            return collection
        raise AssertionError((method, path, data))


class CopierTests(unittest.TestCase):
    def setUp(self):
        self.api = MemoryAPI()
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name) / "backups"
        self.addCleanup(self.temp.cleanup)

    def plan(self):
        return preview(self.api, SOURCE, TARGET)

    def assert_no_writes(self):
        self.assertEqual(self.api.writes, [])
        self.assertFalse(self.directory.exists())

    def test_same_server_is_rejected_before_any_api_call(self):
        with self.assertRaises(CopyError):
            preview(self.api, SOURCE, SOURCE)
        self.assertEqual(self.api.calls, [])
        self.assert_no_writes()

    def test_invalid_ids_are_rejected_without_network_or_mutations(self):
        for invalid in ("", "../server", "1" * 21, "18446744073709551616", "https://discord.com/channels/123"):
            with self.subTest(invalid=invalid), self.assertRaises(CopyError):
                preview(self.api, invalid, TARGET)
        self.assertEqual(self.api.calls, [])
        self.assert_no_writes()

    def test_destination_requires_admin_when_not_owner(self):
        self.api.states[TARGET]["guild"]["owner_id"] = MEMBER
        with self.assertRaises(CopyError):
            self.plan()
        self.assert_no_writes()

    def test_non_owner_administrator_can_copy_without_retyping_id(self):
        self.api.states[TARGET]["guild"]["owner_id"] = MEMBER
        next(r for r in self.api.states[TARGET]["roles"] if r["id"] == TARGET_ROLE)["permissions"] = "8"
        plan = self.plan()
        self.api.fail_write = lambda method, path, data: method == "DELETE" and path.endswith("/" + TARGET_ROLE)
        messages = []
        result = execute(self.api, plan, self.directory, log=messages.append)
        self.assertTrue(any(c["name"] == "sohbet" for c in self.api.states[TARGET]["channels"]))
        self.assertGreaterEqual(result["remaining_roles"], 1)
        self.assertTrue(any("SİLİNEMEDİ" in m and TARGET_ROLE in m and "Eski" in m for m in messages))

    def test_admin_is_rechecked_before_first_mutation(self):
        self.api.states[TARGET]["guild"]["owner_id"] = MEMBER
        admin = next(r for r in self.api.states[TARGET]["roles"] if r["id"] == TARGET_ROLE)
        admin["permissions"] = "8"
        plan = self.plan()
        admin["permissions"] = "0"
        with self.assertRaises(CopyError):
            execute(self.api, plan, self.directory)
        self.assert_no_writes()

    def test_empty_destination_skips_deletes(self):
        self.api.states[TARGET]["roles"] = [role(TARGET, "@everyone", 0)]
        self.api.states[TARGET]["channels"] = []
        result = execute(self.api, self.plan(), self.directory)
        self.assertEqual(result["deletion_failures"], 0)
        self.assertFalse(any(method == "DELETE" for method, _, _ in self.api.calls))

    def test_failed_channel_and_role_deletion_continue_and_are_reported(self):
        self.api.fail_write = lambda method, path, data: method == "DELETE" and (path.endswith(OLD_CHANNEL) or path.endswith(TARGET_ROLE))
        messages = []
        result = execute(self.api, self.plan(), self.directory, log=messages.append)
        target = self.api.states[TARGET]
        self.assertTrue(any(c["id"] == OLD_CHANNEL for c in target["channels"]))
        self.assertTrue(any(c["name"] == "sohbet" for c in target["channels"]))
        self.assertTrue(any(r["name"] == "Ekip" for r in target["roles"]))
        self.assertEqual(result["remaining_channels"], 1)
        self.assertEqual(result["remaining_roles"], 2)
        self.assertTrue(any(m.startswith("SİLİNEMEDİ | Kanal: eski-sohbet") and OLD_CHANNEL in m for m in messages))
        self.assertTrue(any(m.startswith("SİLİNEMEDİ | Rol: Eski") and TARGET_ROLE in m for m in messages))

    def test_ambiguous_delete_failure_continues_without_retrying_delete(self):
        original = self.api.request
        attempts = []
        def flaky(method, path, data=None):
            if method == "DELETE" and path.endswith(OLD_CHANNEL):
                attempts.append(path)
                raise CopyError("Sonuç belirsiz")
            return original(method, path, data)
        self.api.request = flaky
        result = execute(self.api, self.plan(), self.directory)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(result["remaining_channels"], 1)

    def test_global_role_permissions_and_guild_settings_are_not_written(self):
        original = copy.deepcopy(self.api.states[TARGET]["guild"])
        everyone = self.api.states[TARGET]["roles"][0]["permissions"]
        execute(self.api, self.plan(), self.directory)
        self.assertEqual(self.api.states[TARGET]["guild"], original)
        self.assertEqual(self.api.states[TARGET]["roles"][0]["permissions"], everyone)
        for method, path, payload in self.api.writes:
            self.assertNotEqual((method, path), ("PATCH", f"/guilds/{TARGET}"))
            self.assertNotEqual((method, path), ("PATCH", f"/guilds/{TARGET}/roles/{TARGET}"))
            if method == "POST" and path.endswith("/roles"):
                self.assertEqual(set(payload), {"name", "colors"})
                self.assertEqual(payload["colors"], {"primary_color": 0x654321})

    def test_bot_accounts_are_rejected(self):
        self.api.user["bot"] = True
        with self.assertRaises(CopyError):
            self.plan()
        self.assert_no_writes()

    def test_missing_members_are_ignored_and_only_role_overwrites_are_copied(self):
        self.api.members.clear()
        plan = self.plan()
        execute(self.api, plan, self.directory)
        self.assertFalse(any("/members/" in path for _, path, _ in self.api.calls))
        for channel in self.api.states[TARGET]["channels"]:
            self.assertTrue(all(o["type"] == 0 for o in channel.get("permission_overwrites", [])))

    def test_unsupported_channels_stop_before_deletion(self):
        self.api.states[SOURCE]["channels"][0]["type"] = 10
        with self.assertRaises(CopyError):
            self.plan()
        self.assert_no_writes()

    def test_forum_voice_and_converted_special_channels_copy_without_extra_settings(self):
        for original_kind, expected_kind in ((0, 0), (2, 2), (5, 0), (13, 2), (15, 15), (16, 0)):
            with self.subTest(original_kind=original_kind):
                api = MemoryAPI()
                channel = api.states[SOURCE]["channels"][0]
                channel.update(type=original_kind, available_tags=[{"name": "Tag", "id": "888"}],
                               topic="Forum rules", default_reaction_emoji={"emoji_name": "test"},
                               default_sort_order=1, default_forum_layout=2, nsfw=True)
                execute(api, preview(api, SOURCE, TARGET), self.directory)
                copied = next(c for c in api.states[TARGET]["channels"] if c["name"] == "sohbet")
                self.assertEqual(copied["type"], expected_kind)
                sent = next(payload for method, path, payload in api.writes if method == "POST" and path.endswith("/channels") and payload["name"] == "sohbet")
                self.assertEqual(set(sent), {"name", "type", "parent_id", "permission_overwrites"})
                self.assertTrue(all(o["type"] == 0 for o in sent["permission_overwrites"]))
                self.assertFalse(any(method == "PATCH" and path == f"/guilds/{TARGET}" for method, path, _ in api.writes))

    def test_source_destination_or_account_change_invalidates_preview(self):
        for change in ("source", "target", "account"):
            with self.subTest(change=change):
                self.api = MemoryAPI()
                plan = self.plan()
                if change == "account":
                    self.api.user["id"] = MEMBER
                    self.api.states[TARGET]["guild"]["owner_id"] = MEMBER
                else:
                    self.api.states[SOURCE if change == "source" else TARGET]["channels"][0]["name"] += "-changed"
                with self.assertRaises(CopyError):
                    execute(self.api, plan, self.directory)
                self.assert_no_writes()

    def test_activity_metadata_and_api_list_order_do_not_invalidate_preview(self):
        plan = self.plan()
        for state in self.api.states.values():
            state["guild"].update(features=["COMMUNITY", "ANIMATED_ICON"], premium_tier=2,
                                  rules_channel_id="777777777777777777")
            state["roles"].reverse()
            state["channels"].reverse()
            for role_item in state["roles"]:
                role_item.update(hoist=True, mentionable=True, flags=1, icon="updated")
                role_item["colors"] = {"primary_color": role_item.pop("color"), "secondary_color": None}
            for channel in state["channels"]:
                channel.update(last_message_id="888888888888888888", last_pin_timestamp="2026-10-22T12:00:00Z",
                               status="active", topic="Updated topic", available_tags=[{"name": "New tag"}])
                channel["permission_overwrites"].reverse()
                channel["permission_overwrites"].append({"id": "999999999999999999", "type": 1, "allow": "1024", "deny": "0"})
        result = execute(self.api, plan, self.directory)
        self.assertTrue(result["backup"].exists())
        self.assertTrue(any(c["name"] == "sohbet" for c in self.api.states[TARGET]["channels"]))

    def test_role_color_and_role_channel_permission_changes_still_block_deletion(self):
        for change in ("role_color", "channel_permission", "parent"):
            with self.subTest(change=change):
                self.api = MemoryAPI()
                plan = self.plan()
                if change == "role_color":
                    self.api.states[SOURCE]["roles"][0]["color"] = 0x123456
                elif change == "channel_permission":
                    self.api.states[SOURCE]["channels"][0]["permission_overwrites"][0]["deny"] = "2048"
                else:
                    self.api.states[SOURCE]["channels"][0]["parent_id"] = None
                with self.assertRaisesRegex(CopyError, "Kaynak sunucunun rol/kanal yapısı"):
                    execute(self.api, plan, self.directory)
                self.assert_no_writes()

    def test_durable_structure_backup_precedes_first_mutation(self):
        plan = self.plan()
        original_source = copy.deepcopy(self.api.states[SOURCE])
        original_target = copy.deepcopy(self.api.states[TARGET])
        observed_backups = []

        def check_backup(method, path, data):
            backups = list(self.directory.glob("*.json"))
            self.assertEqual(len(backups), 1)
            content = json.loads(backups[0].read_text(encoding="utf-8"))
            self.assertEqual(content["target_before"], original_target)
            self.assertEqual(content["source"], original_source)
            self.assertEqual(set(content), {"format", "created_at", "notice", "source", "target_before"})
            observed_backups.append(backups[0])

        self.api.before_write = check_backup
        path = execute(self.api, plan, self.directory)
        self.assertEqual(path["backup"], observed_backups[0])
        self.assertGreater(len(observed_backups), 1)
        self.assertEqual(self.api.states[SOURCE], original_source)

    def test_backup_failure_prevents_all_mutation(self):
        plan = self.plan()
        self.directory.write_text("not a directory", encoding="utf-8")
        with self.assertRaises((CopyError, OSError)):
            execute(self.api, plan, self.directory)
        self.assertEqual(self.api.writes, [])

    def test_copy_maps_roles_categories_and_permissions_and_preserves_managed_role(self):
        plan = self.plan()
        execute(self.api, plan, self.directory)
        target = self.api.states[TARGET]
        roles = {item["name"]: item for item in target["roles"]}
        channels = {item["name"]: item for item in target["channels"]}
        self.assertEqual(set(roles), {"@everyone", "Ekip", "Entegrasyon"})
        self.assertEqual(roles["Entegrasyon"]["id"], MANAGED_ROLE)
        self.assertTrue(roles["Entegrasyon"]["managed"])
        self.assertEqual(roles["@everyone"]["permissions"], "0")
        self.assertEqual(roles["Ekip"]["colors"]["primary_color"], 0x654321)
        self.assertNotEqual(roles["Ekip"]["id"], SOURCE_ROLE)
        self.assertEqual(set(channels), {"Genel", "sohbet", "Ses"})
        for name in ("sohbet", "Ses"):
            self.assertEqual(channels[name]["parent_id"], channels["Genel"]["id"])
        expected_overwrites = [
            {"id": TARGET, "type": 0, "allow": "0", "deny": "1024"},
            {"id": roles["Ekip"]["id"], "type": 0, "allow": "1024", "deny": "0"}]
        self.assertEqual(channels["sohbet"]["permission_overwrites"], expected_overwrites)
        self.assertEqual(channels["Genel"]["permission_overwrites"], expected_overwrites)
        self.assertNotIn("topic", channels["sohbet"])
        self.assertNotIn("rate_limit_per_user", channels["sohbet"])
        self.assertNotIn("bitrate", channels["Ses"])
        self.assertEqual(channels["sohbet"]["position"], 1)
        self.assertEqual(channels["Genel"]["position"], 2)
        deletes = [path for method, path, _ in self.api.writes if method == "DELETE"]
        self.assertEqual(deletes, [f"/channels/{OLD_CHANNEL}", f"/channels/{OLD_CATEGORY}", f"/guilds/{TARGET}/roles/{TARGET_ROLE}"])

    def test_pre_cancelled_operation_leaves_destination_unchanged(self):
        plan = self.plan()
        original = copy.deepcopy(self.api.states[TARGET])
        self.api.cancel.set()
        with self.assertRaises(Cancelled):
            execute(self.api, plan, self.directory)
        self.assert_no_writes()
        self.assertEqual(self.api.states[TARGET], original)

    def test_cancellation_after_first_delete_stops_all_further_writes(self):
        plan = self.plan()
        self.api.cancel_after_writes = 1
        with self.assertRaises(Cancelled):
            execute(self.api, plan, self.directory)
        self.assertEqual(len(self.api.writes), 1)
        self.assertTrue(list(self.directory.glob("*.json")))

    def test_mutation_error_stops_and_preserves_partial_result_and_backup(self):
        plan = self.plan()
        self.api.fail_write = lambda method, path, data: method == "POST" and path.endswith("/roles")
        with self.assertRaises(ApiError):
            execute(self.api, plan, self.directory)
        self.assertEqual([method for method, _, _ in self.api.writes], ["DELETE", "DELETE", "DELETE"])
        self.assertEqual(self.api.states[TARGET]["channels"], [])
        self.assertTrue(list(self.directory.glob("*.json")))

    def test_ignored_channel_ordering_is_not_reported_as_success(self):
        extra = copy.deepcopy(self.api.states[SOURCE]["channels"][0])
        extra.update(id="111111111111111124", name="ikinci-sohbet", position=2)
        self.api.states[SOURCE]["channels"].append(extra)
        plan = self.plan()
        self.api.ignore_channel_positions = True
        with self.assertRaises(CopyError):
            execute(self.api, plan, self.directory)

    def test_required_community_channels_are_logged_and_skipped_without_reassigning(self):
        self.api.states[TARGET]["guild"].update(features=["COMMUNITY"], rules_channel_id=OLD_CHANNEL,
                                               public_updates_channel_id=OLD_CHANNEL)
        original_guild = copy.deepcopy(self.api.states[TARGET]["guild"])
        messages = []
        result = execute(self.api, self.plan(), self.directory, log=messages.append)
        self.assertEqual(self.api.states[TARGET]["guild"], original_guild)
        self.assertTrue(any(c["name"] == "sohbet" for c in self.api.states[TARGET]["channels"]))
        self.assertEqual(result["remaining_channels"], 1)
        self.assertTrue(any(m.startswith("SİLİNEMEDİ") and OLD_CHANNEL in m for m in messages))
        self.assertFalse(any(method == "PATCH" and path == f"/guilds/{TARGET}" for method, path, _ in self.api.writes))

    def test_remaining_channels_at_discord_limit_stop_creation(self):
        self.api.states[TARGET]["guild"].update(features=["COMMUNITY"], rules_channel_id=OLD_CHANNEL)
        template = self.api.states[SOURCE]["channels"][0]
        self.api.states[SOURCE]["channels"] = [
            {**copy.deepcopy(template), "id": str(700000000000000000 + index), "name": f"kanal-{index}",
             "parent_id": None, "permission_overwrites": [], "position": index}
            for index in range(500)]
        with self.assertRaises(CopyError):
            execute(self.api, self.plan(), self.directory)
        self.assertFalse(any(method == "POST" for method, _, _ in self.api.writes))



class Response:
    def __init__(self, payload=None, headers=None):
        self.payload = json.dumps(payload).encode() if payload is not None else b""
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return self.payload[:limit]


class Opener:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if not self.results:
            raise AssertionError("Unexpected extra HTTP request")
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.logs = []
        self.waits = []
        self.api = DiscordAPI("synthetic-test-secret", log=self.logs.append)
        self.api.wait = self.waits.append

    def test_user_authorization_is_raw_and_only_sent_to_discord(self):
        self.api.opener = Opener(Response({"id": OWNER}))
        self.assertEqual(self.api.request("GET", "/users/@me"), {"id": OWNER})
        request, timeout = self.api.opener.calls[0]
        self.assertEqual(request.get_header("Authorization"), "synthetic-test-secret")
        self.assertEqual(request.full_url, "https://discord.com/api/v10/users/@me")
        self.assertEqual(timeout, 30)
        with self.assertRaises(CopyError):
            self.api.request("GET", "https://example.invalid/")
        self.assertEqual(len(self.api.opener.calls), 1)

    def test_redirect_handler_rejects_cross_origin_and_same_origin_redirects(self):
        handler = NoRedirect()
        self.assertTrue(any(isinstance(item, NoRedirect) for item in self.api.opener.handlers))
        for destination in ("https://example.invalid/steal", "https://discord.com/login"):
            for status in (301, 302, 303, 307, 308):
                with self.subTest(destination=destination, status=status):
                    self.assertIsNone(handler.redirect_request(None, None, status, "redirect", {}, destination))

    def test_rate_limit_429_is_honored_before_retry(self):
        error = urllib.error.HTTPError("https://discord.com/api/v10/users/@me", 429, "limited", {},
                                       io.BytesIO(json.dumps({"retry_after": 2.5}).encode()))
        self.api.opener = Opener(error, Response({"id": OWNER}))
        self.assertEqual(self.api.request("GET", "/users/@me"), {"id": OWNER})
        self.assertEqual(len(self.api.opener.calls), 2)
        self.assertIn(2.6, self.waits)
        self.assertEqual(len(self.logs), 1)

    def test_rate_limit_reset_header_defers_next_request(self):
        self.api.opener = Opener(Response({}, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset-After": "9"}), Response({}))
        with patch("copier.time.monotonic", return_value=100):
            self.api.request("GET", "/users/@me")
            self.api.request("GET", "/users/@me")
        self.assertEqual(self.waits, [0, 9])

    def test_ambiguous_mutation_timeout_is_never_retried(self):
        self.api.opener = Opener(TimeoutError("synthetic-test-secret"), Response({"id": "should-not-exist"}))
        with self.assertRaises(CopyError) as raised:
            self.api.request("POST", f"/guilds/{TARGET}/channels", {"name": "sohbet", "type": 0})
        self.assertEqual(len(self.api.opener.calls), 1)
        self.assertNotIn("synthetic-test-secret", str(raised.exception))
        self.assertEqual(self.logs, [])

    def test_error_body_and_credential_are_excluded_from_messages_and_logs(self):
        error = urllib.error.HTTPError("https://discord.com/api/v10/users/@me", 403, "synthetic-test-secret", {},
                                       io.BytesIO(json.dumps({"code": 50013, "message": "synthetic-test-secret PRIVATE-API-DETAIL"}).encode()))
        self.api.opener = Opener(error)
        with self.assertRaises(ApiError) as raised:
            self.api.request("GET", "/users/@me")
        output = str(raised.exception) + "\n".join(self.logs)
        self.assertIn("403", output)
        self.assertIn("50013", output)
        self.assertNotIn("synthetic-test-secret", output)
        self.assertNotIn("PRIVATE-API-DETAIL", output)
        self.assertEqual(len(self.api.opener.calls), 1)


if __name__ == "__main__":
    unittest.main()
