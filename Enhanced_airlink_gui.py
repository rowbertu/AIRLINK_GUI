import threading
import time
import serial
import serial.tools.list_ports
from PIL import Image, ImageTk
import customtkinter as ctk
import tkinter as tk
import winsound

# ---------------------------
# Theme / Colors (military)
# ---------------------------
BG_PRIMARY = "#223225"   # deep green/charcoal
BG_PANEL = "#2e3b32"     # panel green
ACCENT = "#9fb87f"       # olive accent
TEXT = "#eef6e8"         # soft light
SAND = "#e6dfbf"         # sand (for panels/text backgrounds)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")  # or "dark-blue"

# ---------------------------
# AirLink Boot Splash Screen
# ---------------------------
class SplashScreen(ctk.CTk):
    def __init__(self, on_close):
        super().__init__()
        self.on_close = on_close
        self.title("AirLink Boot")
        self.overrideredirect(True)
        self.configure(fg_color="#000000")
        self.attributes("-topmost", True)

        # --- Center window ---
        w, h = 820, 500
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = int((sw - w) / 2), int((sh - h) / 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # --- Logo ---
        try:
            img = Image.open("LOGO.png").resize((300, 250))
            self.logo_tk = ImageTk.PhotoImage(img)
            self.logo_label = ctk.CTkLabel(self, image=self.logo_tk, text="", fg_color="transparent")
        except Exception:
            self.logo_label = ctk.CTkLabel(
                self,
                text="[AIRLINK]",
                font=("Consolas", 30, "bold"),
                text_color="#00ff88"
            )
        self.logo_label.place(relx=0.5, rely=0.45, anchor="center")

        # --- Title Text ---
        self.title_label = ctk.CTkLabel(
            self,
            text="🛰️ AirLink Defense System 🛰️",
            font=("Consolas", 22, "bold"),
            text_color="#d0f0d0"
        )
        self.title_label.place(relx=0.5, rely=0.85, anchor="center")
        
        self.subtitle = ctk.CTkLabel(
             self,text="Secure Receiver Control System  ",
             font=("Consolas",19, "bold"),
             text_color="#e1efe1"        
        )
        self.subtitle.place(relx=0.5, rely=0.92, anchor="center")

        # --- Initialize fade and animations ---
        self.alpha = 0
        self.fade_in()
        threading.Thread(target=self.morse_airlink_beep, daemon=True).start()
        # Stay longer before fade-out
        self.after(8500, self.fade_out)

    # -----------------------
    # Fade In/Out Animations
    # -----------------------
    def fade_in(self):
        self.alpha += 0.05
        if self.alpha <= 1:
            self.attributes("-alpha", self.alpha)
            self.after(50, self.fade_in)

    def fade_out(self):
        self.alpha -= 0.05
        if self.alpha > 0:
            self.attributes("-alpha", self.alpha)
            self.after(60, self.fade_out)
        else:
            self.destroy()
            self.on_close()

    # -----------------------
    # Morse Code Beep
    # -----------------------
    def morse_airlink_beep(self):
        morse = {
            'A': ".-", 'I': "..", 'R': ".-.", 'L': ".-..", 'N': "-.", 'K': "-.-"
        }

        def beep(sequence, freq=950):
            for c in sequence:
                if c == '.':
                    winsound.Beep(freq, 150)
                elif c == '-':
                    winsound.Beep(freq, 350)
                time.sleep(0.15)

        time.sleep(0.1)  # slight delay after start
        for letter in "AIRLINK":
            beep(morse[letter])
            time.sleep(0.25)

# ---------------------------
# Demo launcher
# ---------------------------
def launch_main():
    app.withdraw()  # hide main window while splash is showing
    print(">>> Main AirLink UI launched")

if __name__ == "__main__":
    splash = SplashScreen(on_close=launch_main)
    splash.mainloop()
    
# ---------------------------
# AirLink UI
# ---------------------------
class AirLinkApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🛰️ AirLink — Receiver Control Center")
        self.geometry("1200x750")
        self.minsize(900, 600)

        # Serial variables
        self.ser = None
        self.running = False
        self.read_thread = None
        self.selected_port = tk.StringVar()
        self.ping_visible = True

        # Background image (original) and label
        self._load_background("bg.png")

        # Layout frames
        self._build_header()
        self._build_controls()
        self._build_logs()

        # Start periodic tasks
        self.after(200, self._refresh_ports)   # initial port scan
        self._status_pulse_state = 0
        self._pulse_status()  # start status animation

    # -------------------------
    # Background handling
    # -------------------------
    def _load_background(self, path):
        try:
            self.original_bg = Image.open(path).convert("RGBA")
        except Exception:
            self.original_bg = None
            return

        # place a label to hold background
        self.bg_label = tk.Label(self, bd=0)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # bind resize
        self.bind("<Configure>", self._on_resize_bg)
        # initial draw
        self._on_resize_bg(None)

    def _on_resize_bg(self, event):
        if not hasattr(self, "original_bg") or self.original_bg is None:
            return
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        # cover (like CSS background-size: cover) preserving aspect ratio
        img = self.original_bg.copy()
        img_ratio = img.width / img.height
        win_ratio = w / h
        if win_ratio > img_ratio:
            # window is wider: fit width, crop top/bottom
            new_w = w
            new_h = round(w / img_ratio)
        else:
            # window taller: fit height, crop left/right
            new_h = h
            new_w = round(h * img_ratio)
        resized = img.resize((new_w, new_h), Image.LANCZOS)

        # crop center
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        cropped = resized.crop((left, top, left + w, top + h))

        self.bg_imgtk = ImageTk.PhotoImage(cropped)
        self.bg_label.configure(image=self.bg_imgtk)

    # -------------------------
    # Header (title + logo)
    # -------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(side="top", fill="x", padx=20, pady=(18, 6))

        # left: logo
        try:
            logo_img = Image.open("LOGO.png").convert("RGBA")
            logo_img = logo_img.resize((100, 88), Image.LANCZOS)
            self.logo_tk = ImageTk.PhotoImage(logo_img)
            logo_label = ctk.CTkLabel(header, image=self.logo_tk, text="", fg_color="transparent")
            logo_label.pack(side="left", padx=(6, 12))
        except Exception:
            pass

        title = ctk.CTkLabel(header, text="AIRLINK DEFENSE SYSTEM", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT, fg_color="transparent")
        title.pack(side="left", padx=6)

        subtitle = ctk.CTkLabel(header, text="Secure Receiver Control Console", font=ctk.CTkFont(size=22, weight="bold"), text_color=SAND, fg_color="transparent")
        subtitle.pack(side="left", padx=(12,0))

        # status indicator at right
        status_frame = ctk.CTkFrame(header, width=220, height=50, fg_color=BG_PANEL, corner_radius=12)
        status_frame.pack(side="right", padx=12)
        status_frame.pack_propagate(False)

        self.status_led = ctk.CTkLabel(status_frame, text="●", text_color="#555555", font=ctk.CTkFont(size=16, weight="bold"), fg_color="transparent")
        self.status_led.pack(side="left", padx=(12,6))
        self.status_text = ctk.CTkLabel(status_frame, text="DISCONNECTED", text_color="#ff6b6b", font=ctk.CTkFont(size=12, weight="bold"), fg_color="transparent")
        self.status_text.pack(side="left")

    # -------------------------
    # Controls (COM selection, buttons)
    # -------------------------
    def _build_controls(self):
        ctrl_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=14)
        ctrl_frame.pack(side="top", fill="x", padx=20, pady=(6, 12))
        ctrl_frame.grid_columnconfigure((0,1,2,3,4), weight=1)

        # COM port label + dropdown
        lbl = ctk.CTkLabel(ctrl_frame, text="Serial Port", text_color=TEXT, fg_color="transparent", anchor="w")
        lbl.grid(row=0, column=0, padx=12, pady=12, sticky="w")

        self.combobox = ctk.CTkComboBox(ctrl_frame, values=[], variable=self.selected_port, width=220, dropdown_hover_color=ACCENT)
        self.combobox.grid(row=0, column=1, padx=6, pady=12, sticky="w")

        refresh_btn = ctk.CTkButton(ctrl_frame, text="Refresh", width=100, command=self._refresh_ports, fg_color=ACCENT, hover_color="#8aa86b")
        refresh_btn.grid(row=0, column=2, padx=6, pady=12)

        connect_btn = ctk.CTkButton(ctrl_frame, text="Connect", width=110, command=self._connect_serial)
        connect_btn.grid(row=0, column=3, padx=6, pady=12)

        disconnect_btn = ctk.CTkButton(ctrl_frame, text="Disconnect", width=110, command=self._disconnect_serial, fg_color="#c77373", hover_color="#d88c8c")
        disconnect_btn.grid(row=0, column=4, padx=6, pady=12)

    # -------------------------
    # Logs area (message + ping)
    # -------------------------
    def _build_logs(self):
        logs_frame = ctk.CTkFrame(self, fg_color="transparent")
        logs_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0,20))

        # left: message log (bigger)
        msg_panel = ctk.CTkFrame(logs_frame, fg_color=BG_PANEL, corner_radius=12)
        msg_panel.pack(side="left", fill="both", expand=True, padx=(0,8), pady=4)

        msg_label = ctk.CTkLabel(msg_panel, text="MESSAGE LOG", text_color=TEXT, font=ctk.CTkFont(size=14, weight="bold"), fg_color="transparent")
        msg_label.pack(anchor="nw", padx=12, pady=(12,6))

        # Use Tk Text inside styled frame for performance
        txt_frame = tk.Frame(msg_panel, bg=BG_PANEL)
        txt_frame.pack(fill="both", expand=True, padx=12, pady=(0,12))
        self.message_text = tk.Text(txt_frame, bg=SAND, fg="#1b1b1b", wrap="word", bd=0, relief="flat", font=("Consolas", 24))
        self.message_text.pack(fill="both", expand=True, side="left")
        self.message_text.insert("end", "Awaiting mission data...\n")
        self.message_text.config(state="disabled")

        # right: ping / controls column
        right_col = ctk.CTkFrame(logs_frame, fg_color="transparent")
        right_col.pack(side="right", fill="y", padx=(8,0), pady=4)

        # toggle button above ping
        self.toggle_btn = ctk.CTkButton(right_col, text="▼ Hide Ping Log", command=self._toggle_ping, width=220, fg_color="#b3aa79", hover_color="#a49e6f")
        self.toggle_btn.pack(pady=(0,8))

        ping_panel = ctk.CTkFrame(right_col, fg_color=BG_PANEL, corner_radius=12)
        ping_panel.pack(fill="y", padx=4, pady=4)

        ping_label = ctk.CTkLabel(ping_panel, text="LINK / PING LOG", text_color=TEXT, font=ctk.CTkFont(size=14, weight="bold"), fg_color="transparent")
        ping_label.pack(anchor="nw", padx=12, pady=(12,6))

        ping_frame = tk.Frame(ping_panel, bg=BG_PANEL)
        ping_frame.pack(fill="both", expand=True, padx=12, pady=(0,12))

        self.ping_text = tk.Text(ping_frame, bg=SAND, fg="#1b1b1b", wrap="word", bd=0, relief="flat", font=("Consolas", 14))
        self.ping_text.pack(fill="both", expand=True)
        self.ping_text.insert("end", "Monitoring link heartbeat...\n")
        self.ping_text.config(state="disabled")

    # -------------------------
    # Status pulse (LED)
    # -------------------------
    def _pulse_status(self):
        # simple pulsing effect for the status LED
        if getattr(self, "ser", None) and getattr(self, "ser", "closed") != None and self.running:
            # connected: cycle green shades
            colors = ["#7fd27f", "#98da98", "#b1e6b1"]
            c = colors[self._status_pulse_state % len(colors)]
            self.status_led.configure(text="●", text_color=c)
            self.status_text.configure(text="CONNECTED", text_color="#7ed07e")
            self._status_pulse_state += 1
        else:
            self.status_led.configure(text="●", text_color="#555555")
            self.status_text.configure(text="DISCONNECTED", text_color="#ff7b7b")
            self._status_pulse_state = 0
        self.after(600, self._pulse_status)

    # -------------------------
    # COM port refresh/connect/disconnect
    # -------------------------
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            self.combobox.configure(values=ports)
            try:
                # don't overwrite user selection unless empty
                if not self.selected_port.get():
                    self.selected_port.set(ports[0])
            except Exception:
                pass
        else:
            self.combobox.configure(values=[])
            self.selected_port.set("")

        # refresh automatically every 5s
        self.after(5000, self._refresh_ports)

    def _connect_serial(self):
        port = self.selected_port.get()
        if not port:
            self._log_message("No COM port selected.")
            return
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.5)
            self.running = True
            self._log_message(f"Connected to {port}")
            # start read thread
            self.read_thread = threading.Thread(target=self._serial_reader, daemon=True)
            self.read_thread.start()
        except Exception as e:
            self._log_message(f"Error opening {port}: {e}")

    def _disconnect_serial(self):
        self.running = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self._log_message("Disconnected.")
        except Exception:
            pass

    # -------------------------
    # Serial reader & message routing
    # -------------------------
    def _serial_reader(self):
        buf = b""
        while self.running and self.ser and self.ser.is_open:
            try:
                data = self.ser.readline()
                if not data:
                    time.sleep(0.01)
                    continue
                line = data.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                # separate ping vs message
                if "Ping" in line or "Pong" in line:
                    self._log_ping(line)
                else:
                    self._log_message(line)
            except Exception as e:
                self._log_message(f"Serial error: {e}")
                break
        # cleanup when loop exits
        self.running = False

    # -------------------------
    # Logging helpers (thread-safe via after)
    # -------------------------
    def _log_message(self, text):
        def _append():
            self.message_text.config(state="normal")
            self.message_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {text}\n")
            self.message_text.see("end")
            self.message_text.config(state="disabled")
        self.after(0, _append)

    def _log_ping(self, text):
        def _append():
            self.ping_text.config(state="normal")
            self.ping_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {text}\n")
            self.ping_text.see("end")
            self.ping_text.config(state="disabled")
        self.after(0, _append)

    # -------------------------
    # Ping toggle
    # -------------------------
    def _toggle_ping(self):
        if self.ping_visible:
            # hide ping panel by reducing its pack_forget equivalent: we just disable and shrink
            self.ping_text.master.master.pack_forget()  # ping_panel's parent (right_col) hide entire column
            self.toggle_btn.configure(text="▶ Show Ping Log")
            self.ping_visible = False
        else:
            # rebuild right side by recreating logs area (simple approach)
            # NOTE: simpler to restart app layout; we'll re-pack logs correctly by destroying and rebuilding
            for w in self.pack_slaves():
                pass
            # Quick and simple: re-create logs area; easier approach is to restart layout
            # For simplicity, just make ping visible again by packing parent (there's only one right_col)
            # We used pack_forget earlier; now repack the logs area by calling _build_logs (recreate)
            # CAVEAT: this approach may duplicate; to keep it simple we will just re-run build logs
            # In practice you'd want a cleaner show/hide; here we keep it fast:
            self._rebuild_logs_show_ping()

    def _rebuild_logs_show_ping(self):
        # Destroy and rebuild logs area to restore ping
        # find and destroy old logs_frame (there's only one)
        for child in list(self.pack_slaves()):
            pass
        # Simpler: just repack logs by calling _build_logs again after clearing existing
        # remove existing logs (if any)
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkFrame) and w is not None:
                # skip header and controls heuristics by name not available; we won't destroy header/control frames
                pass
        # To keep this function safe, we will toggle by just packing ping panel again:
        # find right_col by searching descendants for the toggle button's parent
        # VERY simple: unpack then repack ping_text.master.master (the ping_panel parent) into logs_frame
        try:
            right_parent = self.toggle_btn.master
            right_parent.pack(side="right", fill="y", padx=(8,0), pady=4)
            self.toggle_btn.configure(text="▼ Hide Ping Log")
            self.ping_visible = True
        except Exception:
            # fallback: rebuild entire UI (not ideal but safe)
            self._log_message("Restoring ping panel (fallback). Restart app if layout is corrupted.")
            self.ping_visible = True

    # -------------------------
    # Utilities
    # -------------------------
    def pack_slaves(self):
        # convenience: return packed children (top-level frames)
        return [w for w in self.winfo_children() if str(w.winfo_manager())]

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    app = AirLinkApp()
    app.mainloop()
