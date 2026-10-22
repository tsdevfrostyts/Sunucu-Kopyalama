import time
import tkinter as tk
from pathlib import Path

import customtkinter as ctk


COLORS = {
    "bg": "#0c1019", "sidebar": "#111622", "panel": "#151c29", "input": "#0f1520",
    "border": "#364258", "text": "#f0f3fc", "muted": "#a8b5cd", "accent": "#7478ff",
    "primary": "#565bd0", "primary_hover": "#5c61d5", "subtle": "#252b4c", "success": "#88ddbc", "danger": "#b92c48",
    "danger_hover": "#cf3a58", "warning": "#f3c786", "focus": "#a7b4ff",
}


class Motion:
    def __init__(self, root):
        self.root = root
        self.jobs = {}

    def animate(self, key, start, end, setter, duration=180):
        if key in self.jobs:
            self.root.after_cancel(self.jobs.pop(key))
        began = time.monotonic()
        def tick():
            t = min(1, (time.monotonic() - began) * 1000 / duration)
            setter(start + (end - start) * (1 - (1 - t) ** 3))
            if t < 1:
                self.jobs[key] = self.root.after(16, tick)
            else:
                self.jobs.pop(key, None)
        tick()

    def finish(self):
        for job in tuple(self.jobs.values()):
            self.root.after_cancel(job)
        self.jobs.clear()


class ModernWindow(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
        super().__init__()
        self.asset_dir = Path(__file__).resolve().parent / "assets"
        self.iconbitmap(str(self.asset_dir / "app.ico"))
        self.title("Sunucu Kopyalayıcı")
        self.geometry(f"{min(1280, self.winfo_screenwidth() - 70)}x{min(900, self.winfo_screenheight() - 100)}")
        self.minsize(1000, 700)
        self.configure(fg_color=COLORS["bg"])
        self.motion = Motion(self)
        self.progress_target = 0
        self.active_stage = 0
        self.bind("<Escape>", lambda event: self.stop() if self.busy else None)

    def label(self, parent, text="", size=13, color="text", bold=False, **kwargs):
        return ctk.CTkLabel(parent, text=text, text_color=COLORS.get(color, color),
                            font=("Segoe UI", size, "bold" if bold else "normal"), anchor="w", **kwargs)

    def card(self, parent):
        return ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=18,
                            border_width=1, border_color="#293247")

    def button(self, parent, text, command, variant="secondary", **kwargs):
        base = COLORS["primary"] if variant == "primary" else COLORS["danger"] if variant == "danger" else "#263047"
        hover = COLORS["primary_hover"] if variant == "primary" else COLORS["danger_hover"] if variant == "danger" else "#37445f"
        button = ctk.CTkButton(parent, text=text, command=command, height=kwargs.pop("height", 44), corner_radius=10,
                               fg_color=("#3c2433" if variant == "danger" else "#263047") if kwargs.get("state") == "disabled" else base,
                               hover=False, text_color=COLORS["text"],
                               text_color_disabled="#a0abc0", font=("Segoe UI", 13, "bold"), **kwargs)
        tk.Frame.configure(button, takefocus=True)
        def paint(target):
            current = button.cget("fg_color")
            if not isinstance(current, str) or not current.startswith("#"):
                current = base
            a = tuple(int(current[i:i + 2], 16) for i in (1, 3, 5))
            b = tuple(int(target[i:i + 2], 16) for i in (1, 3, 5))
            self.motion.animate(str(button), 0, 1, lambda t: button.configure(fg_color="#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))), 130)
        button.bind("<Enter>", lambda event: paint(hover) if button.cget("state") == "normal" else None)
        button.bind("<Leave>", lambda event: paint(base) if button.cget("state") == "normal" else None)
        for sequence in ("<Return>", "<space>"):
            tk.Misc.bind(button, sequence, lambda event, b=button: b.invoke(), add="+")
        tk.Misc.bind(button, "<FocusIn>", lambda event: button.configure(border_width=2, border_color=COLORS["focus"]), add="+")
        tk.Misc.bind(button, "<FocusOut>", lambda event: button.configure(border_width=0), add="+")
        return button

    def entry(self, parent, variable, placeholder="", **kwargs):
        field = ctk.CTkEntry(parent, textvariable=variable, placeholder_text=placeholder,
                             height=44, corner_radius=10, fg_color=COLORS["input"],
                             border_color=COLORS["border"], border_width=1,
                             text_color=COLORS["text"], font=("Segoe UI", 14), **kwargs)
        field.bind("<FocusIn>", lambda event: field.configure(border_color=COLORS["focus"], border_width=2))
        field.bind("<FocusOut>", lambda event: field.configure(border_color=COLORS["border"], border_width=1))
        return field

    def build_ui(self, demo):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(self, width=210, fg_color=COLORS["sidebar"], corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(6, weight=1)
        logo = ctk.CTkFrame(sidebar, width=44, height=44, corner_radius=0, fg_color=COLORS["sidebar"])
        logo.grid(row=0, column=0, sticky="w", padx=24, pady=(30, 12))
        logo.grid_propagate(False)
        self.logo_image = tk.PhotoImage(file=str(self.asset_dir / "logo.png"))
        self.logo_label = tk.Label(logo, image=self.logo_image, bg=COLORS["sidebar"], borderwidth=0)
        self.logo_label.place(relx=.5, rely=.5, anchor="center")
        self.label(sidebar, "Sunucu\nKopyalayıcı", size=22, bold=True, justify="left").grid(row=1, column=0, sticky="w", padx=24)
        self.label(sidebar, "ÇALIŞMA AKIŞI", size=10, color="muted", bold=True).grid(row=2, column=0, sticky="w", padx=24, pady=(40, 15))
        self.steps = []
        for i, (title, description) in enumerate((("Bağlantı", "Hesap ve sunucular"), ("Önizleme", "Yapıyı kontrol et"), ("Aktarım", "Onayla ve kopyala"))):
            row = ctk.CTkFrame(sidebar, fg_color="transparent", corner_radius=12)
            row.grid(row=3 + i, column=0, sticky="ew", padx=14, pady=4)
            number = self.label(row, f"0{i + 1}", size=13, color="muted", bold=True, width=32)
            number.grid(row=0, column=0, rowspan=2, padx=(14, 8), pady=12)
            heading = self.label(row, title, size=14, bold=True)
            heading.grid(row=0, column=1, sticky="w", pady=(10, 0))
            self.label(row, description, size=11, color="muted").grid(row=1, column=1, sticky="w", pady=(0, 10))
            self.steps.append((row, number, heading))
        self.backup_button = self.button(sidebar, "Yapı yedeklerini aç", self.open_backups, width=170)
        self.backup_button.grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 16))

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=(28, 20), pady=(24, 16))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=(6, 12), pady=(0, 20))
        header.grid_columnconfigure(0, weight=1)
        self.label(header, "SUNUCU YÖNETİMİ", size=10, color="muted", bold=True).grid(row=0, column=0, sticky="w")
        self.label(header, "Yapıyı taşı. Baştan uğraşma.", size=28, bold=True).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.label(header, "İki sunucu arasında düzenli, adım adım aktarım.", color="muted").grid(row=2, column=0, sticky="w", pady=(2, 0))
        self.badge = ctk.CTkLabel(header, text="●  Hazır", height=30, width=104, corner_radius=15, fg_color="#1a2b29", text_color=COLORS["success"], font=("Segoe UI", 11, "bold"))
        self.badge.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(12, 0))

        self.content = ctk.CTkScrollableFrame(main, fg_color="transparent", corner_radius=0, scrollbar_button_color=COLORS["border"])
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=3, uniform="body")
        self.content.grid_columnconfigure(1, weight=2, uniform="body")
        connection = self.card(self.content)
        connection.grid(row=0, column=0, sticky="nsew", padx=(0, 16), pady=(0, 16))
        connection.grid_columnconfigure(0, weight=1)
        self.label(connection, "01  Bağlantıyı hazırla", size=17, bold=True).grid(sticky="w", padx=22, pady=(18, 0))
        self.label(connection, "Hesabını ve aktarım yönünü belirle.", color="muted", size=12).grid(sticky="w", padx=22, pady=(0, 14))
        self.label(connection, "Hesabının token’i", size=12, bold=True).grid(sticky="w", padx=22)
        self.token_entry = self.entry(connection, self.token, "Kullanıcı token’ini gir", show="•")
        self.token_entry.grid(sticky="ew", padx=22, pady=(5, 6))
        self.show_token = tk.BooleanVar()
        ctk.CTkCheckBox(connection, text="Token’i göster", variable=self.show_token, command=lambda: self.token_entry.configure(show="" if self.show_token.get() else "•"),
                       font=("Segoe UI", 11), text_color=COLORS["muted"], checkbox_width=17, checkbox_height=17,
                       corner_radius=4, border_width=1, fg_color=COLORS["accent"], border_color=COLORS["border"]).grid(sticky="w", padx=22, pady=(2, 16))
        servers = ctk.CTkFrame(connection, fg_color="transparent")
        servers.grid(sticky="ew", padx=22)
        servers.grid_columnconfigure((0, 1), weight=1)
        self.fields = [self.token_entry]
        for col, (title, var, placeholder) in enumerate((("Kaynak sunucu ID", self.source, "Kopyalanacak sunucu"), ("Hedef sunucu ID", self.target, "Yapının taşınacağı sunucu"))):
            self.label(servers, title, size=12, bold=True).grid(row=0, column=col, sticky="w", padx=(0 if col == 0 else 12, 0))
            field = self.entry(servers, var, placeholder)
            field.grid(row=1, column=col, sticky="ew", padx=(0 if col == 0 else 12, 0), pady=(5, 0))
            self.fields.append(field)
        self.label(connection, "Token dosyaya kaydedilmez. Hedefte yönetici yetkisi gerekir.", size=11, color="muted", wraplength=450).grid(sticky="w", padx=22, pady=(10, 14))
        self.preview_button = self.button(connection, "Sunucuları incele  →", self.inspect, "primary")
        self.preview_button.grid(sticky="ew", padx=22, pady=(0, 20))

        review = self.card(self.content)
        review.grid(row=0, column=1, sticky="nsew", pady=(0, 16))
        review.grid_columnconfigure(0, weight=1)
        self.label(review, "02  Aktarım önizlemesi", size=17, bold=True).grid(sticky="w", padx=22, pady=(18, 0))
        self.preview_caption = self.label(review, "Sunucuları inceledikten sonra doldurulur.", size=12, color="muted", wraplength=310)
        self.preview_caption.grid(sticky="w", padx=22, pady=(0, 16))
        metrics = ctk.CTkFrame(review, fg_color="transparent")
        metrics.grid(sticky="ew", padx=22, pady=(0, 10))
        metrics.grid_columnconfigure((0, 1, 2), weight=1, uniform="metric")
        self.metrics = []
        for i, name in enumerate(("ROL", "KATEGORİ", "KANAL")):
            tile = ctk.CTkFrame(metrics, fg_color=COLORS["input"], corner_radius=12)
            tile.grid(row=0, column=i, sticky="ew", padx=(0, 8 if i < 2 else 0))
            value = self.label(tile, "—", size=26, bold=True)
            value.pack(anchor="w", padx=14, pady=(9, 0))
            self.label(tile, name, size=9, color="muted", bold=True).pack(anchor="w", padx=14, pady=(0, 11))
            self.metrics.append(value)
        self.summary = ctk.CTkTextbox(review, height=160, fg_color="transparent", text_color=COLORS["muted"],
                                     font=("Segoe UI", 12), wrap="word", corner_radius=0, border_spacing=0,
                                     scrollbar_button_color=COLORS["border"], state="disabled")
        self.summary.grid(sticky="nsew", padx=22, pady=(0, 20))
        review.grid_rowconfigure(3, weight=1)
        self.set_text(self.summary, "Henüz bir sunucu incelenmedi.\n\nKaynak ve hedef bilgilerini girip ‘Sunucuları incele’ ile devam et. Bu adım hiçbir şeyi değiştirmez.")

        approval = self.card(self.content)
        approval.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        approval.grid_columnconfigure(0, weight=1)
        self.label(approval, "03  Aktarımı başlat", size=16, bold=True).grid(row=0, column=0, sticky="w", padx=22, pady=(16, 0))
        self.label(approval, "Hedefte rol ve kanalları silme denenir. Silinen kanalların mesajları kalıcı kaybolur.", size=12, color="#f7a6b4", wraplength=770).grid(row=1, column=0, columnspan=2, sticky="w", padx=22, pady=(0, 12))
        self.copy_button = self.button(approval, "Hedefi sil ve kopyala", self.copy, "danger", width=220, state="disabled")
        self.copy_button.grid(row=2, column=0, sticky="e", padx=22, pady=(0, 18))

        activity = self.card(self.content)
        activity.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        activity.grid_columnconfigure(0, weight=1)
        self.label(activity, "İşlem günlüğü", size=14, bold=True).grid(row=0, column=0, sticky="w", padx=22, pady=(15, 0))
        self.percent = self.label(activity, "%0", size=12, color="muted")
        self.percent.grid(row=0, column=1, sticky="e", padx=22, pady=(15, 0))
        self.bar = ctk.CTkProgressBar(activity, height=5, corner_radius=3, fg_color="#283149", progress_color=COLORS["accent"], mode="determinate")
        self.bar.set(0)
        self.bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=22, pady=(12, 8))
        self.status_label = self.label(activity, textvariable=self.status, color="muted", size=11, wraplength=680)
        self.status_label.grid(row=2, column=0, sticky="w", padx=22)
        self.stop_button = self.button(activity, "Durdur", self.stop, width=95, height=32, state="disabled")
        self.stop_button.grid(row=2, column=1, sticky="e", padx=22)
        self.log_view = ctk.CTkTextbox(activity, height=250, fg_color=COLORS["input"], text_color=COLORS["muted"],
                                      font=("Consolas", 12), corner_radius=10, wrap="word", state="disabled")
        self.log_view.grid(row=3, column=0, columnspan=2, sticky="ew", padx=22, pady=(10, 18))
        self.log_view.tag_config("error", foreground="#ff6b7d")
        self.label(self.content, "Kullanıcı token’iyle otomasyon Discord kurallarına aykırı olabilir ve hesap kısıtlaması riski taşır.", size=11, color="warning", wraplength=820).grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 8))
        self.show_stage(0)
        self.bind_all("<FocusIn>", self.ensure_focus_visible, add="+")
        self.after(30, self.reveal)
        if demo:
            self.token.set("demo-token-no-network")
            self.source.set("111111111111111111")
            self.target.set("222222222222222222")
            for widget, value in zip(self.metrics, (12, 4, 18)):
                widget.configure(text=str(value))
            self.preview_caption.configure(text="Örnek önizleme · Ağ bağlantısı kapalı")
            self.set_text(self.summary, "KAYNAK\nTopluluk Sunucum\n\nHEDEF\nYeni Sunucum\n3 rol ve 2 kanal silinecek.\n\nKategoriler, kanal izinleri ve rol sırası birlikte aktarılır.")
            self.show_stage(1)

    def show_stage(self, index, state="Hazır"):
        self.active_stage = index
        for i, (row, number, heading) in enumerate(self.steps):
            row.configure(fg_color=COLORS["subtle"] if i == index else "transparent")
            number.configure(text="✓" if i < index else f"0{i + 1}", text_color=COLORS["success"] if i < index else COLORS["accent"] if i == index else COLORS["muted"])
        self.badge.configure(text="●  " + state, fg_color="#1a2b29" if state in ("Hazır", "Tamamlandı") else COLORS["subtle"], text_color=COLORS["success"] if state in ("Hazır", "Tamamlandı") else COLORS["text"])

    def ensure_focus_visible(self, event):
        if not str(event.widget).startswith(str(self.content) + "."):
            return
        canvas = self.content._parent_canvas
        y = event.widget.winfo_rooty() - canvas.winfo_rooty()
        bottom = y + event.widget.winfo_height()
        delta = y - 12 if y < 12 else bottom - canvas.winfo_height() + 12 if bottom > canvas.winfo_height() - 12 else 0
        if delta:
            canvas.yview_moveto((canvas.canvasy(0) + delta) / max(1, self.content.winfo_height()))

    def update_metrics(self, plan):
        categories = sum(c["type"] == 4 for c in plan["source"]["channels"])
        values = (len(plan["source"]["roles"]) - 1, categories, len(plan["source"]["channels"]) - categories)
        for widget, value in zip(self.metrics, values):
            widget.configure(text=str(value))
        self.preview_caption.configure(text="Kaynak sunucudan aktarılacak yapı")

    def animate_progress(self, fraction):
        self.progress_target = max(0, min(1, fraction))
        self.percent.configure(text=f"%{round(self.progress_target * 100)}")
        self.motion.animate("progress", self.bar.get(), self.progress_target, self.bar.set, 220)

    def reveal(self):
        self.motion.animate("reveal", .86, 1, lambda opacity: self.attributes("-alpha", opacity), 240)
