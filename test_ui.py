import time
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import App
from modern_ui import COLORS
from copier import preview
from test_copier import MemoryAPI, SOURCE, TARGET


class ModernUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App(demo=True)
        cls.app.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.motion.finish()
        cls.app.destroy()

    def setUp(self):
        self.app.motion.finish()
        self.app.busy = False
        self.app.plan = None
        self.app.demo = True

    def test_preview_unlocks_copy_without_second_confirmation_and_edits_relock(self):
        app = self.app
        self.assertFalse(hasattr(app, "confirm_entry"))
        self.assertFalse(hasattr(app, "motion_switch"))
        app.plan = {"target_id": "222222222222222222"}
        app.refresh_copy()
        self.assertEqual(app.copy_button.cget("state"), "normal")
        app.source.set("333333333333333333")
        self.assertIsNone(app.plan)
        self.assertEqual(app.copy_button.cget("state"), "disabled")

    def test_animations_always_run_and_latest_progress_wins(self):
        app = self.app
        app.animate_progress(.2)
        app.animate_progress(.85)
        self.assertIn("progress", app.motion.jobs)
        self.assertFalse(hasattr(app, "reduced_motion"))
        until = time.monotonic() + .3
        while time.monotonic() < until:
            app.update()
            time.sleep(.01)
        self.assertAlmostEqual(app.bar.get(), .85)
        self.assertEqual(app.percent.cget("text"), "%85")

    def test_copy_starts_worker_directly_without_confirmation_dialog(self):
        app = self.app
        app.demo = False
        app.plan = {"target_id": "222222222222222222"}
        with patch("app.messagebox.askyesno", side_effect=AssertionError("No second confirmation")), patch.object(app, "work") as worker:
            app.copy()
        worker.assert_called_once()

    def test_failed_deletion_log_line_is_red_and_normal_line_is_not(self):
        app = self.app
        app.set_text(app.log_view, "")
        app.append_log("SİLİNEMEDİ | Rol: Test (123): HTTP403")
        app.append_log("Kanal oluşturuldu: sohbet")
        self.assertIn("error", app.log_view.tag_names("1.0"))
        self.assertNotIn("error", app.log_view.tag_names("2.0"))
        self.assertEqual(app.log_view.tag_cget("error", "foreground"), "#ff6b7d")

    def test_keyboard_button_activation_respects_disabled_state(self):
        app = self.app
        hits = []
        button = app.button(app, "Keyboard test", lambda: hits.append(True))
        button.place(x=230, y=100)
        app.update()
        tk.Misc.focus_force(button)
        app.update()
        button.event_generate("<Return>")
        app.update()
        self.assertEqual(hits, [True])
        button.configure(state="disabled")
        button.event_generate("<space>")
        app.update()
        self.assertEqual(hits, [True])
        button.destroy()

    def test_focus_scrolls_transfer_button_into_view_at_small_window(self):
        app = self.app
        app.geometry("1000x700")
        app.update()
        app.content._parent_canvas.yview_moveto(0)
        app.update()
        app.ensure_focus_visible(SimpleNamespace(widget=app.copy_button))
        app.update()
        canvas = app.content._parent_canvas
        self.assertGreaterEqual(app.copy_button.winfo_rooty(), canvas.winfo_rooty())
        self.assertLessEqual(app.copy_button.winfo_rooty() + app.copy_button.winfo_height(), canvas.winfo_rooty() + canvas.winfo_height())
        app.geometry("1280x900")
        app.update()

    def test_token_mask_and_success_preview_survive_secret_clear(self):
        app = self.app
        app.token.set("synthetic-only")
        app.set_text(app.summary, "Result details")
        app.clear_token()
        self.assertEqual(app.token.get(), "")
        self.assertEqual(app.token_entry.cget("show"), "•")
        self.assertIn("Result details", app.summary.get("1.0", "end"))

    def test_error_and_cancellation_preserve_token_and_server_fields(self):
        app = self.app
        for message in ("Geçici hata", "Durduruldu. Tamamlanan değişiklikler geri alınmadı."):
            with self.subTest(message=message):
                app.token.set("synthetic-retained-token")
                app.source.set(SOURCE)
                app.target.set(TARGET)
                original_api = object()
                app.api = original_api
                app.events.put(("error", message))
                with patch("app.messagebox.showerror"):
                    app.poll()
                self.assertEqual(app.token.get(), "synthetic-retained-token")
                self.assertEqual((app.source.get(), app.target.get()), (SOURCE, TARGET))
                self.assertIs(app.api, original_api)
                self.assertEqual(app.copy_button.cget("state"), "disabled")

    def test_preview_preserves_token_and_server_fields(self):
        app = self.app
        app.token.set("synthetic-preview-token")
        app.source.set(SOURCE)
        app.target.set(TARGET)
        app.inspected_inputs = (app.token.get(), SOURCE, TARGET)
        app.events.put(("preview", preview(MemoryAPI(), SOURCE, TARGET)))
        app.poll()
        self.assertEqual(app.token.get(), "synthetic-preview-token")
        self.assertEqual((app.source.get(), app.target.get()), (SOURCE, TARGET))
        self.assertEqual(app.copy_button.cget("state"), "normal")

    def test_completed_copy_clears_token_including_completion_with_warnings(self):
        app = self.app
        for failures in (0, 1):
            with self.subTest(failures=failures):
                app.token.set("synthetic-completion-token")
                app.events.put(("done", {"backup": "synthetic-backup.json", "deletion_failures": failures,
                                         "remaining_roles": failures, "remaining_channels": 0}))
                app.poll()
                self.assertEqual(app.token.get(), "")
                self.assertIsNone(app.api)
                self.assertEqual(app.token_entry.cget("show"), "•")

    def test_normal_text_contrast(self):
        def luminance(h):
            values = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
            return sum(a * b for a, b in zip(values, (.2126, .7152, .0722)))
        for fg, bg in (("text", "panel"), ("muted", "panel"), ("text", "primary"), ("text", "primary_hover"), ("text", "danger")):
            a, b = sorted((luminance(COLORS[fg]), luminance(COLORS[bg])))
            self.assertGreaterEqual((b + .05) / (a + .05), 4.5, (fg, bg))

    def test_release_logo_large_log_and_removed_sidebar_copy(self):
        app = self.app
        self.assertEqual((app.logo_image.width(), app.logo_image.height()), (44, 44))
        self.assertTrue(app.logo_label.cget("image"))
        self.assertGreaterEqual(app.log_view.cget("height"), 250)
        pending = [app]
        texts = []
        while pending:
            widget = pending.pop()
            pending.extend(widget.winfo_children())
            try:
                texts.append(str(widget.cget("text")))
            except (tk.TclError, ValueError):
                pass
        self.assertNotIn("YALNIZCA SUNUCU YAPISI", texts)
        self.assertNotIn("Roller · Kategoriler\nKanallar ve izinler", texts)


if __name__ == "__main__":
    unittest.main()
