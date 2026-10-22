import ctypes
import json
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from copier import CopyError, DiscordAPI, execute, preview
from modern_ui import COLORS, ModernWindow


BASE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SunucuKopyalayici"


class App(ModernWindow):
    def __init__(self, demo=False):
        super().__init__()
        self.demo = demo
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.api = self.plan = None
        self.busy = False
        self.mutating = False
        self.token, self.source, self.target = [tk.StringVar() for _ in range(3)]
        self.status = tk.StringVar(value="Hazır · Önizleme hiçbir şeyi değiştirmez")
        self.build_ui(demo)
        for var in (self.token, self.source, self.target):
            var.trace_add("write", self.invalidate)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100, self.poll)
        self.token_entry.focus_set()

    def set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")

    def append_log(self, text, error=False):
        self.log_view.configure(state="normal")
        self.log_view.insert("end", text + "\n", ("error",) if error or text.startswith("SİLİNEMEDİ |") else ())
        self.log_view.see("end")
        self.log_view.configure(state="disabled")

    def invalidate(self, *_):
        self.plan = None
        self.refresh_copy()
        if not self.busy and not getattr(self, "_clearing_token", False):
            self.show_stage(0)
            for metric in self.metrics:
                metric.configure(text="—")
            self.preview_caption.configure(text="Sunucuları yeniden incele.")
            self.set_text(self.summary, "Bağlantı bilgileri değişti. Güncel yapıyı görmek için sunucuları yeniden incele.")

    def refresh_copy(self, *_):
        enabled = self.plan is not None and not self.busy
        self.copy_button.configure(state="normal" if enabled else "disabled", fg_color=COLORS["danger"] if enabled else "#3c2433")

    def work(self, function, kind):
        self.busy = True
        self.preview_button.configure(state="disabled")
        self.copy_button.configure(state="disabled", fg_color="#3c2433")
        self.stop_button.configure(state="normal")
        self.cancel.clear()
        self.bar.stop()
        self.bar.configure(mode="determinate")
        self.animate_progress(0)
        self.awaiting_progress = True
        self.percent.configure(text="—")
        self.bar.configure(mode="indeterminate")
        self.bar.start()
        self.show_stage(0 if kind == "preview" else 2, "İnceleniyor" if kind == "preview" else "Aktarılıyor")
        self.status.set("Sunucular inceleniyor…" if kind == "preview" else "Kopyalanıyor · Lütfen pencereyi açık tut")
        def worker():
            try:
                result = function()
                self.events.put((kind, result))
            except CopyError as exc:
                self.events.put(("error", str(exc)))
            except Exception:
                self.events.put(("error", "Beklenmeyen hata nedeniyle işlem durdu. Kısmi değişiklik olabilir; yeniden önizleyin. Token hiçbir hata kaydına yazılmadı."))
        threading.Thread(target=worker, daemon=True).start()

    def inspect(self):
        if self.busy or self.demo:
            return
        self.plan = None
        try:
            self.api = DiscordAPI(self.token.get(), self.cancel, lambda text: self.events.put(("log", text)))
        except CopyError as exc:
            messagebox.showerror("Kontrol edilemedi", str(exc), parent=self)
            return
        source, target = self.source.get(), self.target.get()
        self.inspected_inputs = (self.token.get(), source, target)
        self.work(lambda: preview(self.api, source, target), "preview")

    def copy(self):
        if self.busy or self.plan is None or self.demo:
            return
        plan = self.plan
        self.mutating = True
        self.work(lambda: execute(self.api, plan, BASE / "backups", lambda text: self.events.put(("log", text)), lambda done, total: self.events.put(("progress", (done, total)))), "done")

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.append_log(value)
                    continue
                if kind == "progress":
                    self.awaiting_progress = False
                    self.bar.stop()
                    self.bar.configure(mode="determinate")
                    self.animate_progress(value[0] / max(1, value[1]))
                    continue
                self.busy = self.mutating = False
                self.bar.stop()
                self.bar.configure(mode="determinate")
                self.bar.set(self.progress_target)
                self.preview_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                if kind == "preview":
                    if self.inspected_inputs != (self.token.get(), self.source.get(), self.target.get()):
                        self.status.set("Alanlar değişti; tekrar incele.")
                        self.show_stage(0)
                        continue
                    self.plan = value
                    self.update_metrics(value)
                    self.show_stage(1, "İncelendi")
                    s, t = value["source"], value["target"]
                    categories = sum(c["type"] == 4 for c in s["channels"])
                    deleted_roles = sum(r["id"] != value["target_id"] and not r.get("managed") for r in t["roles"])
                    text = f"Kaynak: {s['guild']['name']} · {len(s['roles']) - 1} rol, {categories} kategori, {len(s['channels']) - categories} kanal\nHedef: {t['guild']['name']} · {deleted_roles} rol ve {len(t['channels'])} kanal için silme denenecek\nYalnızca rol bazlı kanal izinleri aktarılır. Kişisel izinler ve sunucu ayarları aktarılmaz."
                    if value["warnings"]:
                        text += "\n" + "\n".join("• " + warning for warning in value["warnings"])
                    self.set_text(self.summary, text)
                    self.status.set("İnceleme tamamlandı · Aktarım düğmesiyle başlayabilirsin")
                    self.append_log("Önizleme hazır. Henüz hiçbir şey değiştirilmedi.")
                elif kind == "done":
                    self.plan = None
                    self.animate_progress(1)
                    self.show_stage(2, "Tamamlandı")
                    self.status.set("Tamamlandı · Son yapı ve izin kontrolü geçti")
                    self.append_log(f"Kopyalama tamamlandı. Yapı yedeği: {value['backup']}")
                    self.clear_token()
                    if value["deletion_failures"]:
                        self.status.set("Aktarım tamamlandı · Silinemeyen öğeler var; kırmızı satırları incele")
                        self.append_log(f"Uyarı: {value['deletion_failures']} öğenin silme adımı atlandı. Hedefte {value['remaining_roles']} eski rol ve {value['remaining_channels']} eski kanal kaldı.", error=True)
                        self.show_stage(2, "Uyarılı bitti")
                    else:
                        self.show_stage(2, "Tamamlandı")
                else:
                    self.plan = None
                    self.show_stage(0, "Durduruldu")
                    self.status.set("İşlem durdu · Yeniden incelemeden devam edilmez")
                    self.append_log(value, error=True)
                    messagebox.showerror("İşlem durdu", value, parent=self)
                    self.show_stage(0, "Durduruldu")
                self.refresh_copy()
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def clear_token(self):
        self._clearing_token = True
        self.token.set("")
        self._clearing_token = False
        self.api = None
        self.inspected_inputs = None
        self.show_token.set(False)
        self.token_entry.configure(show="•")

    def stop(self):
        self.cancel.set()
        self.stop_button.configure(state="disabled")
        self.status.set("Durdurma istendi · Devam eden isteğin bitmesi bekleniyor")

    def open_backups(self):
        try:
            (BASE / "backups").mkdir(parents=True, exist_ok=True)
            os.startfile(BASE / "backups")
        except OSError:
            messagebox.showerror("Klasör açılamadı", str(BASE / "backups"), parent=self)

    def close(self):
        if self.busy:
            self.stop()
            messagebox.showinfo("Durduruluyor", "Durdurma istendi. Tamamlanan silme/oluşturma işlemleri geri alınmaz. İstek bittikten sonra pencereyi kapatabilirsin.", parent=self)
            return
        self.clear_token()
        self.motion.finish()
        self.destroy()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    if "--self-check" in sys.argv:
        app = App(demo=True)
        app.update()
        assert app.copy_button.cget("state") == "disabled"
        assert app.token_entry.cget("show") == "•"
        assert app.token_entry.winfo_width() > 100
        assert app.copy_button.winfo_width() >= 170
        app.animate_progress(.6)
        assert "progress" in app.motion.jobs
        assert not hasattr(app, "confirm_entry")
        assert not hasattr(app, "motion_switch")
        assert (app.logo_image.width(), app.logo_image.height()) == (44, 44)
        assert app.log_view.cget("height") >= 250
        app.motion.finish()
        app.destroy()
        if "--report" in sys.argv:
            path = Path(sys.argv[sys.argv.index("--report") + 1])
            path.write_text(json.dumps({"gui": "ok", "token_masked": True, "copy_disabled": True, "animations": "enabled", "extra_confirmation": "removed", "logo": "ok", "large_log": True, "network": "not used"}), encoding="utf-8")
        return
    App(demo="--demo" in sys.argv).mainloop()


if __name__ == "__main__":
    main()
