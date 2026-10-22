import hashlib
import json
import math
import os
import re
import socket
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


class CopyError(Exception):
    pass


class Cancelled(CopyError):
    pass


class ApiError(CopyError):
    def __init__(self, status, code=None):
        self.status = status
        hints = {401: "Token geçersiz veya süresi dolmuş.", 403: "Discord işlemi reddetti; yetkileri veya hesap doğrulamasını kontrol edin.",
                 404: "Sunucu, kanal veya üye bulunamadı.", 429: "Discord istek sınırı aşıldı."}
        super().__init__(f"HTTP {status}" + (f" / Discord {code}" if isinstance(code, int) else "") + ": " +
                         hints.get(status, "Discord işlemi tamamlamadı. Kısmi değişiklik olabilir; yeniden önizleyin."))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class DiscordAPI:
    def __init__(self, token, cancel=None, log=lambda text: None):
        token = token.strip()
        if not token or any(c.isspace() for c in token) or token.lower().startswith(("bot ", "bearer ")):
            raise CopyError("Yalnızca kendi hesabınızın kullanıcı token’ini girin.")
        if not token.isascii():
            raise CopyError("Token geçerli ASCII karakterlerinden oluşmalıdır.")
        self._token = token
        self.cancel = cancel or threading.Event()
        self.log = log
        self.opener = urllib.request.build_opener(NoRedirect)
        self.next_request = 0

    def wait(self, seconds):
        if not math.isfinite(seconds) or not 0 <= seconds <= 600:
            raise CopyError("Discord bekleme süresi geçersiz veya 10 dakikadan uzun; işlem durdu.")
        if self.cancel.wait(seconds):
            raise Cancelled("Durduruldu. Tamamlanan değişiklikler geri alınmadı.")

    def request(self, method, path, data=None):
        if not path.startswith(("/guilds/", "/channels/", "/users/@me")) or ".." in path or "?" in path:
            raise CopyError("Geçersiz API yolu.")
        for attempt in range(8):
            self.wait(max(0, self.next_request - time.monotonic()))
            body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request("https://discord.com/api/v10" + path, data=body, method=method,
                                         headers={"Authorization": self._token, "Content-Type": "application/json",
                                                  "User-Agent": "ServerCopier/1.0 (local desktop utility)"})
            try:
                with self.opener.open(req, timeout=30) as response:
                    raw = response.read(8_000_001)
                    if len(raw) > 8_000_000:
                        raise CopyError("API yanıtı boyut sınırını aştı; işlem durdu.")
                    result = json.loads(raw) if raw else None
                    delay = 0.25
                    if response.headers.get("X-RateLimit-Remaining") == "0":
                        delay = max(delay, float(response.headers.get("X-RateLimit-Reset-After", "1")))
                    if not math.isfinite(delay) or delay > 600:
                        raise CopyError("Discord bekleme sınırı aşıldı.")
                    self.next_request = time.monotonic() + delay
                    return result
            except urllib.error.HTTPError as exc:
                try:
                    error = json.loads(exc.read(65536))
                except (ValueError, UnicodeError):
                    error = {}
                finally:
                    exc.close()
                self.next_request = time.monotonic() + 0.25
                if not isinstance(error, dict):
                    error = {}
                if exc.code == 429 and attempt < 7:
                    try:
                        delay = float(error.get("retry_after", "1"))
                    except (TypeError, ValueError):
                        raise CopyError("Discord geçersiz bekleme süresi döndürdü.") from None
                    self.log(f"Discord istek sınırı: {delay:.1f} saniye bekleniyor.")
                    self.wait(delay + 0.1)
                    continue
                if method == "GET" and exc.code >= 500 and attempt < 2:
                    self.wait(2 ** attempt)
                    continue
                raise ApiError(exc.code, error.get("code")) from None
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError):
                raise CopyError("Bağlantı kesildi veya zaman aşımı oluştu. Son isteğin sonucu belirsiz olabilir; tekrar önizleyin.") from None
            except (ValueError, UnicodeError):
                raise CopyError("Discord yanıtı okunamadı. Son isteğin sonucu belirsiz olabilir; tekrar önizleyin.") from None


def guild_id(value):
    value = value.strip()
    if not re.fullmatch(r"[0-9]{17,20}", value) or int(value) >= 2 ** 64:
        raise CopyError("Sunucu ID’si 17–20 rakam olmalıdır. Discord > Gelişmiş > Geliştirici Modu’nu açıp sunucu ID’sini kopyalayın.")
    return value


def snapshot(api, gid):
    return {"guild": api.request("GET", f"/guilds/{gid}"),
            "roles": api.request("GET", f"/guilds/{gid}/roles"),
            "channels": api.request("GET", f"/guilds/{gid}/channels")}


def fingerprint(state):
    guild = state["guild"]
    roles = [{"id": r["id"], "position": r.get("position", 0), "managed": bool(r.get("managed")),
              **role_payload(r)} for r in state["roles"]]
    channels = []
    for channel in state["channels"]:
        overwrites = [{"id": o["id"], "allow": str(int(o.get("allow") or 0)), "deny": str(int(o.get("deny") or 0))}
                      for o in channel.get("permission_overwrites", []) if o["type"] == 0]
        channels.append({"id": channel["id"], "name": channel["name"], "type": channel["type"],
                         "parent_id": channel.get("parent_id"), "position": channel.get("position", 0),
                         "permission_overwrites": sorted(overwrites, key=lambda o: o["id"])})
    relevant = {"guild": {k: guild.get(k) for k in ("id", "name", "owner_id")},
                "roles": sorted(roles, key=lambda r: r["id"]),
                "channels": sorted(channels, key=lambda c: c["id"])}
    return hashlib.sha256(json.dumps(relevant, sort_keys=True).encode()).hexdigest()


def role_payload(role):
    colors = role.get("colors") or {"primary_color": role.get("color", 0)}
    return {"name": role["name"], "colors": {"primary_color": colors.get("primary_color", 0)}}


def channel_payload(channel, roles, parents):
    kinds = {0: 0, 2: 2, 4: 4, 5: 0, 13: 2, 15: 15, 16: 0}
    if channel["type"] not in kinds:
        raise CopyError(f"Desteklenmeyen kanal türü: {channel['type']}. Hedefte hiçbir şey silinmedi.")
    result = {"name": channel["name"], "type": kinds[channel["type"]]}
    overwrites = []
    for entry in channel.get("permission_overwrites", []):
        if entry["type"] != 0:
            continue
        mapped = roles.get(entry["id"])
        if mapped is None:
            raise CopyError("Bir kanal izninin rolü kaynak rol listesinde yok. İşlem durduruldu.")
        overwrites.append({"id": mapped, "type": 0, "allow": str(entry.get("allow", "0")), "deny": str(entry.get("deny", "0"))})
    result["permission_overwrites"] = overwrites
    if channel.get("parent_id"):
        if channel["parent_id"] not in parents:
            raise CopyError("Bir kanalın üst kategorisi bulunamadı.")
        result["parent_id"] = parents[channel["parent_id"]]
    return result


def preview(api, source_id, target_id):
    source_id, target_id = guild_id(source_id), guild_id(target_id)
    if source_id == target_id:
        raise CopyError("Kaynak ve hedef aynı sunucu olamaz.")
    user = api.request("GET", "/users/@me")
    if user.get("bot"):
        raise CopyError("Bot token’i desteklenmiyor; kullanıcı token’i gerekiyor.")
    source, target = snapshot(api, source_id), snapshot(api, target_id)
    if target["guild"].get("owner_id") != user["id"]:
        member = api.request("GET", f"/guilds/{target_id}/members/{user['id']}")
        member_roles = set(member.get("roles", [])) | {target_id}
        if not any(int(r["permissions"]) & 8 for r in target["roles"] if r["id"] in member_roles):
            raise CopyError("Hedef sunucuda Yönetici (Administrator) yetkisi gerekiyor. Bu hedefte işlem yapılmadı.")
    if not source["roles"] or not any(r["id"] == source_id for r in source["roles"]):
        raise CopyError("Kaynak @everyone rolü okunamadı.")
    retained = [r for r in target["roles"] if r.get("managed")]
    if len(source["roles"]) + len(retained) > 250 or len(source["channels"]) > 500:
        raise CopyError("Hedefin Discord rol veya kanal sınırı aşılacak.")
    warnings = set()
    if retained:
        warnings.add(f"Hedefte Discord tarafından yönetilen {len(retained)} entegrasyon rolü korunacak; bunlar silinemez.")
    if any(r.get("managed") for r in source["roles"]):
        warnings.add("Kaynak entegrasyon rolleri normal rol olarak oluşturulur; bot bağlantıları aktarılmaz.")
    if any(o["type"] != 0 for c in source["channels"] for o in c.get("permission_overwrites", [])):
        warnings.add("Kişiye özel kanal izinleri atlanır; yalnızca rollere verilen kanal izinleri aktarılır.")
    identity_roles = {r["id"]: r["id"] for r in source["roles"]}
    identity_parents = {c["id"]: c["id"] for c in source["channels"] if c["type"] == 4}
    for channel in source["channels"]:
        channel_payload(channel, identity_roles, identity_parents)
    return {"source_id": source_id, "target_id": target_id, "source": source, "target": target,
            "user_id": user["id"], "warnings": sorted(warnings)}


def backup(plan, directory):
    directory = Path(directory)
    path = directory / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + plan["target_id"] + ".json")
    content = {"format": 1, "created_at": datetime.now().astimezone().isoformat(),
               "notice": "Yalnızca yapı kaydıdır. Mesajları/üyeleri içermez; otomatik geri yükleme değildir.",
               "source": plan["source"], "target_before": plan["target"]}
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as file:
            json.dump(content, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
    except OSError:
        raise CopyError("Yerel yapı yedeği yazılamadı; hedefte hiçbir şey silinmedi.") from None
    return path


def verify(api, plan, roles, channels, expected_channels, failed_deletions):
    final = snapshot(api, plan["target_id"])
    final_roles = {r["id"]: r for r in final["roles"]}
    final_channels = {c["id"]: c for c in final["channels"]}
    expected_role_ids = set(roles.values()) | {r["id"] for r in plan["target"]["roles"] if r.get("managed")}
    if (not expected_role_ids <= set(final_roles) or set(final_roles) - expected_role_ids - set(failed_deletions["roles"])
            or not set(channels.values()) <= set(final_channels)
            or set(final_channels) - set(channels.values()) - set(failed_deletions["channels"])):
        raise CopyError("Son kontrolde rol/kanal listesi beklenenden farklı. İşlem kısmen tamamlanmış olabilir.")
    ordered = sorted(plan["source"]["roles"], key=lambda r: (r.get("position", 0), int(r["id"])))
    for role in ordered:
        if role["id"] == plan["source_id"]:
            continue
        actual = final_roles[roles[role["id"]]]
        expected = role_payload(role)
        if actual["name"] != expected["name"]:
            raise CopyError("Son kontrolde rol adı uyuşmadı.")
        colors = actual.get("colors") or {"primary_color": actual.get("color", 0)}
        if colors.get("primary_color") != expected["colors"]["primary_color"]:
            raise CopyError("Son kontrolde rol rengi uyuşmadı.")
    actual_order = sorted(ordered, key=lambda r: (final_roles[roles[r["id"]]]["position"], int(roles[r["id"]])))
    if [r["id"] for r in actual_order] != [r["id"] for r in ordered]:
        raise CopyError("Son kontrolde rol sırası uyuşmadı. Hedefi Discord’da inceleyin.")
    def permissions(value):
        return sorted((str(o["id"]), o["type"], str(o.get("allow", "0")), str(o.get("deny", "0"))) for o in value)
    for original_id, expected in expected_channels.items():
        actual = final_channels[channels[original_id]]
        if any(actual.get(k) != expected.get(k) for k in ("name", "type", "parent_id")) or permissions(actual.get("permission_overwrites", [])) != permissions(expected["permission_overwrites"]):
            raise CopyError("Son kontrolde kanal yapısı veya izinleri uyuşmadı. Hedefi Discord’da inceleyin.")
    groups = {}
    for channel in plan["source"]["channels"]:
        bucket = 2 if channel["type"] in (2, 13) else 4 if channel["type"] == 4 else 0
        groups.setdefault((channel.get("parent_id"), bucket), []).append(channel)
    for group in groups.values():
        # Discord normalizes numeric positions; relative order is the user-visible invariant.
        before = sorted(group, key=lambda c: (c.get("position", 0), int(c["id"])))
        after = sorted(group, key=lambda c: (final_channels[channels[c["id"]]].get("position", 0), int(channels[c["id"]])))
        if [c["id"] for c in before] != [c["id"] for c in after]:
            raise CopyError("Son kontrolde kanal sırası uyuşmadı. Hedefi Discord’da inceleyin.")
    return final


def execute(api, plan, directory, log=lambda text: None, progress=lambda done, total: None):
    fresh = preview(api, plan["source_id"], plan["target_id"])
    if fresh["user_id"] != plan["user_id"]:
        raise CopyError("Hesap önizlemeden sonra değişti. Yeniden önizleyin; hiçbir şey silinmedi.")
    for side, label in (("source", "Kaynak"), ("target", "Hedef")):
        if fingerprint(fresh[side]) != fingerprint(plan[side]):
            raise CopyError(f"{label} sunucunun rol/kanal yapısı önizlemeden sonra değişti. Yeniden önizleyin; hiçbir şey silinmedi.")
    path = backup(fresh, directory)
    log(f"Yapı yedeği kaydedildi: {path}")
    source, target = fresh["source"], fresh["target"]
    sid, tid = fresh["source_id"], fresh["target_id"]
    deletable_roles = [r for r in target["roles"] if r["id"] != tid and not r.get("managed")]
    managed_roles = [r for r in target["roles"] if r.get("managed")]
    failed_deletions = {"roles": [], "channels": []}
    total = len(target["channels"]) + len(deletable_roles) + len(managed_roles) + len(source["roles"]) - 1 + len(source["channels"]) + 3
    done = 0
    def step(text):
        nonlocal done
        done += 1
        log(text)
        progress(done, total)
    def delete(kind, item, route):
        try:
            api.request("DELETE", route)
        except Cancelled:
            raise
        except CopyError as exc:
            failed_deletions[kind].append(item["id"])
            step(f"SİLİNEMEDİ | {'Rol' if kind == 'roles' else 'Kanal'}: {item['name']} ({item['id']}): {exc}")
        else:
            step(f"{'Rol' if kind == 'roles' else 'Kanal'} silindi: {item['name']}")

    for channel in sorted(target["channels"], key=lambda c: c["type"] == 4):
        delete("channels", channel, f"/channels/{channel['id']}")
    for role in sorted(deletable_roles, key=lambda r: r.get("position", 0), reverse=True):
        delete("roles", role, f"/guilds/{tid}/roles/{role['id']}")
    for role in managed_roles:
        failed_deletions["roles"].append(role["id"])
        step(f"SİLİNEMEDİ | Rol: {role['name']} ({role['id']}): Discord tarafından yönetilen rol; devam ediliyor.")
    remaining = snapshot(api, tid)
    if len(remaining["roles"]) + len(source["roles"]) - 1 > 250 or len(remaining["channels"]) + len(source["channels"]) > 500:
        raise CopyError("Silinemeyen öğeler nedeniyle Discord rol/kanal sınırı aşılacak. Kopyalama için hedefte yer açın.")
    role_map = {sid: tid}
    ordered_roles = sorted((r for r in source["roles"] if r["id"] != sid), key=lambda r: (r.get("position", 0), int(r["id"])))
    for role in ordered_roles:
        result = api.request("POST", f"/guilds/{tid}/roles", role_payload(role))
        role_map[role["id"]] = result["id"]
        step(f"Rol oluşturuldu: {role['name']}")
    if ordered_roles:
        api.request("PATCH", f"/guilds/{tid}/roles", [{"id": role_map[r["id"]], "position": i} for i, r in enumerate(ordered_roles, 1)])
    step("Rol sıralaması aktarıldı.")
    channel_map, expected_channels = {}, {}
    for channel in sorted(source["channels"], key=lambda c: (c["type"] != 4, c.get("position", 0), int(c["id"]))):
        payload = channel_payload(channel, role_map, channel_map)
        result = api.request("POST", f"/guilds/{tid}/channels", payload)
        channel_map[channel["id"]] = result["id"]
        expected_channels[channel["id"]] = payload
        step(f"Kanal oluşturuldu: {channel['name']}")
    if source["channels"]:
        api.request("PATCH", f"/guilds/{tid}/channels", [{"id": channel_map[c["id"]], "position": c.get("position", 0)} for c in source["channels"]])
    step("Kanal sıralaması aktarıldı.")
    final = verify(api, fresh, role_map, channel_map, expected_channels, failed_deletions)
    step("Son kontrol geçti: kopyalanan roller, kanallar ve izinler doğrulandı.")
    return {"backup": path, "deletion_failures": sum(len(items) for items in failed_deletions.values()),
            "remaining_roles": len({r["id"] for r in final["roles"]} & set(failed_deletions["roles"])),
            "remaining_channels": len({c["id"] for c in final["channels"]} & set(failed_deletions["channels"]))}
