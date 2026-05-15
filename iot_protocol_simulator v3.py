#!/usr/bin/env python3
"""
================================================================
  IoT Protocol Simulator  —  MQTT / MQTTS / CoAP / AMQP / NFC
================================================================

  Developed by: Dr. Mohammed Tawfik
  Assistant Professor — Cybersecurity & Cloud Computing
  Ajloun National University  /  Sana'a University
  Contact:      kmkhol01@gmail.com

  A teaching & research tool that simulates IoT messaging protocols
  with 12 live virtual sensors, real-time plots, and a modern UI.

  Install dependencies:
      pip install customtkinter paho-mqtt aiocoap pika ndeflib matplotlib

  Run:
      python iot_protocol_simulator.py
"""

import sys, os, threading, asyncio, ssl, json, random, time
from collections import deque
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

# ──────────────────────────────────────────────────────────────
#  CustomTkinter (modern UI) — REQUIRED
# ──────────────────────────────────────────────────────────────
try:
    import customtkinter as ctk
except ImportError:
    print("\n" + "="*60)
    print("  ✗ customtkinter is required for the modern UI.")
    print("="*60)
    print("  Install it with:")
    print(f"      {sys.executable} -m pip install customtkinter\n")
    sys.exit(1)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ──────────────────────────────────────────────────────────────
#  Protocol libraries (optional)
# ──────────────────────────────────────────────────────────────
try:
    import paho.mqtt.client as mqtt
    MQTT_OK = True
except ImportError:
    MQTT_OK = False

try:
    from aiocoap import Context, Message, Code
    import aiocoap.resource as resource
    COAP_OK = True
except ImportError:
    COAP_OK = False

try:
    import pika
    AMQP_OK = True
except ImportError:
    AMQP_OK = False

try:
    import ndef
    NDEF_OK = True
except ImportError:
    NDEF_OK = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    # Dark theme for plots
    plt.rcParams.update({
        "axes.facecolor":  "#1f1f2e",
        "figure.facecolor":"#181822",
        "savefig.facecolor":"#181822",
        "text.color":      "#e0e0e0",
        "axes.labelcolor": "#cccccc",
        "axes.edgecolor":  "#444455",
        "xtick.color":     "#aaaaaa",
        "ytick.color":     "#aaaaaa",
        "grid.color":      "#33334a",
        "grid.alpha":      0.4,
        "axes.titlesize":  9,
        "axes.titleweight":"bold",
        "axes.titlecolor": "#e0e0e0",
        "font.size":       8,
    })
    MPL_OK = True
except ImportError:
    MPL_OK = False


# ──────────────────────────────────────────────────────────────
#  Startup diagnostics — helps identify which Python is running
# ──────────────────────────────────────────────────────────────
print("="*64)
print("  IoT Protocol Simulator  —  by Dr. Mohammed Tawfik")
print("  Contact: kmkhol01@gmail.com")
print("="*64)
print(f"  Python     : {sys.version.split()[0]}")
print(f"  Executable : {sys.executable}")
print(f"  Working dir: {os.getcwd()}")
print("-"*64)
print(f"  customtkinter : ✓ {ctk.__version__ if hasattr(ctk,'__version__') else ''}")
for name, ok in [("paho-mqtt", MQTT_OK), ("aiocoap", COAP_OK),
                 ("pika", AMQP_OK), ("ndeflib", NDEF_OK),
                 ("matplotlib", MPL_OK)]:
    print(f"  {name:14s}: {'✓' if ok else '✗ (pip install ' + name + ')'}")
print("="*64 + "\n")


# ──────────────────────────────────────────────────────────────
#  Theme palette
# ──────────────────────────────────────────────────────────────
PAL = {
    "bg":        "#13131c",
    "sidebar":   "#0f0f17",
    "card":      "#1e1e2e",
    "card2":     "#262638",
    "border":    "#2a2a3e",
    "accent":    "#3b82f6",
    "accent2":   "#60a5fa",
    "ok":        "#10b981",
    "warn":      "#f59e0b",
    "err":       "#ef4444",
    "text":      "#e6e6f0",
    "muted":     "#8b8ba0",
    "tx":        "#60a5fa",
    "rx":        "#34d399",
    "info":      "#9ca3af",
}

# Public MQTT brokers (some may be blocked in your region — try multiple)
MQTT_BROKERS = [
    "test.mosquitto.org",
    "broker.hivemq.com",
    "broker.emqx.io",
    "mqtt.eclipseprojects.io",
    "public.mqtthq.com",
    "localhost",
]


def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


# ──────────────────────────────────────────────────────────────
#  Reusable UI helpers
# ──────────────────────────────────────────────────────────────
def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=PAL["card"], corner_radius=10,
                        border_width=1, border_color=PAL["border"], **kw)

def section_title(parent, text, icon=""):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", padx=16, pady=(12, 4))
    ctk.CTkLabel(f, text=f"{icon} {text}".strip(),
                 font=ctk.CTkFont(size=13, weight="bold"),
                 text_color=PAL["text"]).pack(anchor="w")
    return f

def page_header(parent, title, subtitle=""):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", padx=24, pady=(20, 8))
    ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=24, weight="bold"),
                 text_color=PAL["text"]).pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(f, text=subtitle, font=ctk.CTkFont(size=12),
                     text_color=PAL["muted"]).pack(anchor="w", pady=(2,0))
    return f

class StatusBadge(ctk.CTkFrame):
    def __init__(self, parent, text="Disconnected", color=PAL["err"]):
        super().__init__(parent, fg_color=PAL["card2"], corner_radius=20, height=28)
        self.dot = ctk.CTkLabel(self, text="●", text_color=color,
                                font=ctk.CTkFont(size=14))
        self.dot.pack(side="left", padx=(10,4))
        self.lbl = ctk.CTkLabel(self, text=text, font=ctk.CTkFont(size=11),
                                text_color=PAL["text"])
        self.lbl.pack(side="left", padx=(0,12), pady=4)
    def set(self, text, color):
        self.dot.configure(text_color=color)
        self.lbl.configure(text=text)


class LogView(ctk.CTkTextbox):
    """Color-coded protocol log."""
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="#0d0d16", text_color=PAL["text"],
                         font=ctk.CTkFont(family="Consolas", size=11),
                         border_width=1, border_color=PAL["border"],
                         corner_radius=8, **kw)
        # Tag colors
        self._tk_text = self._textbox  # underlying tk.Text
        self._tk_text.tag_config("tx",   foreground=PAL["tx"])
        self._tk_text.tag_config("rx",   foreground=PAL["rx"])
        self._tk_text.tag_config("err",  foreground=PAL["err"])
        self._tk_text.tag_config("warn", foreground=PAL["warn"])
        self._tk_text.tag_config("info", foreground=PAL["muted"])
        self._tk_text.tag_config("ok",   foreground=PAL["ok"])
    def log(self, msg, tag="info"):
        def _do():
            try:
                self._tk_text.configure(state="normal")
                self._tk_text.insert("end", f"[{ts()}] {msg}\n", tag)
                self._tk_text.see("end")
                # limit size
                lines = int(self._tk_text.index("end-1c").split(".")[0])
                if lines > 1000:
                    self._tk_text.delete("1.0", "200.0")
            except Exception:
                pass
        try:
            self.after(0, _do)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
#  Virtual Sensor model
# ══════════════════════════════════════════════════════════════
class VirtualSensor:
    def __init__(self, name, unit, mean, low, high, std,
                 color="#3b82f6", kind="walk", drift=0.0):
        self.name = name; self.unit = unit
        self.mean = mean; self.low = low; self.high = high
        self.std = std; self.color = color
        self.kind = kind; self.drift = drift
        self.value = mean
        self.enabled = tk.BooleanVar(value=True)

    def tick(self):
        if self.kind == "motion":
            self.value = 1.0 if random.random() < 0.07 else 0.0
        elif self.kind == "decay":
            self.value = max(self.low, self.value - random.uniform(0, abs(self.drift) or 0.02))
        else:
            reversion = (self.mean - self.value) * 0.05
            self.value += reversion + self.drift + random.gauss(0, self.std)
            self.value = max(self.low, min(self.high, self.value))
        return self.value


# ══════════════════════════════════════════════════════════════
#  DASHBOARD PAGE — 12 sensors + live plots + publisher
# ══════════════════════════════════════════════════════════════
class DashboardPage(ctk.CTkFrame):
    HIST = 120

    def __init__(self, parent):
        super().__init__(parent, fg_color=PAL["bg"])
        self.client = None
        self.connected = False
        self.running = False
        self.tick_job = None
        self.msg_count = 0
        self.sensors = self._make_sensors()
        self.history = {s.name: deque(maxlen=self.HIST) for s in self.sensors}
        self._build()

    def _make_sensors(self):
        return [
            VirtualSensor("temperature","°C",   22,  15, 38,  0.3,  color="#ef4444"),
            VirtualSensor("humidity",   "%",    50,  20, 90,  0.8,  color="#3b82f6"),
            VirtualSensor("pressure",   "hPa", 1013,990,1030, 0.2,  color="#8b5cf6"),
            VirtualSensor("light",      "lux",  350, 0,1000, 30,    color="#f59e0b"),
            VirtualSensor("co2",        "ppm",  450,300,2000,15,    color="#64748b"),
            VirtualSensor("gas_mq2",    "ppm",  220, 0,1000, 12,    color="#a855f7"),
            VirtualSensor("pm25",       "µg/m³",12,  0, 200, 1,     color="#94a3b8"),
            VirtualSensor("sound",      "dB",   42,  20,110, 2,     color="#14b8a6"),
            VirtualSensor("heart_rate", "bpm",  72,  50,140, 1.5,   color="#ec4899"),
            VirtualSensor("vibration",  "g",    0.1, 0,  5,  0.08,  color="#f97316"),
            VirtualSensor("uv_index",   "",     3,   0, 11,  0.25,  color="#22c55e"),
            VirtualSensor("motion",     "PIR",  0,   0,  1,  0,     color="#06b6d4", kind="motion"),
        ]

    def _build(self):
        page_header(self, "📊  Sensor Dashboard",
                    "12 virtual sensors publishing live telemetry to MQTT/MQTTS broker")

        # ---- Control card ----
        ctrl = card(self); ctrl.pack(fill="x", padx=20, pady=10)
        row1 = ctk.CTkFrame(ctrl, fg_color="transparent"); row1.pack(fill="x", padx=14, pady=(12,6))

        ctk.CTkLabel(row1, text="Protocol", text_color=PAL["muted"]).pack(side="left", padx=(0,4))
        self.proto = ctk.CTkComboBox(row1, values=["MQTT","MQTTS","Local only"],
                                     width=110, state="readonly")
        self.proto.set("MQTT"); self.proto.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Broker", text_color=PAL["muted"]).pack(side="left", padx=(12,4))
        self.broker = ctk.CTkComboBox(row1, values=MQTT_BROKERS, width=200)
        self.broker.set("broker.hivemq.com"); self.broker.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Port", text_color=PAL["muted"]).pack(side="left", padx=(12,4))
        self.port = ctk.CTkEntry(row1, width=70); self.port.insert(0,"1883"); self.port.pack(side="left")

        ctk.CTkLabel(row1, text="Prefix", text_color=PAL["muted"]).pack(side="left", padx=(12,4))
        self.prefix = ctk.CTkEntry(row1, width=110); self.prefix.insert(0,"iot/demo")
        self.prefix.pack(side="left")

        ctk.CTkLabel(row1, text="User", text_color=PAL["muted"]).pack(side="left", padx=(12,4))
        self.user = ctk.CTkEntry(row1, width=100, placeholder_text="(optional)")
        self.user.pack(side="left")
        ctk.CTkLabel(row1, text="Pass", text_color=PAL["muted"]).pack(side="left", padx=(8,4))
        self.pwd = ctk.CTkEntry(row1, width=100, show="•", placeholder_text="(optional)")
        self.pwd.pack(side="left")

        self.btn_conn = ctk.CTkButton(row1, text="Connect", width=100, command=self.toggle_connect)
        self.btn_conn.pack(side="right", padx=4)

        row2 = ctk.CTkFrame(ctrl, fg_color="transparent"); row2.pack(fill="x", padx=14, pady=(2,12))
        ctk.CTkLabel(row2, text="Rate (Hz)", text_color=PAL["muted"]).pack(side="left", padx=(0,6))
        self.rate = tk.DoubleVar(value=2.0)
        ctk.CTkSlider(row2, from_=0.5, to=10, variable=self.rate, width=160,
                      command=lambda v: self.rate_lbl.configure(text=f"{float(v):.1f}")
                      ).pack(side="left", padx=4)
        self.rate_lbl = ctk.CTkLabel(row2, text="2.0", width=36); self.rate_lbl.pack(side="left")

        self.conn_badge = StatusBadge(row2, "Disconnected", PAL["err"])
        self.conn_badge.pack(side="left", padx=10)
        self.run_badge = StatusBadge(row2, "Idle", PAL["muted"])
        self.run_badge.pack(side="left", padx=4)
        self.count_lbl = ctk.CTkLabel(row2, text="Published: 0", text_color=PAL["muted"])
        self.count_lbl.pack(side="left", padx=12)

        self.btn_run = ctk.CTkButton(row2, text="▶  Start", width=100, fg_color=PAL["ok"],
                                     hover_color="#0e9d6e", command=self.toggle_run)
        self.btn_run.pack(side="right", padx=4)
        ctk.CTkButton(row2, text="↻ Reset", width=80, fg_color=PAL["card2"],
                      hover_color="#33334a", command=self.reset).pack(side="right", padx=4)

        # ---- Sensor toggles ----
        tog_card = card(self); tog_card.pack(fill="x", padx=20, pady=(0,10))
        ctk.CTkLabel(tog_card, text="SENSORS  —  click to enable/disable",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        tog_inner = ctk.CTkFrame(tog_card, fg_color="transparent")
        tog_inner.pack(fill="x", padx=10, pady=(0,10))
        for i, s in enumerate(self.sensors):
            cb = ctk.CTkCheckBox(tog_inner, text=s.name, variable=s.enabled,
                                 fg_color=s.color, hover_color=s.color, border_color=s.color,
                                 font=ctk.CTkFont(size=11))
            cb.grid(row=i//6, column=i%6, sticky="w", padx=10, pady=3)

        # ---- Plot grid ----
        if not MPL_OK:
            warn = card(self); warn.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(warn, text=f"⚠  matplotlib not installed in this Python.\n"
                                    f"   Install with:  {sys.executable} -m pip install matplotlib",
                         text_color=PAL["warn"], justify="left",
                         font=ctk.CTkFont(family="Consolas", size=11)
                         ).pack(padx=14, pady=14, anchor="w")
            return

        plot_card = card(self); plot_card.pack(fill="both", expand=True, padx=20, pady=(0,20))
        self.fig = Figure(figsize=(11, 5.5), dpi=85)
        self.axes, self.lines = {}, {}
        for i, s in enumerate(self.sensors):
            ax = self.fig.add_subplot(3, 4, i+1)
            line, = ax.plot([], [], color=s.color, linewidth=1.5)
            ax.set_title(f"{s.name} ({s.unit})")
            ax.tick_params(labelsize=6)
            ax.grid(True, alpha=0.3)
            self.axes[s.name] = ax; self.lines[s.name] = line
        self.fig.tight_layout(pad=1.0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_card)
        self.canvas.get_tk_widget().configure(bg=PAL["card"], highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas.draw()

    # --- Connection ---
    def toggle_connect(self):
        if self.connected: self._disconnect()
        else: self._connect()

    def _connect(self):
        if self.proto.get() == "Local only":
            self.connected = True
            self.conn_badge.set("Local mode", PAL["warn"])
            self.btn_conn.configure(text="Stop Local")
            return
        if not MQTT_OK:
            messagebox.showerror("Missing", "pip install paho-mqtt"); return
        try:
            self.client = mqtt.Client(client_id=f"dash-{random.randint(1000,9999)}")
            if self.user.get().strip():
                self.client.username_pw_set(self.user.get(), self.pwd.get())
            port = int(self.port.get())
            if self.proto.get() == "MQTTS":
                self.client.tls_set(cert_reqs=ssl.CERT_NONE)
                self.client.tls_insecure_set(True)
                if port == 1883: port = 8883
            self.client.on_connect    = lambda c,u,f,rc: self._on_conn(rc)
            self.client.on_disconnect = lambda c,u,rc: self._on_disconn(rc)
            self.client.connect_async(self.broker.get(), port, keepalive=60)
            self.client.loop_start()
            self.conn_badge.set(f"Connecting to {self.broker.get()}:{port}…", PAL["warn"])
            self.after(10000, self._connack_timeout)
        except Exception as e:
            messagebox.showerror("Connect error", str(e))

    def _connack_timeout(self):
        if not self.connected and self.client:
            self.conn_badge.set("No CONNACK — try another broker", PAL["err"])

    def _on_conn(self, rc):
        if rc == 0:
            self.connected = True
            self.after(0, lambda: self.conn_badge.set("Connected", PAL["ok"]))
            self.after(0, lambda: self.btn_conn.configure(text="Disconnect"))
        else:
            self.after(0, lambda: self.conn_badge.set(f"Failed rc={rc}", PAL["err"]))

    def _on_disconn(self, rc):
        self.connected = False
        self.after(0, lambda: self.conn_badge.set("Disconnected", PAL["err"]))
        self.after(0, lambda: self.btn_conn.configure(text="Connect"))

    def _disconnect(self):
        if self.proto.get() == "Local only":
            self.connected = False
            self.conn_badge.set("Disconnected", PAL["err"])
            self.btn_conn.configure(text="Connect"); return
        try:
            if self.client:
                self.client.loop_stop(); self.client.disconnect()
        except Exception: pass

    # --- Run loop ---
    def toggle_run(self):
        if self.running:
            self.running = False
            self.btn_run.configure(text="▶  Start", fg_color=PAL["ok"])
            self.run_badge.set("Stopped", PAL["muted"])
            if self.tick_job: self.after_cancel(self.tick_job); self.tick_job = None
        else:
            self.running = True
            self.btn_run.configure(text="⏸  Stop", fg_color=PAL["warn"])
            self.run_badge.set("Running", PAL["ok"])
            self._tick()

    def _tick(self):
        if not self.running: return
        prefix = self.prefix.get().strip("/")
        local = (self.proto.get() == "Local only")
        for s in self.sensors:
            if not s.enabled.get(): continue
            val = s.tick()
            self.history[s.name].append(val)
            if self.client and self.connected and not local:
                payload = json.dumps({
                    "sensor": s.name, "value": round(val,3),
                    "unit": s.unit, "ts": datetime.now().isoformat(timespec="seconds")
                })
                try:
                    self.client.publish(f"{prefix}/{s.name}", payload, qos=0)
                    self.msg_count += 1
                except Exception: pass
        self.count_lbl.configure(text=f"Published: {self.msg_count:,}")
        self._refresh()
        self.tick_job = self.after(int(1000/max(self.rate.get(),0.1)), self._tick)

    def _refresh(self):
        if not MPL_OK: return
        for s in self.sensors:
            h = self.history[s.name]
            if not h: continue
            xs = list(range(-len(h)+1, 1))
            self.lines[s.name].set_data(xs, list(h))
            ax = self.axes[s.name]
            ax.relim(); ax.autoscale_view()
            ax.set_title(f"{s.name}: {s.value:.2f} {s.unit}")
        self.canvas.draw_idle()

    def reset(self):
        for s in self.sensors: s.value = s.mean
        for k in self.history: self.history[k].clear()
        self.msg_count = 0
        self.count_lbl.configure(text="Published: 0")
        self._refresh()


# ══════════════════════════════════════════════════════════════
#  MONITOR PAGE — subscriber that auto-discovers sensors
# ══════════════════════════════════════════════════════════════
class MonitorPage(ctk.CTkFrame):
    HIST = 120
    REDRAW_MS = 400

    def __init__(self, parent):
        super().__init__(parent, fg_color=PAL["bg"])
        self.client = None
        self.connected = False
        self.history, self.units, self.axes, self.lines = {}, {}, {}, {}
        self.msg_count = 0
        self.last_count = 0
        self._build()
        if MPL_OK: self.after(self.REDRAW_MS, self._periodic_redraw)
        self.after(1000, self._update_rate)

    def _build(self):
        page_header(self, "📡  Live Monitor",
                    "Subscribe to a topic pattern and auto-plot every sensor that arrives")

        ctrl = card(self); ctrl.pack(fill="x", padx=20, pady=10)
        row = ctk.CTkFrame(ctrl, fg_color="transparent"); row.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(row, text="Broker", text_color=PAL["muted"]).pack(side="left", padx=(0,4))
        self.broker = ctk.CTkComboBox(row, values=MQTT_BROKERS, width=200)
        self.broker.set("broker.hivemq.com"); self.broker.pack(side="left")
        ctk.CTkLabel(row, text="Port", text_color=PAL["muted"]).pack(side="left", padx=(10,4))
        self.port = ctk.CTkEntry(row, width=70); self.port.insert(0,"1883"); self.port.pack(side="left")
        self.tls_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(row, text="TLS", variable=self.tls_var, width=50,
                        command=self._toggle_port).pack(side="left", padx=10)
        ctk.CTkLabel(row, text="Topic", text_color=PAL["muted"]).pack(side="left", padx=(8,4))
        self.topic = ctk.CTkEntry(row, width=160); self.topic.insert(0,"iot/demo/+")
        self.topic.pack(side="left")
        ctk.CTkLabel(row, text="User", text_color=PAL["muted"]).pack(side="left", padx=(8,4))
        self.user = ctk.CTkEntry(row, width=90, placeholder_text="optional")
        self.user.pack(side="left")
        ctk.CTkLabel(row, text="Pass", text_color=PAL["muted"]).pack(side="left", padx=(8,4))
        self.pwd = ctk.CTkEntry(row, width=90, show="•", placeholder_text="optional")
        self.pwd.pack(side="left")
        self.btn = ctk.CTkButton(row, text="Connect & Subscribe", width=170, command=self.toggle)
        self.btn.pack(side="right", padx=4)
        ctk.CTkButton(row, text="Clear", width=80, fg_color=PAL["card2"],
                      hover_color="#33334a", command=self.clear).pack(side="right", padx=4)

        row2 = ctk.CTkFrame(ctrl, fg_color="transparent"); row2.pack(fill="x", padx=14, pady=(0,12))
        self.status = StatusBadge(row2, "Disconnected", PAL["err"])
        self.status.pack(side="left")
        self.count_lbl = ctk.CTkLabel(row2, text="Messages: 0  (0/s)", text_color=PAL["muted"])
        self.count_lbl.pack(side="left", padx=14)

        if not MPL_OK:
            w = card(self); w.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(w, text="⚠  matplotlib not installed.", text_color=PAL["warn"]
                         ).pack(padx=14, pady=14)
            return

        plot_card = card(self); plot_card.pack(fill="both", expand=True, padx=20, pady=(0,20))
        self.fig = Figure(figsize=(11, 6), dpi=85)
        ax = self.fig.add_subplot(1,1,1)
        ax.text(0.5, 0.6,
                "Waiting for incoming messages…",
                ha="center", va="center", color=PAL["text"], fontsize=14, fontweight="bold")
        ax.text(0.5, 0.42,
                "To see data:\n\n"
                "1.  Open the  📊 Dashboard  tab\n"
                "2.  Use the SAME broker & port as here\n"
                "3.  Match the Prefix to this Topic (e.g. iot/demo)\n"
                "4.  Click  Connect  →  ▶ Start\n\n"
                "Or wait for any other publisher on this topic.",
                ha="center", va="center", color=PAL["muted"], fontsize=11)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_visible(False)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_card)
        self.canvas.get_tk_widget().configure(bg=PAL["card"], highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self.canvas.draw()

    def _toggle_port(self):
        cur = self.port.get()
        self.port.delete(0,"end")
        self.port.insert(0, "8883" if self.tls_var.get() else "1883")

    def toggle(self):
        if self.connected: self._disconnect()
        else: self._connect()

    def _connect(self):
        if not MQTT_OK:
            messagebox.showerror("Missing","pip install paho-mqtt"); return
        try:
            self.client = mqtt.Client(client_id=f"mon-{random.randint(1000,9999)}")
            if self.user.get().strip():
                self.client.username_pw_set(self.user.get(), self.pwd.get())
            if self.tls_var.get():
                self.client.tls_set(cert_reqs=ssl.CERT_NONE)
                self.client.tls_insecure_set(True)
            self.client.on_connect    = self._on_conn
            self.client.on_disconnect = self._on_disconn
            self.client.on_message    = self._on_msg
            self.client.connect_async(self.broker.get(), int(self.port.get()), keepalive=60)
            self.client.loop_start()
            self.status.set(f"Connecting…", PAL["warn"])
        except Exception as e:
            messagebox.showerror("Connect error", str(e))

    def _on_conn(self, c,u,f,rc):
        if rc == 0:
            self.connected = True
            self.after(0, lambda: self.status.set("Connected", PAL["ok"]))
            self.after(0, lambda: self.btn.configure(text="Disconnect"))
            self.client.subscribe(self.topic.get(), 0)
        else:
            self.after(0, lambda: self.status.set(f"Failed rc={rc}", PAL["err"]))

    def _on_disconn(self, c,u,rc):
        self.connected = False
        self.after(0, lambda: self.status.set("Disconnected", PAL["err"]))
        self.after(0, lambda: self.btn.configure(text="Connect & Subscribe"))

    def _on_msg(self, c, u, msg):
        topic, payload = msg.topic, msg.payload
        self.after(0, lambda: self._process(topic, payload))

    def _process(self, topic, payload):
        try:
            data = json.loads(payload.decode())
            name = str(data.get("sensor") or topic.split("/")[-1])
            value = float(data.get("value"))
            unit = str(data.get("unit",""))
        except Exception:
            name = topic.split("/")[-1]
            try: value = float(payload.decode())
            except Exception: return
            unit = ""
        if name not in self.history:
            self.history[name] = deque(maxlen=self.HIST)
            self.units[name] = unit
            self._rebuild_grid()
        self.history[name].append(value)
        self.msg_count += 1

    def _rebuild_grid(self):
        if not MPL_OK: return
        self.fig.clear(); self.axes.clear(); self.lines.clear()
        n = len(self.history); cols = min(4, max(1, n)); rows = (n + cols - 1) // cols
        palette = ["#ef4444","#3b82f6","#8b5cf6","#f59e0b","#64748b","#a855f7",
                   "#94a3b8","#14b8a6","#ec4899","#f97316","#22c55e","#06b6d4"]
        for i, nm in enumerate(self.history.keys()):
            ax = self.fig.add_subplot(rows, cols, i+1)
            line, = ax.plot([], [], color=palette[i % len(palette)], linewidth=1.5)
            ax.set_title(nm); ax.tick_params(labelsize=6); ax.grid(True, alpha=0.3)
            self.axes[nm] = ax; self.lines[nm] = line
        self.fig.tight_layout(pad=1.0)

    def _periodic_redraw(self):
        if MPL_OK and self.history:
            for nm, h in self.history.items():
                if not h or nm not in self.lines: continue
                xs = list(range(-len(h)+1, 1)); ys = list(h)
                self.lines[nm].set_data(xs, ys)
                self.axes[nm].relim(); self.axes[nm].autoscale_view()
                self.axes[nm].set_title(f"{nm}: {ys[-1]:.2f} {self.units.get(nm,'')}")
            self.canvas.draw_idle()
        self.after(self.REDRAW_MS, self._periodic_redraw)

    def _update_rate(self):
        rate = self.msg_count - self.last_count
        self.last_count = self.msg_count
        self.count_lbl.configure(text=f"Messages: {self.msg_count:,}  ({rate}/s)")
        self.after(1000, self._update_rate)

    def clear(self):
        self.history.clear(); self.units.clear()
        self.msg_count = 0; self.last_count = 0
        if MPL_OK:
            self.fig.clear()
            ax = self.fig.add_subplot(1,1,1)
            ax.text(0.5,0.5,"Cleared.", ha="center", va="center", color=PAL["muted"])
            ax.set_xticks([]); ax.set_yticks([])
            self.canvas.draw_idle()

    def _disconnect(self):
        try:
            if self.client: self.client.loop_stop(); self.client.disconnect()
        except Exception: pass


# ══════════════════════════════════════════════════════════════
#  MQTT / MQTTS PAGE
# ══════════════════════════════════════════════════════════════
class MQTTPage(ctk.CTkFrame):
    def __init__(self, parent, tls=False):
        super().__init__(parent, fg_color=PAL["bg"])
        self.tls = tls
        self.client = None
        self.connected = False
        self._build()

    def _build(self):
        title = "🔒  MQTTS  —  MQTT over TLS" if self.tls else "📨  MQTT  —  Publisher / Subscriber"
        sub = "Encrypted MQTT v3.1.1 (port 8883) using TLS" if self.tls else \
              "MQTT v3.1.1 plaintext (port 1883). Choose another broker if connection fails."
        page_header(self, title, sub)

        scroll = ctk.CTkScrollableFrame(self, fg_color=PAL["bg"])
        scroll.pack(fill="both", expand=True, padx=14, pady=8)

        # Connection card
        c = card(scroll); c.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(c, text="BROKER CONNECTION",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,6))

        g = ctk.CTkFrame(c, fg_color="transparent"); g.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(g, text="Host").grid(row=0,column=0,sticky="e", padx=4, pady=4)
        self.host = ctk.CTkComboBox(g, values=MQTT_BROKERS, width=200)
        self.host.set("broker.hivemq.com"); self.host.grid(row=0,column=1, pady=4, padx=4)
        ctk.CTkLabel(g, text="Port").grid(row=0,column=2,sticky="e", padx=4)
        self.port = ctk.CTkEntry(g, width=80)
        self.port.insert(0, "8883" if self.tls else "1883")
        self.port.grid(row=0,column=3, padx=4)
        ctk.CTkLabel(g, text="ClientID").grid(row=0,column=4,sticky="e", padx=4)
        self.cid = ctk.CTkEntry(g, width=160)
        self.cid.insert(0, f"sim-{random.randint(1000,9999)}")
        self.cid.grid(row=0,column=5, padx=4)

        ctk.CTkLabel(g, text="User").grid(row=1,column=0,sticky="e", padx=4, pady=4)
        self.user = ctk.CTkEntry(g, width=200); self.user.grid(row=1,column=1, pady=4, padx=4)
        ctk.CTkLabel(g, text="Pass").grid(row=1,column=2,sticky="e", padx=4)
        self.pwd = ctk.CTkEntry(g, width=120, show="•"); self.pwd.grid(row=1,column=3, padx=4)

        self.status = StatusBadge(g, "Disconnected", PAL["err"])
        self.status.grid(row=1, column=4, padx=10, pady=4)
        self.btn_conn = ctk.CTkButton(g, text="Connect", width=120, command=self.toggle_connect)
        self.btn_conn.grid(row=1, column=5, padx=4, pady=4)

        # Pub / Sub side by side
        ps = ctk.CTkFrame(scroll, fg_color="transparent"); ps.pack(fill="x", padx=6, pady=6)
        ps.grid_columnconfigure((0,1), weight=1)

        # Publisher
        pub = card(ps); pub.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        ctk.CTkLabel(pub, text="PUBLISHER",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        pf = ctk.CTkFrame(pub, fg_color="transparent"); pf.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(pf, text="Topic").grid(row=0,column=0,sticky="e", pady=3, padx=4)
        self.pub_topic = ctk.CTkEntry(pf, width=240); self.pub_topic.insert(0,"sensors/temp")
        self.pub_topic.grid(row=0,column=1, sticky="we", pady=3, padx=4)
        ctk.CTkLabel(pf, text="QoS").grid(row=1,column=0,sticky="e", pady=3, padx=4)
        self.pub_qos = ctk.CTkComboBox(pf, values=["0","1","2"], width=80, state="readonly")
        self.pub_qos.set("0"); self.pub_qos.grid(row=1,column=1, sticky="w", pady=3, padx=4)
        self.retain_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(pf, text="Retain", variable=self.retain_var
                        ).grid(row=2, column=1, sticky="w", pady=3, padx=4)
        ctk.CTkLabel(pf, text="Message").grid(row=3,column=0,sticky="ne", pady=3, padx=4)
        self.pub_msg = ctk.CTkTextbox(pf, height=80, fg_color="#0d0d16",
                                      border_width=1, border_color=PAL["border"],
                                      font=ctk.CTkFont(family="Consolas", size=11))
        self.pub_msg.grid(row=3,column=1, sticky="we", pady=3, padx=4)
        self.pub_msg.insert("1.0", '{"temperature": 24.5, "unit": "C"}')
        pf.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(pub, text="📤  Publish", command=self.publish,
                      fg_color=PAL["accent"]).pack(anchor="e", padx=14, pady=(0,12))

        # Subscriber
        sub = card(ps); sub.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        ctk.CTkLabel(sub, text="SUBSCRIBER",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        sf = ctk.CTkFrame(sub, fg_color="transparent"); sf.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(sf, text="Topic").grid(row=0,column=0,sticky="e", pady=3, padx=4)
        self.sub_topic = ctk.CTkEntry(sf, width=240); self.sub_topic.insert(0,"sensors/#")
        self.sub_topic.grid(row=0,column=1, sticky="we", pady=3, padx=4)
        ctk.CTkLabel(sf, text="QoS").grid(row=1,column=0,sticky="e", pady=3, padx=4)
        self.sub_qos = ctk.CTkComboBox(sf, values=["0","1","2"], width=80, state="readonly")
        self.sub_qos.set("1"); self.sub_qos.grid(row=1,column=1, sticky="w", pady=3, padx=4)
        sf.grid_columnconfigure(1, weight=1)
        b = ctk.CTkFrame(sub, fg_color="transparent"); b.pack(anchor="e", padx=14, pady=(0,12))
        ctk.CTkButton(b, text="📥  Subscribe", width=120, command=self.subscribe,
                      fg_color=PAL["ok"], hover_color="#0e9d6e").pack(side="left", padx=2)
        ctk.CTkButton(b, text="Unsubscribe", width=110, command=self.unsubscribe,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=2)

        # Log
        log_card = card(scroll); log_card.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(log_card, text="PROTOCOL LOG",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        self.log = LogView(log_card, height=200)
        self.log.pack(fill="both", expand=True, padx=10, pady=(0,10))

    def toggle_connect(self):
        if self.connected: self.disconnect()
        else: self.connect()

    def connect(self):
        if not MQTT_OK:
            messagebox.showerror("Missing","pip install paho-mqtt"); return
        try:
            self.client = mqtt.Client(client_id=self.cid.get(), clean_session=True)
            if self.user.get():
                self.client.username_pw_set(self.user.get(), self.pwd.get())
            if self.tls:
                self.client.tls_set(cert_reqs=ssl.CERT_NONE)
                self.client.tls_insecure_set(True)
                self.log.log("TLS context configured (CERT_NONE, insecure for demo)", "info")
            self.client.on_connect = self._on_conn
            self.client.on_disconnect = self._on_disconn
            self.client.on_message = self._on_msg
            self.client.on_publish = lambda c,u,mid: self.log.log(f"PUBACK mid={mid}", "rx")
            self.client.on_subscribe = lambda c,u,mid,gq: self.log.log(f"SUBACK mid={mid} qos={list(gq)}", "rx")
            self.log.log(f"CONNECT → {self.host.get()}:{self.port.get()}", "tx")
            self.status.set("Connecting…", PAL["warn"])
            self.client.connect_async(self.host.get(), int(self.port.get()), keepalive=60)
            self.client.loop_start()
            self.after(10000, self._connack_timeout)
        except Exception as e:
            self.log.log(f"ERROR {e}", "err")

    def _connack_timeout(self):
        if not self.connected and self.client:
            self.log.log("⚠  No CONNACK received in 10s — broker may be unreachable.", "warn")
            self.log.log("   Try another broker: broker.hivemq.com, broker.emqx.io, public.mqtthq.com", "info")
            self.status.set("No CONNACK — try another broker", PAL["err"])

    def _on_conn(self, c,u,f,rc):
        if rc == 0:
            self.connected = True
            self.after(0, lambda: self.status.set("Connected", PAL["ok"]))
            self.after(0, lambda: self.btn_conn.configure(text="Disconnect"))
            self.log.log("CONNACK rc=0 (Accepted)", "ok")
        else:
            err = {1:"unacceptable protocol",2:"client ID rejected",3:"server unavailable",
                   4:"bad credentials",5:"not authorised"}.get(rc, "unknown")
            self.log.log(f"CONNACK rc={rc} ({err})", "err")
            self.after(0, lambda: self.status.set(f"Failed rc={rc}", PAL["err"]))

    def _on_disconn(self, c,u,rc):
        self.connected = False
        self.after(0, lambda: self.status.set("Disconnected", PAL["err"]))
        self.after(0, lambda: self.btn_conn.configure(text="Connect"))
        self.log.log(f"DISCONNECT rc={rc}", "info")

    def _on_msg(self, c,u,msg):
        try: payload = msg.payload.decode()
        except Exception: payload = msg.payload.hex()
        self.log.log(f"RX  topic={msg.topic} qos={msg.qos} retain={msg.retain} → {payload}", "rx")

    def disconnect(self):
        if self.client:
            try: self.client.loop_stop(); self.client.disconnect()
            except Exception as e: self.log.log(f"err: {e}", "err")

    def publish(self):
        if not self.connected:
            messagebox.showwarning("Not connected","Connect first."); return
        topic = self.pub_topic.get()
        qos = int(self.pub_qos.get())
        msg = self.pub_msg.get("1.0","end").strip()
        info = self.client.publish(topic, msg, qos=qos, retain=self.retain_var.get())
        self.log.log(f"PUBLISH topic={topic} qos={qos} retain={self.retain_var.get()} mid={info.mid}", "tx")

    def subscribe(self):
        if not self.connected:
            messagebox.showwarning("Not connected","Connect first."); return
        topic = self.sub_topic.get(); qos = int(self.sub_qos.get())
        self.client.subscribe(topic, qos)
        self.log.log(f"SUBSCRIBE {topic} qos={qos}", "tx")

    def unsubscribe(self):
        if not self.connected: return
        topic = self.sub_topic.get(); self.client.unsubscribe(topic)
        self.log.log(f"UNSUBSCRIBE {topic}", "tx")


# ══════════════════════════════════════════════════════════════
#  CoAP PAGE  —  full server with live resource management
# ══════════════════════════════════════════════════════════════
class _CoAPResource(resource.Resource if COAP_OK else object):
    """Generic CoAP resource implementing GET/PUT/POST/DELETE."""
    def __init__(self, path, value, logger, ct=0):
        if COAP_OK: super().__init__()
        self.path = path
        self.value = str(value)
        self.log = logger
        self.ct = ct  # 0=text/plain, 50=application/json

    async def render_get(self, request):
        self.log(f"SRV  GET   /{self.path}  → reply '{self.value}'", "rx")
        m = Message(payload=self.value.encode(), code=Code.CONTENT)
        try: m.opt.content_format = self.ct
        except Exception: pass
        return m

    async def render_put(self, request):
        new = request.payload.decode(errors='replace')
        self.log(f"SRV  PUT   /{self.path}  '{self.value}' → '{new}'", "rx")
        self.value = new
        return Message(code=Code.CHANGED, payload=self.value.encode())

    async def render_post(self, request):
        d = request.payload.decode(errors='replace')
        self.log(f"SRV  POST  /{self.path}  data='{d}'", "rx")
        return Message(code=Code.CREATED, payload=f"created:{d}".encode())

    async def render_delete(self, request):
        self.log(f"SRV  DEL   /{self.path}", "rx")
        return Message(code=Code.DELETED)


class CoAPPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=PAL["bg"])
        self.loop = None
        self.site = None
        self.ctx_server = None
        self.running = False
        self.resources = {}     # path -> _CoAPResource
        self.value_labels = {}  # path -> CTkLabel for live value display
        self._build()
        if COAP_OK:
            self._init_defaults()
            self._refresh_list()
            self.after(800, self._poll_values)
        self._start_loop()

    def _init_defaults(self):
        for p, v in [
            ("sensor/temp",     "22.5"),
            ("sensor/humidity", "55"),
            ("sensor/light",    "340"),
            ("actuator/led",    "OFF"),
            ("device/info",     "MCU=ESP32 fw=1.0.3"),
        ]:
            self.resources[p] = _CoAPResource(p, v, self.log.log)

    def _build(self):
        page_header(self, "🌐  CoAP",
                    "Constrained Application Protocol (RFC 7252) — UDP REST for IoT. "
                    "Resources can be added, edited and removed on a live server.")

        if not COAP_OK:
            w = card(self); w.pack(fill="x", padx=20, pady=14)
            ctk.CTkLabel(w, text=f"⚠  aiocoap not installed.\n"
                                  f"Install: {sys.executable} -m pip install aiocoap",
                         text_color=PAL["warn"], justify="left",
                         font=ctk.CTkFont(family="Consolas", size=11)
                         ).pack(padx=14, pady=14)
            return

        scroll = ctk.CTkScrollableFrame(self, fg_color=PAL["bg"])
        scroll.pack(fill="both", expand=True, padx=14, pady=8)

        # ── Server card ──
        srv = card(scroll); srv.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(srv, text="LOCAL CoAP SERVER",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        g = ctk.CTkFrame(srv, fg_color="transparent"); g.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(g, text="Bind").grid(row=0,column=0,sticky="e",padx=4)
        self.srv_host = ctk.CTkEntry(g, width=140); self.srv_host.insert(0,"127.0.0.1")
        self.srv_host.grid(row=0,column=1, padx=4, pady=4)
        ctk.CTkLabel(g, text="Port").grid(row=0,column=2,sticky="e",padx=4)
        self.srv_port = ctk.CTkEntry(g, width=80); self.srv_port.insert(0,"5683")
        self.srv_port.grid(row=0,column=3, padx=4)
        self.srv_status = StatusBadge(g, "Stopped", PAL["muted"])
        self.srv_status.grid(row=0, column=4, padx=10)
        self.btn_srv = ctk.CTkButton(g, text="▶  Start Server", width=140, command=self.toggle_server,
                                     fg_color=PAL["ok"], hover_color="#0e9d6e")
        self.btn_srv.grid(row=0, column=5, padx=4)

        # ── Resources card ──
        rc = card(scroll); rc.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(rc, text="REGISTERED RESOURCES  —  add/edit/remove live (no restart)",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))

        ar = ctk.CTkFrame(rc, fg_color="transparent"); ar.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(ar, text="+ New", text_color=PAL["muted"]).pack(side="left", padx=(0,8))
        self.res_path = ctk.CTkEntry(ar, width=200, placeholder_text="path/like/sensor/temp")
        self.res_path.pack(side="left", padx=4)
        self.res_val = ctk.CTkEntry(ar, width=200, placeholder_text="initial value")
        self.res_val.pack(side="left", padx=4)
        ctk.CTkButton(ar, text="+ Add Resource", width=140, command=self.add_resource,
                      fg_color=PAL["accent"]).pack(side="left", padx=4)
        ctk.CTkButton(ar, text="↻ Rebuild Server", width=140, command=self.rebuild_server,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=4)

        hdr = ctk.CTkFrame(rc, fg_color=PAL["card2"], corner_radius=6)
        hdr.pack(fill="x", padx=14, pady=(8,2))
        ctk.CTkLabel(hdr, text="PATH",   width=220, anchor="w",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(side="left", padx=8, pady=4)
        ctk.CTkLabel(hdr, text="VALUE",  width=260, anchor="w",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(side="left", padx=8)
        ctk.CTkLabel(hdr, text="ACTIONS",                  anchor="w",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(side="left", padx=8)

        self.res_list = ctk.CTkScrollableFrame(rc, fg_color="transparent", height=180)
        self.res_list.pack(fill="x", padx=10, pady=(0,10))

        # ── Client card ──
        cli = card(scroll); cli.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(cli, text="CoAP CLIENT REQUEST",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        g2 = ctk.CTkFrame(cli, fg_color="transparent"); g2.pack(fill="x", padx=14, pady=(0,12))
        g2.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(g2, text="Method").grid(row=0,column=0,sticky="e",padx=4)
        self.method = ctk.CTkComboBox(g2, values=["GET","POST","PUT","DELETE"], width=110, state="readonly")
        self.method.set("GET"); self.method.grid(row=0,column=1, padx=4, pady=4)
        ctk.CTkLabel(g2, text="URI").grid(row=0,column=2,sticky="e",padx=4)
        self.uri = ctk.CTkEntry(g2)
        self.uri.insert(0, "coap://127.0.0.1/sensor/temp")
        self.uri.grid(row=0,column=3, sticky="we", padx=4, pady=4)
        ctk.CTkLabel(g2, text="Payload").grid(row=1,column=0,sticky="ne",padx=4,pady=4)
        self.payload = ctk.CTkTextbox(g2, height=60, fg_color="#0d0d16",
                                      border_width=1, border_color=PAL["border"],
                                      font=ctk.CTkFont(family="Consolas", size=11))
        self.payload.grid(row=1,column=1, columnspan=3, sticky="we", padx=4, pady=4)

        b = ctk.CTkFrame(cli, fg_color="transparent"); b.pack(anchor="e", padx=14, pady=(0,10))
        ctk.CTkButton(b, text="🔍  Discover  /.well-known/core", command=self.discover,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=4)
        ctk.CTkButton(b, text="📤  Send Request", command=self.send_request,
                      fg_color=PAL["accent"]).pack(side="left", padx=4)

        # ── Log ──
        lc = card(scroll); lc.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(lc, text="PROTOCOL LOG",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        self.log = LogView(lc, height=200)
        self.log.pack(fill="both", expand=True, padx=10, pady=(0,10))

    # ───── Resource list UI ─────
    def _refresh_list(self):
        for w in self.res_list.winfo_children(): w.destroy()
        self.value_labels = {}
        if not self.resources:
            ctk.CTkLabel(self.res_list, text="(no resources — add one above)",
                         text_color=PAL["muted"]).pack(pady=14)
            return
        for path in sorted(self.resources.keys()):
            res = self.resources[path]
            row = ctk.CTkFrame(self.res_list, fg_color=PAL["card2"], corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"/{path}", width=220, anchor="w",
                         font=ctk.CTkFont(family="Consolas", size=11),
                         text_color=PAL["accent2"]).pack(side="left", padx=8, pady=4)
            val_lbl = ctk.CTkLabel(row, text=str(res.value), width=260, anchor="w",
                                   font=ctk.CTkFont(family="Consolas", size=11),
                                   text_color=PAL["text"])
            val_lbl.pack(side="left", padx=8)
            self.value_labels[path] = val_lbl
            ctk.CTkButton(row, text="✏  Edit",  width=68, height=26,
                          fg_color=PAL["card"], hover_color="#33334a",
                          command=lambda p=path: self.edit_resource(p)).pack(side="left", padx=2)
            ctk.CTkButton(row, text="🔍 GET",   width=68, height=26,
                          fg_color=PAL["card"], hover_color="#33334a",
                          command=lambda p=path: self.test_get(p)).pack(side="left", padx=2)
            ctk.CTkButton(row, text="🗑  Del",  width=68, height=26,
                          fg_color=PAL["card"], hover_color="#33334a",
                          command=lambda p=path: self.remove_resource(p)).pack(side="left", padx=2)

    def _poll_values(self):
        # Reflect server-side value changes (after PUT etc) into the list
        for p, lbl in list(self.value_labels.items()):
            if p in self.resources:
                cur = str(self.resources[p].value)
                try:
                    if lbl.cget("text") != cur: lbl.configure(text=cur)
                except Exception: pass
        self.after(800, self._poll_values)

    def add_resource(self):
        path = self.res_path.get().strip().strip("/")
        val = self.res_val.get().strip()
        if not path:
            messagebox.showwarning("Path required","Enter a path like 'sensor/temp'"); return
        if path in self.resources:
            messagebox.showwarning("Exists", f"/{path} already exists"); return
        self.resources[path] = _CoAPResource(path, val, self.log.log)
        self.res_path.delete(0,"end"); self.res_val.delete(0,"end")
        self._refresh_list()
        self.log.log(f"Resource added: /{path} = '{val}'", "ok")
        if self.running:
            asyncio.run_coroutine_threadsafe(self._rebuild(), self.loop)

    def remove_resource(self, path):
        if path not in self.resources: return
        del self.resources[path]
        self._refresh_list()
        self.log.log(f"Resource removed: /{path}", "info")
        if self.running:
            asyncio.run_coroutine_threadsafe(self._rebuild(), self.loop)

    def edit_resource(self, path):
        if path not in self.resources: return
        try:
            dlg = ctk.CTkInputDialog(text=f"Set new value for /{path}", title="Edit Resource")
            new_val = dlg.get_input()
        except Exception:
            new_val = None
        if new_val is None: return
        self.resources[path].value = new_val
        if path in self.value_labels: self.value_labels[path].configure(text=new_val)
        self.log.log(f"Resource updated: /{path} = '{new_val}'", "info")

    def test_get(self, path):
        self.uri.delete(0, "end")
        self.uri.insert(0, f"coap://{self.srv_host.get()}/{path}")
        self.method.set("GET")
        self.payload.delete("1.0","end")
        if self.running:
            self.send_request()
        else:
            self.log.log("Server not running — URI filled, click Send after starting.", "warn")

    def rebuild_server(self):
        if not self.running:
            messagebox.showinfo("Not running", "Start the server first."); return
        asyncio.run_coroutine_threadsafe(self._rebuild(), self.loop)

    # ───── Server control ─────
    def _start_loop(self):
        if not COAP_OK: return
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=lambda: (asyncio.set_event_loop(self.loop), self.loop.run_forever()),
                         daemon=True).start()

    def toggle_server(self):
        if not COAP_OK: return
        if self.running:
            asyncio.run_coroutine_threadsafe(self._stop(), self.loop)
        else:
            asyncio.run_coroutine_threadsafe(self._start(), self.loop)

    async def _build_site(self):
        self.site = resource.Site()
        self.site.add_resource(['.well-known','core'],
                          resource.WKCResource(self.site.get_resources_as_linkheader))
        for p, res in self.resources.items():
            self.site.add_resource(p.split('/'), res)

    async def _start(self):
        try:
            await self._build_site()
            self.ctx_server = await Context.create_server_context(
                self.site, bind=(self.srv_host.get(), int(self.srv_port.get())))
            self.running = True
            self.after(0, lambda: self.btn_srv.configure(text="⏹  Stop Server", fg_color=PAL["err"]))
            self.after(0, lambda: self.srv_status.set("Running", PAL["ok"]))
            self.log.log(f"Server started on coap://{self.srv_host.get()}:{self.srv_port.get()}", "ok")
            self.log.log(f"  Serving {len(self.resources)} resource(s) + /.well-known/core:", "info")
            for p in sorted(self.resources.keys()):
                self.log.log(f"    /{p}", "info")
        except Exception as e:
            self.log.log(f"Server error: {e}", "err")
            self.running = False
            self.after(0, lambda: self.srv_status.set("Start failed", PAL["err"]))

    async def _stop(self):
        try:
            if self.ctx_server: await self.ctx_server.shutdown()
        except Exception as e:
            self.log.log(f"Stop err: {e}", "err")
        self.ctx_server = None
        self.running = False
        self.after(0, lambda: self.btn_srv.configure(text="▶  Start Server", fg_color=PAL["ok"]))
        self.after(0, lambda: self.srv_status.set("Stopped", PAL["muted"]))
        self.log.log("Server stopped", "info")

    async def _rebuild(self):
        """Rebuild a running server with current resources (no restart from user)."""
        try:
            if self.ctx_server:
                await self.ctx_server.shutdown()
                await asyncio.sleep(0.15)  # let UDP socket release
            await self._build_site()
            self.ctx_server = await Context.create_server_context(
                self.site, bind=(self.srv_host.get(), int(self.srv_port.get())))
            self.log.log(f"Server rebuilt — now serving {len(self.resources)} resource(s)", "ok")
        except Exception as e:
            self.log.log(f"Rebuild err: {e}", "err")
            self.running = False
            self.after(0, lambda: self.srv_status.set("Stopped (rebuild failed)", PAL["err"]))
            self.after(0, lambda: self.btn_srv.configure(text="▶  Start Server", fg_color=PAL["ok"]))

    # ───── Client ─────
    def send_request(self):
        if not COAP_OK: return
        asyncio.run_coroutine_threadsafe(self._do_req(), self.loop)

    async def _do_req(self):
        m = {"GET":Code.GET,"POST":Code.POST,"PUT":Code.PUT,"DELETE":Code.DELETE}
        try:
            ctx = await Context.create_client_context()
            payload = self.payload.get("1.0","end").strip().encode()
            req = Message(code=m[self.method.get()], uri=self.uri.get(), payload=payload)
            self.log.log(f"TX  {self.method.get():6s} {self.uri.get()}  payload={payload!r}", "tx")
            resp = await asyncio.wait_for(ctx.request(req).response, timeout=10)
            txt = resp.payload.decode(errors='replace')
            self.log.log(f"RX  code={resp.code}  payload={txt!r}", "rx")
            await ctx.shutdown()
        except asyncio.TimeoutError:
            self.log.log("Request timeout (10s) — is the server running?", "err")
        except Exception as e:
            self.log.log(f"Request error: {e}", "err")

    def discover(self):
        if not COAP_OK: return
        host = self.uri.get().split("://",1)[-1].split("/",1)[0]
        async def _disc():
            try:
                ctx = await Context.create_client_context()
                req = Message(code=Code.GET, uri=f"coap://{host}/.well-known/core")
                self.log.log(f"TX  GET    coap://{host}/.well-known/core", "tx")
                resp = await asyncio.wait_for(ctx.request(req).response, timeout=10)
                self.log.log(f"RX  code={resp.code}", "rx")
                for ln in resp.payload.decode(errors='replace').split(","):
                    if ln.strip(): self.log.log(f"     {ln.strip()}", "rx")
                await ctx.shutdown()
            except Exception as e:
                self.log.log(f"Discover err: {e}", "err")
        asyncio.run_coroutine_threadsafe(_disc(), self.loop)


# ══════════════════════════════════════════════════════════════
#  AMQP PAGE  —  Local in-memory simulator + Real RabbitMQ mode
# ══════════════════════════════════════════════════════════════
class LocalAMQPBroker:
    """Tiny in-memory AMQP 0-9-1 simulator. No network needed."""
    def __init__(self):
        self.exchanges = {}            # name -> type
        self.queues    = {}            # name -> deque
        self.bindings  = []            # list of (exch, queue, rkey)
        self.delivery_tag = 0

    def declare_exchange(self, name, etype): self.exchanges[name] = etype
    def declare_queue(self, name):           self.queues.setdefault(name, deque())
    def bind(self, exch, queue, rkey):
        if (exch, queue, rkey) not in self.bindings:
            self.bindings.append((exch, queue, rkey))

    def publish(self, exch, rkey, body, properties=None):
        if exch not in self.exchanges: return []
        etype = self.exchanges[exch]
        out = []
        for (e, q, bk) in self.bindings:
            if e != exch: continue
            if self._matches(etype, bk, rkey) and q in self.queues:
                self.delivery_tag += 1
                self.queues[q].append({
                    "tag": self.delivery_tag, "rkey": rkey,
                    "body": body, "props": properties,
                })
                out.append(q)
        return out

    def _matches(self, etype, bk, rk):
        if etype == "direct":  return bk == rk
        if etype == "fanout":  return True
        if etype == "topic":   return self._tm(bk.split("."), rk.split("."))
        if etype == "headers": return True
        return False

    def _tm(self, pat, key):
        if not pat and not key: return True
        if not pat: return False
        if pat[0] == "#":
            if len(pat) == 1: return True
            for i in range(len(key)+1):
                if self._tm(pat[1:], key[i:]): return True
            return False
        if not key: return False
        if pat[0] in ("*", key[0]): return self._tm(pat[1:], key[1:])
        return False

    def pop(self, queue):
        if queue in self.queues and self.queues[queue]:
            return self.queues[queue].popleft()
        return None

    def purge(self, queue):
        if queue in self.queues:
            n = len(self.queues[queue]); self.queues[queue].clear(); return n
        return 0

    def stats(self):
        return (len(self.exchanges), len(self.queues), len(self.bindings),
                sum(len(q) for q in self.queues.values()))


class AMQPPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=PAL["bg"])
        self.local = LocalAMQPBroker()
        self.conn  = None
        self.ch    = None
        self.consuming = False
        self.mode  = "Local Simulator"
        self._build()

    def _build(self):
        page_header(self, "🐰  AMQP 0-9-1",
                    "Producer / Consumer with full direct/fanout/topic/headers routing. "
                    "Local mode needs no broker; Real mode connects to RabbitMQ.")

        scroll = ctk.CTkScrollableFrame(self, fg_color=PAL["bg"])
        scroll.pack(fill="both", expand=True, padx=14, pady=8)

        # Mode card
        mc = card(scroll); mc.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(mc, text="BROKER MODE", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        mr = ctk.CTkFrame(mc, fg_color="transparent"); mr.pack(fill="x", padx=14, pady=(0,12))
        self.mode_cb = ctk.CTkComboBox(mr, values=["Local Simulator","Real RabbitMQ"], width=180,
                                       state="readonly", command=self._mode_changed)
        self.mode_cb.set("Local Simulator"); self.mode_cb.pack(side="left", padx=4)
        self.mode_lbl = ctk.CTkLabel(mr,
            text="✓ Local in-memory broker is active (always connected — no RabbitMQ needed).",
            text_color=PAL["ok"])
        self.mode_lbl.pack(side="left", padx=12)

        # Real-broker card (shown only when Real mode)
        self.real_card = card(scroll); self.real_card.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(self.real_card, text="REAL BROKER (RabbitMQ)",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        g = ctk.CTkFrame(self.real_card, fg_color="transparent"); g.pack(fill="x", padx=14, pady=(0,10))
        ctk.CTkLabel(g, text="Host").grid(row=0,column=0,sticky="e",padx=4)
        self.host = ctk.CTkEntry(g, width=140); self.host.insert(0,"localhost"); self.host.grid(row=0,column=1,padx=4,pady=4)
        ctk.CTkLabel(g, text="Port").grid(row=0,column=2,sticky="e",padx=4)
        self.port = ctk.CTkEntry(g, width=70); self.port.insert(0,"5672"); self.port.grid(row=0,column=3,padx=4)
        ctk.CTkLabel(g, text="User").grid(row=0,column=4,sticky="e",padx=4)
        self.user = ctk.CTkEntry(g, width=90); self.user.insert(0,"guest"); self.user.grid(row=0,column=5,padx=4)
        ctk.CTkLabel(g, text="Pass").grid(row=0,column=6,sticky="e",padx=4)
        self.pwd = ctk.CTkEntry(g, width=90, show="•"); self.pwd.insert(0,"guest"); self.pwd.grid(row=0,column=7,padx=4)
        ctk.CTkLabel(g, text="VHost").grid(row=0,column=8,sticky="e",padx=4)
        self.vhost = ctk.CTkEntry(g, width=60); self.vhost.insert(0,"/"); self.vhost.grid(row=0,column=9,padx=4)
        self.status = StatusBadge(g, "Disconnected", PAL["err"])
        self.status.grid(row=0, column=10, padx=10)
        self.btn = ctk.CTkButton(g, text="Connect", width=110, command=self.toggle)
        self.btn.grid(row=0, column=11, padx=4)
        ctk.CTkLabel(self.real_card, text="💡  Quick start: docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:management",
                     text_color=PAL["muted"], font=ctk.CTkFont(family="Consolas", size=10)
                     ).pack(anchor="w", padx=14, pady=(0,10))
        self.real_card.pack_forget()  # hidden in local mode

        # Exchange / Queue
        eq = card(scroll); eq.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(eq, text="EXCHANGE & QUEUE", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        g2 = ctk.CTkFrame(eq, fg_color="transparent"); g2.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(g2, text="Exchange").grid(row=0,column=0,sticky="e",padx=4,pady=3)
        self.exch = ctk.CTkEntry(g2, width=180); self.exch.insert(0,"demo.exchange"); self.exch.grid(row=0,column=1,padx=4)
        ctk.CTkLabel(g2, text="Type").grid(row=0,column=2,sticky="e",padx=4)
        self.etype = ctk.CTkComboBox(g2, values=["direct","fanout","topic","headers"], width=110, state="readonly")
        self.etype.set("topic"); self.etype.grid(row=0,column=3,padx=4)
        ctk.CTkButton(g2, text="Declare Exchange", command=self.declare_exch, width=160,
                      fg_color=PAL["accent"]).grid(row=0,column=4,padx=10)
        ctk.CTkLabel(g2, text="Queue").grid(row=1,column=0,sticky="e",padx=4,pady=3)
        self.queue = ctk.CTkEntry(g2, width=180); self.queue.insert(0,"demo.queue"); self.queue.grid(row=1,column=1,padx=4)
        ctk.CTkLabel(g2, text="Bind key").grid(row=1,column=2,sticky="e",padx=4)
        self.rkey = ctk.CTkEntry(g2, width=160); self.rkey.insert(0,"sensors.#"); self.rkey.grid(row=1,column=3,padx=4)
        ctk.CTkButton(g2, text="Declare + Bind Queue", command=self.declare_queue, width=180,
                      fg_color=PAL["accent"]).grid(row=1,column=4,padx=10)

        # Producer / Consumer
        ps = ctk.CTkFrame(scroll, fg_color="transparent"); ps.pack(fill="x", padx=6, pady=6)
        ps.grid_columnconfigure((0,1), weight=1)

        prod = card(ps); prod.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        ctk.CTkLabel(prod, text="PRODUCER", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        pf = ctk.CTkFrame(prod, fg_color="transparent"); pf.pack(fill="x", padx=14, pady=(0,12))
        pf.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(pf, text="Routing key").grid(row=0,column=0,sticky="e",padx=4,pady=3)
        self.pub_rkey = ctk.CTkEntry(pf, width=220); self.pub_rkey.insert(0,"sensors.temp")
        self.pub_rkey.grid(row=0,column=1,sticky="we",padx=4)
        self.persist = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(pf, text="Persistent", variable=self.persist
                        ).grid(row=1,column=1,sticky="w",padx=4)
        ctk.CTkLabel(pf, text="Body").grid(row=2,column=0,sticky="ne",padx=4,pady=3)
        self.msg = ctk.CTkTextbox(pf, height=80, fg_color="#0d0d16",
                                  border_width=1, border_color=PAL["border"],
                                  font=ctk.CTkFont(family="Consolas", size=11))
        self.msg.grid(row=2,column=1,sticky="we",padx=4)
        self.msg.insert("1.0",'{"sensor":"DHT11","value":42}')
        ctk.CTkButton(prod, text="📤  Publish", command=self.publish,
                      fg_color=PAL["accent"]).pack(anchor="e", padx=14, pady=(0,12))

        cons = card(ps); cons.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        ctk.CTkLabel(cons, text="CONSUMER", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        cf = ctk.CTkFrame(cons, fg_color="transparent"); cf.pack(fill="both", expand=True, padx=14, pady=(0,12))
        self.stats_lbl = ctk.CTkLabel(cf,
            text="Stats: 0 exchanges · 0 queues · 0 bindings · 0 msgs",
            text_color=PAL["muted"], font=ctk.CTkFont(family="Consolas", size=10))
        self.stats_lbl.pack(anchor="w", pady=4)
        b = ctk.CTkFrame(cf, fg_color="transparent"); b.pack(anchor="w", pady=8)
        ctk.CTkButton(b, text="▶  Start Consuming", command=self.start_consuming,
                      fg_color=PAL["ok"], hover_color="#0e9d6e").pack(side="left", padx=2)
        ctk.CTkButton(b, text="⏸  Stop", command=self.stop_consuming,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=2)
        ctk.CTkButton(b, text="🗑  Purge Queue", command=self.purge,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=2)

        # Log
        lc = card(scroll); lc.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(lc, text="PROTOCOL LOG", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        self.log = LogView(lc, height=200)
        self.log.pack(fill="both", expand=True, padx=10, pady=(0,10))

        self.after(700, self._update_stats)

    def _mode_changed(self, val):
        self.mode = val
        if val == "Local Simulator":
            self.real_card.pack_forget()
            self.mode_lbl.configure(
                text="✓ Local in-memory broker is active (always connected — no RabbitMQ needed).",
                text_color=PAL["ok"])
            self.log.log("Switched to Local Simulator mode", "info")
        else:
            self.real_card.pack(fill="x", padx=6, pady=6, after=self.mode_cb.master.master)
            self.mode_lbl.configure(
                text="⚠  Real mode — connect to a RabbitMQ broker below.",
                text_color=PAL["warn"])
            self.log.log("Switched to Real RabbitMQ mode", "info")

    def _update_stats(self):
        if self.mode == "Local Simulator":
            e,q,b,m = self.local.stats()
            self.stats_lbl.configure(text=f"Stats: {e} exchanges · {q} queues · {b} bindings · {m} pending msgs")
        self.after(700, self._update_stats)

    def _real(self):
        return self.mode == "Real RabbitMQ"

    def toggle(self):
        if self.conn and self.conn.is_open: self.disconnect()
        else: self.connect()

    def connect(self):
        if not AMQP_OK:
            messagebox.showerror("Missing","pip install pika"); return
        try:
            creds = pika.PlainCredentials(self.user.get(), self.pwd.get())
            params = pika.ConnectionParameters(self.host.get(), int(self.port.get()),
                                               self.vhost.get(), creds,
                                               heartbeat=30, blocked_connection_timeout=10,
                                               socket_timeout=5)
            self.log.log(f"Connecting amqp://{self.host.get()}:{self.port.get()}{self.vhost.get()}...", "tx")
            self.conn = pika.BlockingConnection(params)
            self.ch = self.conn.channel()
            self.status.set("Connected", PAL["ok"])
            self.btn.configure(text="Disconnect")
            self.log.log("Connection.Tune ok, channel.open ok", "ok")
        except Exception as e:
            self.log.log(f"Connect error: {type(e).__name__}: {e or '(no message — broker likely down or unreachable)'}", "err")
            self.log.log("→ Switch Mode to 'Local Simulator' if you don't have RabbitMQ running.", "warn")
            self.status.set("Connect failed", PAL["err"])

    def disconnect(self):
        self.stop_consuming()
        try:
            if self.conn and self.conn.is_open: self.conn.close()
        except Exception: pass
        self.status.set("Disconnected", PAL["err"])
        self.btn.configure(text="Connect")
        self.log.log("Disconnected", "info")

    def declare_exch(self):
        name, etype = self.exch.get(), self.etype.get()
        if self._real():
            if not self.ch: messagebox.showwarning("Not connected","Connect first."); return
            try:
                self.ch.exchange_declare(exchange=name, exchange_type=etype, durable=False)
                self.log.log(f"exchange.declare ok: {name} ({etype})", "tx")
            except Exception as e: self.log.log(f"declare err: {e}", "err")
        else:
            self.local.declare_exchange(name, etype)
            self.log.log(f"[local] exchange.declare ok: {name} ({etype})", "tx")

    def declare_queue(self):
        q, e, rk = self.queue.get(), self.exch.get(), self.rkey.get()
        if self._real():
            if not self.ch: messagebox.showwarning("Not connected","Connect first."); return
            try:
                self.ch.queue_declare(queue=q, durable=False, auto_delete=False)
                self.ch.queue_bind(exchange=e, queue=q, routing_key=rk)
                self.log.log(f"queue.declare+bind ok: {q} ← {e} key={rk}", "tx")
            except Exception as ex: self.log.log(f"declare err: {ex}", "err")
        else:
            self.local.declare_queue(q)
            self.local.bind(e, q, rk)
            self.log.log(f"[local] queue.declare+bind ok: {q} ← {e} key={rk}", "tx")

    def publish(self):
        body = self.msg.get("1.0","end").strip().encode()
        if self._real():
            if not self.ch: messagebox.showwarning("Not connected","Connect first."); return
            try:
                props = pika.BasicProperties(content_type="application/json",
                                             delivery_mode=2 if self.persist.get() else 1,
                                             timestamp=int(datetime.now().timestamp()))
                self.ch.basic_publish(exchange=self.exch.get(), routing_key=self.pub_rkey.get(),
                                      body=body, properties=props)
                self.log.log(f"basic.publish exch={self.exch.get()} key={self.pub_rkey.get()} body={body.decode(errors='replace')}", "tx")
            except Exception as e: self.log.log(f"publish err: {e}", "err")
        else:
            delivered = self.local.publish(self.exch.get(), self.pub_rkey.get(), body,
                                           {"persistent": self.persist.get()})
            self.log.log(f"[local] basic.publish exch={self.exch.get()} key={self.pub_rkey.get()} body={body.decode(errors='replace')}", "tx")
            if delivered:
                self.log.log(f"[local] → delivered to: {', '.join(delivered)}", "ok")
            else:
                self.log.log(f"[local] → no matching binding (message dropped)", "warn")

    def purge(self):
        if self._real():
            if not self.ch: return
            try:
                r = self.ch.queue_purge(self.queue.get())
                self.log.log(f"queue.purge ok ({r.method.message_count} msgs)", "tx")
            except Exception as e: self.log.log(f"purge err: {e}", "err")
        else:
            n = self.local.purge(self.queue.get())
            self.log.log(f"[local] queue.purge ok ({n} msgs)", "tx")

    def start_consuming(self):
        if self.consuming: return
        if self._real():
            if not self.ch: messagebox.showwarning("Not connected","Connect first."); return
            try:
                def cb(ch, method, props, body):
                    self.log.log(f"basic.deliver tag={method.delivery_tag} key={method.routing_key} body={body.decode(errors='replace')}", "rx")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                self.ch.basic_consume(queue=self.queue.get(), on_message_callback=cb, auto_ack=False)
                self.consuming = True
                self.log.log(f"basic.consume started on '{self.queue.get()}'", "tx")
                self._poll_real()
            except Exception as e: self.log.log(f"consume err: {e}", "err")
        else:
            self.consuming = True
            self.log.log(f"[local] basic.consume started on '{self.queue.get()}'", "tx")
            self._poll_local()

    def _poll_real(self):
        if not self.consuming or not self.conn or not self.conn.is_open: return
        try: self.conn.process_data_events(time_limit=0)
        except Exception as e:
            self.log.log(f"poll err: {e}", "err"); self.consuming=False; return
        self.after(100, self._poll_real)

    def _poll_local(self):
        if not self.consuming: return
        m = self.local.pop(self.queue.get())
        if m:
            self.log.log(f"[local] basic.deliver tag={m['tag']} key={m['rkey']} body={m['body'].decode(errors='replace')}", "rx")
        self.after(150, self._poll_local)

    def stop_consuming(self):
        if not self.consuming: return
        self.consuming = False
        try:
            if self._real() and self.ch: self.ch.stop_consuming()
            self.log.log("basic.cancel sent", "tx")
        except Exception: pass


# ══════════════════════════════════════════════════════════════
#  NFC PAGE
# ══════════════════════════════════════════════════════════════
class NFCPage(ctk.CTkFrame):
    TAG_CAPS = {
        "Type 1 (Topaz/Jewel)": 96,
        "Type 2 (NTAG213)":     137,
        "Type 2 (NTAG215)":     504,
        "Type 2 (NTAG216)":     888,
        "Type 3 (FeliCa)":      1024,
        "Type 4 (DESFire)":     8192,
        "Type 5 (ISO 15693)":   256,
    }
    URI_PREFIXES = [
        "", "http://www.", "https://www.", "http://", "https://",
        "tel:", "mailto:", "ftp://anonymous:anonymous@", "ftp://ftp.",
        "ftps://", "sftp://", "smb://", "nfs://", "ftp://", "dav://",
        "news:", "telnet://", "imap:", "rtsp://", "urn:", "pop:",
        "sip:", "sips:", "tftp:", "btspp://", "btl2cap://", "btgoep://",
        "tcpobex://", "irdaobex://", "file://", "urn:epc:id:",
        "urn:epc:tag:", "urn:epc:pat:", "urn:epc:raw:", "urn:epc:", "urn:nfc:"
    ]

    def __init__(self, parent):
        super().__init__(parent, fg_color=PAL["bg"])
        self.tag = {
            "uid":      ":".join(["04"] + [f"{random.randint(0,255):02X}" for _ in range(6)]),
            "type":     "Type 2 (NTAG215)",
            "capacity": 504,
            "records":  [],
            "locked":   False,
        }
        self._build()

    def _build(self):
        page_header(self, "📱  NFC", "NDEF tag simulator — no hardware needed")

        scroll = ctk.CTkScrollableFrame(self, fg_color=PAL["bg"])
        scroll.pack(fill="both", expand=True, padx=14, pady=8)

        # Tag info card
        c = card(scroll); c.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(c, text="VIRTUAL NFC TAG", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        g = ctk.CTkFrame(c, fg_color="transparent"); g.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(g, text="UID").grid(row=0,column=0,sticky="e",padx=4,pady=4)
        self.uid_lbl = ctk.CTkLabel(g, text=self.tag["uid"],
                                    font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
                                    text_color=PAL["accent2"])
        self.uid_lbl.grid(row=0,column=1,sticky="w",padx=4)
        ctk.CTkButton(g, text="↻ UID", width=70, command=self.regen_uid,
                      fg_color=PAL["card2"], hover_color="#33334a").grid(row=0,column=2,padx=8)
        ctk.CTkLabel(g, text="Type").grid(row=0,column=3,sticky="e",padx=4)
        self.type_cb = ctk.CTkComboBox(g, values=list(self.TAG_CAPS.keys()), width=200,
                                       state="readonly", command=lambda _: self._set_type())
        self.type_cb.set(self.tag["type"]); self.type_cb.grid(row=0,column=4,padx=4)
        ctk.CTkLabel(g, text="Capacity").grid(row=0,column=5,sticky="e",padx=8)
        self.cap_lbl = ctk.CTkLabel(g, text=f"{self.tag['capacity']} B")
        self.cap_lbl.grid(row=0,column=6,sticky="w",padx=4)
        self.lock_lbl = ctk.CTkLabel(g, text="🔓 Unlocked", text_color=PAL["ok"])
        self.lock_lbl.grid(row=0,column=7,padx=12)

        # Record builder
        rb = card(scroll); rb.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(rb, text="WRITE NDEF RECORD", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        g2 = ctk.CTkFrame(rb, fg_color="transparent"); g2.pack(fill="x", padx=14, pady=(0,12))
        g2.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(g2, text="Record type").grid(row=0,column=0,sticky="e",padx=4,pady=4)
        self.rec_type = ctk.CTkComboBox(g2,
                values=["Text","URI","WiFi","SmartPoster","vCard","MIME","External"],
                width=160, state="readonly")
        self.rec_type.set("Text"); self.rec_type.grid(row=0,column=1,padx=4)
        ctk.CTkLabel(g2, text="Lang / MIME").grid(row=0,column=2,sticky="e",padx=4)
        self.rec_lang = ctk.CTkEntry(g2, width=160); self.rec_lang.insert(0,"en")
        self.rec_lang.grid(row=0,column=3,sticky="we",padx=4)
        ctk.CTkLabel(g2, text="Content").grid(row=1,column=0,sticky="ne",padx=4,pady=4)
        self.rec_content = ctk.CTkTextbox(g2, height=70, fg_color="#0d0d16",
                                          border_width=1, border_color=PAL["border"],
                                          font=ctk.CTkFont(family="Consolas", size=11))
        self.rec_content.grid(row=1,column=1,columnspan=3,sticky="we",padx=4,pady=4)
        self.rec_content.insert("1.0","Hello NFC!")

        bb = ctk.CTkFrame(rb, fg_color="transparent"); bb.pack(anchor="w", padx=14, pady=(0,12))
        ctk.CTkButton(bb, text="✏️  Write", command=self.write_record, fg_color=PAL["accent"]
                      ).pack(side="left", padx=2)
        ctk.CTkButton(bb, text="🗑  Erase All", command=self.erase,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=2)
        ctk.CTkButton(bb, text="🔒 Toggle Lock", command=self.toggle_lock,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=2)
        ctk.CTkButton(bb, text="💾  Export .json", command=self.export_json,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=2)
        ctk.CTkButton(bb, text="💾  Export .bin", command=self.export_bin,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=2)

        # Tag dump
        dc = card(scroll); dc.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(dc, text="TAG MEMORY / READ", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", padx=14, pady=(10,4))
        tb = ctk.CTkFrame(dc, fg_color="transparent"); tb.pack(fill="x", padx=14)
        ctk.CTkButton(tb, text="📖  Read Tag", command=self.refresh,
                      fg_color=PAL["accent"]).pack(side="left", padx=2)
        ctk.CTkButton(tb, text="🧬  Hex Dump", command=self.show_hex,
                      fg_color=PAL["card2"], hover_color="#33334a").pack(side="left", padx=2)
        self.dump = ctk.CTkTextbox(dc, fg_color="#0d0d16", text_color=PAL["text"],
                                   font=ctk.CTkFont(family="Consolas", size=11),
                                   border_width=1, border_color=PAL["border"], corner_radius=8)
        self.dump.pack(fill="both", expand=True, padx=14, pady=(8,12))
        self.refresh()

    def _set_type(self):
        t = self.type_cb.get(); self.tag["type"] = t
        self.tag["capacity"] = self.TAG_CAPS[t]
        self.cap_lbl.configure(text=f"{self.tag['capacity']} B")
        self.refresh()

    def regen_uid(self):
        self.tag["uid"] = ":".join(["04"] + [f"{random.randint(0,255):02X}" for _ in range(6)])
        self.uid_lbl.configure(text=self.tag["uid"]); self.refresh()

    def toggle_lock(self):
        self.tag["locked"] = not self.tag["locked"]
        if self.tag["locked"]:
            self.lock_lbl.configure(text="🔒 Locked (read-only)", text_color=PAL["err"])
        else:
            self.lock_lbl.configure(text="🔓 Unlocked", text_color=PAL["ok"])

    def erase(self):
        if self.tag["locked"]:
            messagebox.showwarning("Locked","Tag is locked."); return
        self.tag["records"] = []; self.refresh()

    def write_record(self):
        if self.tag["locked"]:
            messagebox.showwarning("Locked","Tag is locked."); return
        rtype = self.rec_type.get()
        content = self.rec_content.get("1.0","end").strip()
        lang = self.rec_lang.get().strip() or "en"
        try:
            payload = self._encode_ndef(rtype, content, lang)
        except Exception as e:
            messagebox.showerror("Encode error", str(e)); return
        used = sum(len(bytes.fromhex(r["hex"])) for r in self.tag["records"])
        if used + len(payload) > self.tag["capacity"]:
            messagebox.showerror("Out of space",
                f"Need {len(payload)}B, free {self.tag['capacity']-used}B"); return
        self.tag["records"].append({"type":rtype, "lang_or_mime":lang,
                                    "content":content, "hex":payload.hex().upper()})
        self.refresh()

    def _encode_ndef(self, rtype, content, lang):
        if NDEF_OK and rtype in ("Text","URI"):
            try:
                if rtype == "Text":
                    rec = ndef.TextRecord(content, language=lang)
                else:
                    rec = ndef.UriRecord(content)
                return b''.join(ndef.message_encoder([rec]))
            except Exception: pass
        if rtype == "Text":
            lang_b = lang.encode('ascii')
            payload = bytes([len(lang_b)]) + lang_b + content.encode('utf-8')
            return bytes([0xD1, 1, len(payload)]) + b'T' + payload
        elif rtype == "URI":
            idx = 0
            for i, p in enumerate(self.URI_PREFIXES):
                if p and content.startswith(p):
                    idx = i; content = content[len(p):]; break
            payload = bytes([idx]) + content.encode('utf-8')
            return bytes([0xD1, 1, len(payload)]) + b'U' + payload
        elif rtype == "WiFi":
            mime = b'application/vnd.wfa.wsc'; payload = content.encode('utf-8')
            return bytes([0xD2, len(mime), len(payload)]) + mime + payload
        elif rtype == "SmartPoster":
            t = b'Sp'; payload = content.encode('utf-8')
            return bytes([0xD1, len(t), len(payload)]) + t + payload
        elif rtype == "vCard":
            mime = b'text/vcard'; payload = content.encode('utf-8')
            return bytes([0xD2, len(mime), len(payload)]) + mime + payload
        elif rtype == "MIME":
            mime = (lang or "application/octet-stream").encode('utf-8')
            payload = content.encode('utf-8')
            return bytes([0xD2, len(mime), len(payload)]) + mime + payload
        else:
            t = (lang or "example.com:demo").encode('utf-8')
            payload = content.encode('utf-8')
            return bytes([0xD4, len(t), len(payload)]) + t + payload

    def refresh(self):
        self.dump.delete("1.0","end")
        used = sum(len(bytes.fromhex(r["hex"])) for r in self.tag["records"])
        cap = self.tag["capacity"]; pct = used*100//max(cap,1)
        self.dump.insert("end", "═══════════ NFC TAG ═══════════\n")
        self.dump.insert("end", f"UID       : {self.tag['uid']}\n")
        self.dump.insert("end", f"Type      : {self.tag['type']}\n")
        self.dump.insert("end", f"Capacity  : {cap} bytes\n")
        self.dump.insert("end", f"Used      : {used} bytes ({pct}%)\n")
        self.dump.insert("end", f"Locked    : {'YES' if self.tag['locked'] else 'NO'}\n")
        self.dump.insert("end", f"Records   : {len(self.tag['records'])}\n\n")
        for i, r in enumerate(self.tag["records"], 1):
            self.dump.insert("end", f"── Record {i} ──\n")
            self.dump.insert("end", f"  Type       : {r['type']}\n")
            self.dump.insert("end", f"  Lang/MIME  : {r['lang_or_mime']}\n")
            self.dump.insert("end", f"  Content    : {r['content']}\n")
            self.dump.insert("end", f"  Size       : {len(bytes.fromhex(r['hex']))} bytes\n")
            self.dump.insert("end", f"  NDEF (hex) : {r['hex']}\n\n")

    def show_hex(self):
        ab = b''.join(bytes.fromhex(r["hex"]) for r in self.tag["records"])
        self.dump.delete("1.0","end")
        self.dump.insert("end", "═══════════ RAW MEMORY DUMP ═══════════\n")
        self.dump.insert("end", f"UID: {self.tag['uid'].replace(':','')}\n")
        self.dump.insert("end", f"NDEF bytes ({len(ab)} total):\n\n")
        if not ab:
            self.dump.insert("end","(empty)\n"); return
        hexstr = ab.hex().upper()
        for i in range(0, len(hexstr), 32):
            row = hexstr[i:i+32]
            spaced = ' '.join(row[j:j+2] for j in range(0,len(row),2))
            ascii_part = ''.join(chr(int(row[j:j+2],16)) if 32 <= int(row[j:j+2],16) < 127 else '.'
                                 for j in range(0,len(row),2))
            self.dump.insert("end", f"  {i//2:04X}  {spaced:<47}  {ascii_part}\n")

    def export_json(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if not p: return
        with open(p,"w") as f: json.dump(self.tag, f, indent=2)
        messagebox.showinfo("Saved", f"Tag exported to {p}")

    def export_bin(self):
        p = filedialog.asksaveasfilename(defaultextension=".bin", filetypes=[("Binary","*.bin")])
        if not p: return
        data = b''.join(bytes.fromhex(r["hex"]) for r in self.tag["records"])
        with open(p,"wb") as f: f.write(data)
        messagebox.showinfo("Saved", f"{len(data)} bytes written to {p}")


# ══════════════════════════════════════════════════════════════
#  ZIGBEE PAGE  —  IEEE 802.15.4 + ZCL (Zigbee Cluster Library) simulator
# ══════════════════════════════════════════════════════════════
class ZigbeePage(ctk.CTkFrame):
    CLUSTERS = {
        0x0000: "Basic",
        0x0006: "On/Off",
        0x0008: "Level Control",
        0x0202: "Fan Control",
        0x0300: "Color Control",
        0x0402: "Temperature Measurement",
        0x0403: "Pressure Measurement",
        0x0405: "Relative Humidity",
        0x0406: "Occupancy Sensing",
        0x0500: "IAS Zone",
        0x0702: "Metering",
    }
    COMMANDS = {
        0x0006: {0x00:"Off", 0x01:"On", 0x02:"Toggle"},
        0x0008: {0x00:"Move to Level", 0x04:"Move to Level w/ On/Off", 0x05:"Stop"},
        0x0402: {0x00:"Read Attribute (Temp)"},
        0x0405: {0x00:"Read Attribute (Humidity)"},
        0x0500: {0x00:"Zone Status Change Notification"},
    }
    TEMPLATES = {
        "Coordinator (ZC)":       {"role":"ZC",  "clusters":[0x0000]},
        "Router (ZR)":            {"role":"ZR",  "clusters":[0x0000]},
        "Smart Light":            {"role":"ZED", "clusters":[0x0000,0x0006,0x0008,0x0300]},
        "Smart Plug":             {"role":"ZED", "clusters":[0x0000,0x0006,0x0702]},
        "Dimmer Switch":          {"role":"ZED", "clusters":[0x0000,0x0006,0x0008]},
        "Temperature Sensor":     {"role":"ZED", "clusters":[0x0000,0x0402]},
        "Humidity Sensor":        {"role":"ZED", "clusters":[0x0000,0x0405]},
        "Motion Sensor":          {"role":"ZED", "clusters":[0x0000,0x0406,0x0500]},
        "Door/Window Sensor":     {"role":"ZED", "clusters":[0x0000,0x0500]},
        "Smart Meter":            {"role":"ZED", "clusters":[0x0000,0x0702]},
    }

    def __init__(self, parent):
        super().__init__(parent, fg_color=PAL["bg"])
        self.pan_id  = 0x1A62
        self.channel = 11
        self.nwk_key = "5A:69:67:42:65:65:41:6C:6C:69:61:6E:63:65:30:39"
        self.ext_pan = "00:12:4B:00:" + ":".join(f"{random.randint(0,255):02X}" for _ in range(4))
        self.running = False
        self.devices = []  # list of dicts
        self.seq_num = 0
        self._build()
        # Auto-add coordinator
        self._join_device("Coordinator (ZC)", "Coordinator", short=0x0000)
        self._refresh_devices()

    def _build(self):
        page_header(self, "🐝  Zigbee",
                    "IEEE 802.15.4 (2.4 GHz) + Zigbee Cluster Library (ZCL). Star/mesh topology.")

        scroll = ctk.CTkScrollableFrame(self, fg_color=PAL["bg"])
        scroll.pack(fill="both", expand=True, padx=14, pady=8)

        # Network params
        nc = card(scroll); nc.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(nc, text="NETWORK PARAMETERS",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        g = ctk.CTkFrame(nc, fg_color="transparent"); g.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(g, text="PAN ID").grid(row=0,column=0,sticky="e",padx=4)
        self.pan_lbl = ctk.CTkLabel(g, text=f"0x{self.pan_id:04X}",
                                    font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                                    text_color=PAL["accent2"])
        self.pan_lbl.grid(row=0,column=1,sticky="w",padx=4,pady=4)
        ctk.CTkLabel(g, text="Channel").grid(row=0,column=2,sticky="e",padx=8)
        self.ch_cb = ctk.CTkComboBox(g, values=[str(c) for c in range(11,27)], width=70, state="readonly")
        self.ch_cb.set("11"); self.ch_cb.grid(row=0,column=3,padx=4)
        ctk.CTkLabel(g, text="Ext PAN").grid(row=0,column=4,sticky="e",padx=8)
        self.ext_lbl = ctk.CTkLabel(g, text=self.ext_pan,
                                    font=ctk.CTkFont(family="Consolas", size=10),
                                    text_color=PAL["accent2"])
        self.ext_lbl.grid(row=0,column=5,sticky="w",padx=4)
        ctk.CTkButton(g, text="↻ Regenerate IDs", command=self.regen_ids, width=140,
                      fg_color=PAL["card2"], hover_color="#33334a").grid(row=0,column=6,padx=10)
        ctk.CTkLabel(g, text="NWK Key (AES-128)").grid(row=1,column=0,sticky="e",padx=4,pady=4,columnspan=2)
        ctk.CTkLabel(g, text=self.nwk_key,
                     font=ctk.CTkFont(family="Consolas", size=10),
                     text_color=PAL["muted"]).grid(row=1,column=2,columnspan=4,sticky="w",padx=4)
        self.net_status = StatusBadge(g, "Network Down", PAL["err"])
        self.net_status.grid(row=1,column=6,padx=10)
        self.btn_net = ctk.CTkButton(g, text="▶  Form Network", command=self.toggle_network,
                                     fg_color=PAL["ok"], hover_color="#0e9d6e", width=160)
        self.btn_net.grid(row=2, column=0, columnspan=2, padx=4, pady=8)
        self.btn_join = ctk.CTkButton(g, text="📡  Permit Join (60s)", command=self.permit_join,
                                      fg_color=PAL["card2"], hover_color="#33334a", width=170)
        self.btn_join.grid(row=2, column=2, columnspan=2, padx=4, pady=8)

        # Devices
        dc = card(scroll); dc.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(dc, text="DEVICES ON NETWORK",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        ar = ctk.CTkFrame(dc, fg_color="transparent"); ar.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(ar, text="+ Join", text_color=PAL["muted"]).pack(side="left", padx=(0,8))
        self.dev_type = ctk.CTkComboBox(ar, values=list(self.TEMPLATES.keys()), width=200, state="readonly")
        self.dev_type.set("Smart Light"); self.dev_type.pack(side="left", padx=4)
        self.dev_name = ctk.CTkEntry(ar, width=180, placeholder_text="device name (e.g. Kitchen Light)")
        self.dev_name.pack(side="left", padx=4)
        ctk.CTkButton(ar, text="+ Join Device", width=130, command=self.join_device,
                      fg_color=PAL["accent"]).pack(side="left", padx=4)

        hdr = ctk.CTkFrame(dc, fg_color=PAL["card2"], corner_radius=6)
        hdr.pack(fill="x", padx=14, pady=(8,2))
        for label, w in [("ADDR",70),("NAME",170),("TYPE",170),("ROLE",60),("LQI",50),("STATE",90)]:
            ctk.CTkLabel(hdr, text=label, width=w, anchor="w",
                         font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                         ).pack(side="left", padx=6, pady=4)
        ctk.CTkLabel(hdr, text="ACTIONS", anchor="w",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(side="left", padx=6, pady=4)
        self.dev_list = ctk.CTkScrollableFrame(dc, fg_color="transparent", height=180)
        self.dev_list.pack(fill="x", padx=10, pady=(0,10))

        # Send ZCL command
        sc = card(scroll); sc.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(sc, text="SEND ZCL COMMAND",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        sf = ctk.CTkFrame(sc, fg_color="transparent"); sf.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(sf, text="To Device").grid(row=0,column=0,sticky="e",padx=4)
        self.cmd_dst = ctk.CTkComboBox(sf, values=["(none)"], width=200, state="readonly")
        self.cmd_dst.grid(row=0,column=1,padx=4,pady=4)
        ctk.CTkLabel(sf, text="Cluster").grid(row=0,column=2,sticky="e",padx=4)
        self.cmd_cluster = ctk.CTkComboBox(sf, values=[f"0x{c:04X} {n}" for c,n in self.CLUSTERS.items()],
                                            width=240, state="readonly",
                                            command=lambda v: self._update_cmds())
        self.cmd_cluster.set("0x0006 On/Off"); self.cmd_cluster.grid(row=0,column=3,padx=4)
        ctk.CTkLabel(sf, text="Command").grid(row=0,column=4,sticky="e",padx=4)
        self.cmd_id = ctk.CTkComboBox(sf, values=["0x00 Off","0x01 On","0x02 Toggle"], width=180, state="readonly")
        self.cmd_id.set("0x02 Toggle"); self.cmd_id.grid(row=0,column=5,padx=4)
        ctk.CTkButton(sc, text="📤  Send ZCL", command=self.send_zcl,
                      fg_color=PAL["accent"]).pack(anchor="e", padx=14, pady=(0,12))

        # Log
        lc = card(scroll); lc.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(lc, text="PROTOCOL LOG",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        self.log = LogView(lc, height=180)
        self.log.pack(fill="both", expand=True, padx=10, pady=(0,10))

    def _update_cmds(self):
        try:
            cid = int(self.cmd_cluster.get().split()[0], 16)
            cmds = self.COMMANDS.get(cid, {0x00: "Read Attribute"})
            self.cmd_id.configure(values=[f"0x{c:02X} {n}" for c,n in cmds.items()])
            first = list(cmds.keys())[0]
            self.cmd_id.set(f"0x{first:02X} {cmds[first]}")
        except Exception: pass

    def regen_ids(self):
        self.pan_id = random.randint(0x0001, 0xFFFE)
        self.ext_pan = "00:12:4B:00:" + ":".join(f"{random.randint(0,255):02X}" for _ in range(4))
        self.pan_lbl.configure(text=f"0x{self.pan_id:04X}")
        self.ext_lbl.configure(text=self.ext_pan)
        self.log.log(f"New PAN ID = 0x{self.pan_id:04X}, Ext PAN = {self.ext_pan}", "info")

    def toggle_network(self):
        if self.running:
            self.running = False
            self.btn_net.configure(text="▶  Form Network", fg_color=PAL["ok"])
            self.net_status.set("Network Down", PAL["err"])
            self.log.log(f"Network 0x{self.pan_id:04X} stopped", "info")
        else:
            self.running = True
            self.channel = int(self.ch_cb.get())
            self.btn_net.configure(text="⏹  Stop Network", fg_color=PAL["err"])
            self.net_status.set(f"Operational  ch={self.channel}", PAL["ok"])
            self.log.log(f"Network formed: PAN=0x{self.pan_id:04X} channel={self.channel} 2.4 GHz", "ok")
            self.log.log(f"  Security: AES-128-CCM*  key={self.nwk_key[:23]}...", "info")

    def permit_join(self):
        if not self.running:
            messagebox.showwarning("Network down","Form network first."); return
        self.log.log("MgmtPermitJoiningRequest broadcast (duration=60s)", "tx")
        self.log.log("  Coordinator now accepts new End Devices for 60 seconds", "info")

    def join_device(self):
        if not self.running:
            messagebox.showwarning("Network down","Form network first."); return
        t = self.dev_type.get()
        n = self.dev_name.get().strip() or t
        if t == "Coordinator (ZC)":
            messagebox.showwarning("Already exists","Only one coordinator per network."); return
        self._join_device(t, n)
        self.dev_name.delete(0,"end")
        self._refresh_devices()

    def _join_device(self, dev_type, name, short=None):
        tmpl = self.TEMPLATES[dev_type]
        if short is None:
            short = random.randint(0x0001, 0xFFFE)
            while any(d["short"] == short for d in self.devices):
                short = random.randint(0x0001, 0xFFFE)
        ieee = ":".join(f"{random.randint(0,255):02X}" for _ in range(8))
        state = "ON" if 0x0006 in tmpl["clusters"] else \
                f"{20+random.randint(0,8)}°C" if 0x0402 in tmpl["clusters"] else \
                f"{40+random.randint(0,30)}%" if 0x0405 in tmpl["clusters"] else \
                "OPEN" if 0x0500 in tmpl["clusters"] else "—"
        dev = {
            "short": short, "ieee": ieee, "name": name, "type": dev_type,
            "role": tmpl["role"], "clusters": tmpl["clusters"],
            "lqi": random.randint(180, 255), "state": state,
        }
        self.devices.append(dev)
        if dev_type != "Coordinator (ZC)":
            self.log.log(f"AssociationRequest from {ieee} → granted short=0x{short:04X}", "rx")
            self.log.log(f"  Device joined: '{name}' ({dev_type}) lqi={dev['lqi']}", "ok")
            self.log.log(f"  Clusters: {[f'0x{c:04X} {self.CLUSTERS[c]}' for c in tmpl['clusters']]}", "info")

    def _refresh_devices(self):
        for w in self.dev_list.winfo_children(): w.destroy()
        if not self.devices:
            ctk.CTkLabel(self.dev_list, text="(no devices)", text_color=PAL["muted"]).pack(pady=14)
            return
        targets = []
        for d in self.devices:
            row = ctk.CTkFrame(self.dev_list, fg_color=PAL["card2"], corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"0x{d['short']:04X}", width=70, anchor="w",
                         font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                         text_color=PAL["accent2"]).pack(side="left", padx=6, pady=4)
            ctk.CTkLabel(row, text=d["name"], width=170, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=PAL["text"]
                         ).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=d["type"], width=170, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=PAL["muted"]
                         ).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=d["role"], width=60, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=PAL["ok"] if d["role"]=="ZC" else PAL["text"]
                         ).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=str(d["lqi"]) if d["role"]!="ZC" else "—", width=50, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=PAL["muted"]
                         ).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=d["state"], width=90, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"), text_color=PAL["accent2"]
                         ).pack(side="left", padx=6)
            if d["role"] != "ZC":
                ctk.CTkButton(row, text="🗑 Leave", width=80, height=24,
                              fg_color=PAL["card"], hover_color="#33334a",
                              command=lambda s=d["short"]: self.leave_device(s)).pack(side="left", padx=2)
                targets.append(f"0x{d['short']:04X}  {d['name']}")
        if targets:
            self.cmd_dst.configure(values=targets)
            self.cmd_dst.set(targets[0])
        else:
            self.cmd_dst.configure(values=["(no devices)"])
            self.cmd_dst.set("(no devices)")

    def leave_device(self, short):
        self.devices = [d for d in self.devices if d["short"] != short]
        self.log.log(f"NWK leave: 0x{short:04X} removed from network", "info")
        self._refresh_devices()

    def send_zcl(self):
        if not self.running:
            messagebox.showwarning("Network down","Form network first."); return
        dst_text = self.cmd_dst.get()
        if dst_text.startswith("("):
            messagebox.showwarning("No target","Add an end device first."); return
        try:
            dst = int(dst_text.split()[0], 16)
            cid = int(self.cmd_cluster.get().split()[0], 16)
            cmd = int(self.cmd_id.get().split()[0], 16)
        except Exception as e:
            messagebox.showerror("Parse err", str(e)); return

        self.seq_num = (self.seq_num + 1) & 0xFF
        # Build pseudo-frame
        zcl_hdr = f"FC=0x01 SEQ=0x{self.seq_num:02X} CMD=0x{cmd:02X}"
        frame = (f"APS: src=0x0000 dst=0x{dst:04X} cluster=0x{cid:04X} "
                 f"profile=0x0104  |  ZCL: {zcl_hdr}")
        self.log.log(f"TX  ZCL → 0x{dst:04X}  {self.CLUSTERS.get(cid,'?')}  "
                     f"{self.COMMANDS.get(cid,{}).get(cmd,'?')}", "tx")
        self.log.log(f"    {frame}", "info")

        # Update target state
        for d in self.devices:
            if d["short"] != dst: continue
            if cid == 0x0006:  # On/Off
                if cmd == 0x00: d["state"] = "OFF"
                elif cmd == 0x01: d["state"] = "ON"
                elif cmd == 0x02: d["state"] = "OFF" if d["state"]=="ON" else "ON"
                self.log.log(f"RX  Default Response from 0x{dst:04X}: SUCCESS  state={d['state']}", "rx")
            elif cid == 0x0402:
                t = 20 + random.uniform(-2,8); d["state"] = f"{t:.1f}°C"
                self.log.log(f"RX  ReadAttrResp from 0x{dst:04X}: MeasuredValue={int(t*100)} (0x{int(t*100):04X})", "rx")
            elif cid == 0x0405:
                h = 40 + random.uniform(0,30); d["state"] = f"{h:.0f}%"
                self.log.log(f"RX  ReadAttrResp from 0x{dst:04X}: MeasuredValue={int(h*100)}", "rx")
            else:
                self.log.log(f"RX  Default Response from 0x{dst:04X}: SUCCESS", "rx")
            break
        self._refresh_devices()


# ══════════════════════════════════════════════════════════════
#  Z-WAVE PAGE  —  Mesh + Command Classes simulator
# ══════════════════════════════════════════════════════════════
class ZWavePage(ctk.CTkFrame):
    REGIONS = {
        "US  (908.42 MHz)": 908.42,
        "EU  (868.42 MHz)": 868.42,
        "AU  (921.42 MHz)": 921.42,
        "JP  (922.50 MHz)": 922.50,
        "RU  (869.00 MHz)": 869.00,
        "IN  (865.20 MHz)": 865.20,
    }
    CC = {
        0x20: "Basic",
        0x25: "Switch Binary",
        0x26: "Switch Multilevel",
        0x31: "Sensor Multilevel",
        0x32: "Meter",
        0x70: "Configuration",
        0x71: "Notification",
        0x72: "Manufacturer Specific",
        0x80: "Battery",
        0x86: "Version",
        0x98: "Security 0 (S0)",
        0x9F: "Security 2 (S2)",
    }
    CC_CMDS = {
        0x20: {0x01:"Set", 0x02:"Get", 0x03:"Report"},
        0x25: {0x01:"Set", 0x02:"Get", 0x03:"Report"},
        0x26: {0x01:"Set", 0x02:"Get", 0x03:"Report"},
        0x31: {0x04:"Get", 0x05:"Report"},
        0x71: {0x05:"Notification Get", 0x06:"Notification Report"},
        0x80: {0x02:"Battery Get", 0x03:"Battery Report"},
        0x86: {0x11:"Version Get", 0x12:"Version Report"},
    }
    TEMPLATES = {
        "Controller":            [0x86, 0x72],
        "Light Switch":          [0x25, 0x86, 0x72, 0x98],
        "Dimmer":                [0x26, 0x86, 0x72, 0x98],
        "Smart Plug":            [0x25, 0x32, 0x86, 0x72],
        "Door/Window Sensor":    [0x71, 0x80, 0x86, 0x72, 0x9F],
        "Motion Sensor":         [0x71, 0x80, 0x86, 0x72, 0x9F],
        "Temperature Sensor":    [0x31, 0x80, 0x86, 0x72],
        "Multi-sensor":          [0x31, 0x71, 0x80, 0x86, 0x72, 0x9F],
    }

    def __init__(self, parent):
        super().__init__(parent, fg_color=PAL["bg"])
        self.home_id = random.randint(0x10000000, 0xFFFFFFFE)
        self.region  = "US  (908.42 MHz)"
        self.security = "S2 Authenticated"
        self.include_mode = False
        self.nodes = []  # list of dicts
        self._build()
        # Add controller as Node 1
        self._add_node("Controller", "Z-Wave Controller", node_id=1)
        self._refresh()

    def _build(self):
        page_header(self, "📡  Z-Wave",
                    "Sub-GHz mesh (region-dependent). Up to 232 nodes, command-class based.")

        scroll = ctk.CTkScrollableFrame(self, fg_color=PAL["bg"])
        scroll.pack(fill="both", expand=True, padx=14, pady=8)

        # Network
        nc = card(scroll); nc.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(nc, text="NETWORK",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        g = ctk.CTkFrame(nc, fg_color="transparent"); g.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(g, text="Home ID").grid(row=0,column=0,sticky="e",padx=4)
        self.home_lbl = ctk.CTkLabel(g, text=f"0x{self.home_id:08X}",
                                     font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
                                     text_color=PAL["accent2"])
        self.home_lbl.grid(row=0,column=1,sticky="w",padx=4,pady=4)
        ctk.CTkButton(g, text="↻", width=40, command=self.regen_home,
                      fg_color=PAL["card2"], hover_color="#33334a").grid(row=0,column=2,padx=4)

        ctk.CTkLabel(g, text="Region").grid(row=0,column=3,sticky="e",padx=8)
        self.region_cb = ctk.CTkComboBox(g, values=list(self.REGIONS.keys()), width=180, state="readonly",
                                          command=lambda v: setattr(self,"region",v))
        self.region_cb.set(self.region); self.region_cb.grid(row=0,column=4,padx=4)

        ctk.CTkLabel(g, text="Security").grid(row=1,column=0,sticky="e",padx=4,pady=4)
        self.sec_cb = ctk.CTkComboBox(g, values=["None","S0 Legacy","S2 Unauthenticated","S2 Authenticated","S2 Access Control"],
                                       width=200, state="readonly",
                                       command=lambda v: setattr(self,"security",v))
        self.sec_cb.set(self.security); self.sec_cb.grid(row=1,column=1,padx=4,columnspan=2,sticky="w")

        self.inc_lbl = ctk.CTkLabel(g, text="● Include mode OFF", text_color=PAL["muted"])
        self.inc_lbl.grid(row=1,column=3,padx=8)
        self.btn_inc = ctk.CTkButton(g, text="▶  Start Inclusion", command=self.toggle_inclusion,
                                     fg_color=PAL["ok"], hover_color="#0e9d6e", width=180)
        self.btn_inc.grid(row=1, column=4, padx=4, pady=4)

        # Nodes
        dc = card(scroll); dc.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(dc, text="NODES",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        ar = ctk.CTkFrame(dc, fg_color="transparent"); ar.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(ar, text="+ Include", text_color=PAL["muted"]).pack(side="left", padx=(0,8))
        self.dev_type = ctk.CTkComboBox(ar, values=[k for k in self.TEMPLATES if k!="Controller"],
                                         width=200, state="readonly")
        self.dev_type.set("Light Switch"); self.dev_type.pack(side="left", padx=4)
        self.dev_name = ctk.CTkEntry(ar, width=180, placeholder_text="node name")
        self.dev_name.pack(side="left", padx=4)
        ctk.CTkButton(ar, text="+ Include Node", width=140, command=self.include_node,
                      fg_color=PAL["accent"]).pack(side="left", padx=4)

        hdr = ctk.CTkFrame(dc, fg_color=PAL["card2"], corner_radius=6)
        hdr.pack(fill="x", padx=14, pady=(8,2))
        for label, w in [("NODE",60),("NAME",170),("TYPE",170),("CMD CLASSES",220),("STATE",90)]:
            ctk.CTkLabel(hdr, text=label, width=w, anchor="w",
                         font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                         ).pack(side="left", padx=6, pady=4)
        ctk.CTkLabel(hdr, text="ACTIONS", anchor="w",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(side="left", padx=6, pady=4)
        self.dev_list = ctk.CTkScrollableFrame(dc, fg_color="transparent", height=180)
        self.dev_list.pack(fill="x", padx=10, pady=(0,10))

        # Send command
        sc = card(scroll); sc.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(sc, text="SEND COMMAND",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        sf = ctk.CTkFrame(sc, fg_color="transparent"); sf.pack(fill="x", padx=14, pady=(0,12))
        ctk.CTkLabel(sf, text="To Node").grid(row=0,column=0,sticky="e",padx=4)
        self.cmd_dst = ctk.CTkComboBox(sf, values=["(none)"], width=200, state="readonly")
        self.cmd_dst.grid(row=0,column=1,padx=4,pady=4)
        ctk.CTkLabel(sf, text="Command Class").grid(row=0,column=2,sticky="e",padx=4)
        self.cmd_cc = ctk.CTkComboBox(sf, values=[f"0x{c:02X} {n}" for c,n in self.CC.items()],
                                       width=230, state="readonly",
                                       command=lambda v: self._update_cmds())
        self.cmd_cc.set("0x25 Switch Binary"); self.cmd_cc.grid(row=0,column=3,padx=4)
        ctk.CTkLabel(sf, text="Command").grid(row=0,column=4,sticky="e",padx=4)
        self.cmd_id = ctk.CTkComboBox(sf, values=["0x01 Set","0x02 Get"], width=140, state="readonly")
        self.cmd_id.set("0x01 Set"); self.cmd_id.grid(row=0,column=5,padx=4)
        ctk.CTkLabel(sf, text="Value").grid(row=0,column=6,sticky="e",padx=4)
        self.cmd_val = ctk.CTkEntry(sf, width=80); self.cmd_val.insert(0,"FF")
        self.cmd_val.grid(row=0,column=7,padx=4)
        ctk.CTkButton(sc, text="📤  Send", command=self.send_cmd,
                      fg_color=PAL["accent"]).pack(anchor="e", padx=14, pady=(0,12))

        # Log
        lc = card(scroll); lc.pack(fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(lc, text="PROTOCOL LOG",
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=PAL["muted"]
                     ).pack(anchor="w", padx=14, pady=(10,4))
        self.log = LogView(lc, height=180)
        self.log.pack(fill="both", expand=True, padx=10, pady=(0,10))

    def _update_cmds(self):
        try:
            cid = int(self.cmd_cc.get().split()[0], 16)
            cmds = self.CC_CMDS.get(cid, {0x02:"Get"})
            self.cmd_id.configure(values=[f"0x{c:02X} {n}" for c,n in cmds.items()])
            first = list(cmds.keys())[0]
            self.cmd_id.set(f"0x{first:02X} {cmds[first]}")
        except Exception: pass

    def regen_home(self):
        self.home_id = random.randint(0x10000000, 0xFFFFFFFE)
        self.home_lbl.configure(text=f"0x{self.home_id:08X}")
        self.log.log(f"New Home ID = 0x{self.home_id:08X}", "info")

    def toggle_inclusion(self):
        self.include_mode = not self.include_mode
        if self.include_mode:
            self.btn_inc.configure(text="⏹  Stop Inclusion", fg_color=PAL["err"])
            self.inc_lbl.configure(text="● Include mode ON (60s)", text_color=PAL["ok"])
            self.log.log("Controller in INCLUSION mode — press button on device to add it", "ok")
            self.log.log(f"  Region: {self.region}   Security: {self.security}", "info")
            self.after(60000, self._auto_stop_inclusion)
        else:
            self.btn_inc.configure(text="▶  Start Inclusion", fg_color=PAL["ok"])
            self.inc_lbl.configure(text="● Include mode OFF", text_color=PAL["muted"])
            self.log.log("Inclusion mode ended", "info")

    def _auto_stop_inclusion(self):
        if self.include_mode:
            self.include_mode = False
            self.btn_inc.configure(text="▶  Start Inclusion", fg_color=PAL["ok"])
            self.inc_lbl.configure(text="● Include mode OFF (timeout)", text_color=PAL["muted"])
            self.log.log("Inclusion mode timed out (60s)", "info")

    def include_node(self):
        if not self.include_mode:
            messagebox.showwarning("Not in inclusion","Click Start Inclusion first."); return
        t = self.dev_type.get()
        n = self.dev_name.get().strip() or t
        self._add_node(t, n)
        self.dev_name.delete(0,"end")
        self._refresh()

    def _add_node(self, dev_type, name, node_id=None):
        if node_id is None:
            taken = {nd["id"] for nd in self.nodes}
            node_id = next(i for i in range(2, 233) if i not in taken)
        ccs = self.TEMPLATES[dev_type]
        state = "ON" if 0x25 in ccs else \
                f"{20+random.randint(0,8)}°C" if 0x31 in ccs else \
                "IDLE" if 0x71 in ccs else "—"
        nd = {"id":node_id, "name":name, "type":dev_type, "ccs":ccs, "state":state,
              "battery": 100 if 0x80 in ccs else None}
        self.nodes.append(nd)
        if dev_type != "Controller":
            self.log.log(f"NodeAdd: ID={node_id} type={dev_type}", "rx")
            self.log.log(f"  NIF: CommandClasses=[{', '.join(f'0x{c:02X} '+self.CC[c] for c in ccs)}]", "info")
            self.log.log(f"  S2 KEX granted: keys exchanged using ECDH curve25519", "info")

    def _refresh(self):
        for w in self.dev_list.winfo_children(): w.destroy()
        targets = []
        for nd in self.nodes:
            row = ctk.CTkFrame(self.dev_list, fg_color=PAL["card2"], corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"#{nd['id']:>3}", width=60, anchor="w",
                         font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                         text_color=PAL["accent2"]).pack(side="left", padx=6, pady=4)
            ctk.CTkLabel(row, text=nd["name"], width=170, anchor="w",
                         font=ctk.CTkFont(size=11)).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=nd["type"], width=170, anchor="w",
                         font=ctk.CTkFont(size=11), text_color=PAL["muted"]
                         ).pack(side="left", padx=6)
            cc_str = " ".join(f"0x{c:02X}" for c in nd["ccs"])
            ctk.CTkLabel(row, text=cc_str, width=220, anchor="w",
                         font=ctk.CTkFont(family="Consolas", size=10),
                         text_color=PAL["muted"]).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=nd["state"], width=90, anchor="w",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=PAL["accent2"]).pack(side="left", padx=6)
            if nd["type"] != "Controller":
                ctk.CTkButton(row, text="🗑 Exclude", width=90, height=24,
                              fg_color=PAL["card"], hover_color="#33334a",
                              command=lambda i=nd["id"]: self.exclude(i)).pack(side="left", padx=2)
                targets.append(f"#{nd['id']}  {nd['name']}")
        if targets:
            self.cmd_dst.configure(values=targets); self.cmd_dst.set(targets[0])
        else:
            self.cmd_dst.configure(values=["(none)"]); self.cmd_dst.set("(none)")

    def exclude(self, nid):
        self.nodes = [n for n in self.nodes if n["id"] != nid]
        self.log.log(f"NodeRemove: ID={nid} excluded from network", "info")
        self._refresh()

    def send_cmd(self):
        dst_text = self.cmd_dst.get()
        if dst_text.startswith("("):
            messagebox.showwarning("No target","Include a node first."); return
        try:
            nid = int(dst_text.split()[0].lstrip("#"))
            cc  = int(self.cmd_cc.get().split()[0], 16)
            cmd = int(self.cmd_id.get().split()[0], 16)
            val = self.cmd_val.get().strip() or "00"
        except Exception as e:
            messagebox.showerror("Parse err", str(e)); return

        cc_name  = self.CC.get(cc, "?")
        cmd_name = self.CC_CMDS.get(cc,{}).get(cmd, "?")
        self.log.log(f"TX  Send → Node #{nid}  CC=0x{cc:02X} {cc_name}  Cmd=0x{cmd:02X} {cmd_name}  val=0x{val}", "tx")
        self.log.log(f"    Frame: [HomeID=0x{self.home_id:08X}][src=01][dst={nid:02X}][CC={cc:02X}][CMD={cmd:02X}][val={val}]", "info")

        for nd in self.nodes:
            if nd["id"] != nid: continue
            if cc == 0x25:   # Switch Binary
                if cmd == 0x01:
                    nd["state"] = "ON" if val.upper()=="FF" else "OFF"
                    self.log.log(f"RX  ACK from #{nid}: SwitchBinary state={nd['state']}", "rx")
                elif cmd == 0x02:
                    self.log.log(f"RX  Report from #{nid}: SwitchBinary value={'0xFF' if nd['state']=='ON' else '0x00'}", "rx")
            elif cc == 0x26:  # Multilevel
                if cmd == 0x01:
                    lvl = int(val,16); nd["state"] = f"{lvl}%"
                    self.log.log(f"RX  ACK from #{nid}: Dimmer level={lvl}", "rx")
            elif cc == 0x31:  # Sensor Multilevel
                t = 20 + random.uniform(-3,8); nd["state"] = f"{t:.1f}°C"
                self.log.log(f"RX  Report from #{nid}: SensorType=Temperature value={t:.2f}", "rx")
            elif cc == 0x80:  # Battery
                self.log.log(f"RX  Report from #{nid}: BatteryLevel={nd['battery']}%", "rx")
            elif cc == 0x86:  # Version
                self.log.log(f"RX  Report from #{nid}: ZWaveLibVer=6.7  AppVer=1.05  ProtoVer=4.62", "rx")
            else:
                self.log.log(f"RX  ACK from #{nid}: OK", "rx")
            break
        self._refresh()


# ══════════════════════════════════════════════════════════════
#  ABOUT PAGE
# ══════════════════════════════════════════════════════════════
class AboutPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=PAL["bg"])
        self._build()

    def _build(self):
        page_header(self, "ℹ️  About", "")
        c = card(self); c.pack(fill="both", expand=True, padx=20, pady=10)

        inner = ctk.CTkFrame(c, fg_color="transparent")
        inner.pack(padx=30, pady=24, anchor="w")

        ctk.CTkLabel(inner, text="🔬  IoT Protocol Simulator",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=PAL["text"]).pack(anchor="w")
        ctk.CTkLabel(inner, text="A teaching & research tool for IoT messaging protocols",
                     font=ctk.CTkFont(size=13), text_color=PAL["muted"]).pack(anchor="w", pady=(2,16))

        ctk.CTkLabel(inner, text="Developed by",
                     font=ctk.CTkFont(size=11), text_color=PAL["muted"]).pack(anchor="w")
        ctk.CTkLabel(inner, text="Dr. Mohammed Tawfik",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=PAL["accent2"]).pack(anchor="w", pady=(2,2))
        ctk.CTkLabel(inner, text="Assistant Professor — Cybersecurity & Cloud Computing",
                     font=ctk.CTkFont(size=12), text_color=PAL["text"]).pack(anchor="w")
        ctk.CTkLabel(inner, text="Ajloun National University  ·  Sana'a University",
                     font=ctk.CTkFont(size=12), text_color=PAL["muted"]).pack(anchor="w", pady=(0,4))
        ctk.CTkLabel(inner, text="✉  kmkhol01@gmail.com",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=PAL["accent2"]).pack(anchor="w", pady=(0,18))

        # Features
        ctk.CTkLabel(inner, text="FEATURES",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", pady=(4,4))
        for line in [
            "•  MQTT v3.1.1  (plaintext & TLS) using paho-mqtt",
            "•  CoAP (RFC 7252) client + server using aiocoap with live resources",
            "•  AMQP 0-9-1  with built-in in-memory broker + optional RabbitMQ via pika",
            "•  Zigbee (IEEE 802.15.4 + ZCL) simulator — PAN, clusters, devices, commands",
            "•  Z-Wave  mesh simulator — Home ID, command classes, inclusion, nodes",
            "•  NFC NDEF tag simulator (Text / URI / WiFi / vCard / MIME / External)",
            "•  12 live virtual sensors with mean-reverting random-walk models",
            "•  Auto-discovering subscriber dashboard with live matplotlib plots",
        ]:
            ctk.CTkLabel(inner, text=line, font=ctk.CTkFont(size=12),
                         text_color=PAL["text"]).pack(anchor="w", pady=1)

        # System info
        ctk.CTkLabel(inner, text="\nSYSTEM",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w", pady=(14,4))
        sys_info = [
            f"Python      : {sys.version.split()[0]}",
            f"Executable  : {sys.executable}",
            f"paho-mqtt   : {'✓ installed' if MQTT_OK else '✗ missing'}",
            f"aiocoap     : {'✓ installed' if COAP_OK else '✗ missing'}",
            f"pika        : {'✓ installed' if AMQP_OK else '✗ missing'}",
            f"ndeflib     : {'✓ installed' if NDEF_OK else '✗ missing'}",
            f"matplotlib  : {'✓ installed' if MPL_OK else '✗ missing'}",
        ]
        for line in sys_info:
            ctk.CTkLabel(inner, text=line, font=ctk.CTkFont(family="Consolas", size=11),
                         text_color=PAL["text"] if "✓" in line or ":" in line else PAL["err"]
                         ).pack(anchor="w", pady=1)

        ctk.CTkLabel(inner, text="\nTo install missing packages:",
                     font=ctk.CTkFont(size=11), text_color=PAL["muted"]).pack(anchor="w", pady=(14,2))
        cmd = f"{sys.executable} -m pip install customtkinter paho-mqtt aiocoap pika ndeflib matplotlib"
        ctk.CTkLabel(inner, text=cmd, font=ctk.CTkFont(family="Consolas", size=11),
                     text_color=PAL["accent2"]).pack(anchor="w")


# ══════════════════════════════════════════════════════════════
#  MAIN APP — sidebar navigation
# ══════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("IoT Protocol Simulator  —  by Dr. Mohammed Tawfik")
        self.geometry("1400x860")
        self.minsize(1200, 720)
        self.configure(fg_color=PAL["bg"])

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- Sidebar ----
        sidebar = ctk.CTkFrame(self, width=240, fg_color=PAL["sidebar"], corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Logo / title
        logo = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo.pack(pady=(24, 4), fill="x", padx=20)
        ctk.CTkLabel(logo, text="🔬", font=ctk.CTkFont(size=32)).pack(anchor="w")
        ctk.CTkLabel(logo, text="IoT Sim", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=PAL["text"]).pack(anchor="w")
        ctk.CTkLabel(logo, text="Protocol Simulator",
                     font=ctk.CTkFont(size=11), text_color=PAL["muted"]).pack(anchor="w", pady=(0,12))
        ctk.CTkFrame(sidebar, height=1, fg_color=PAL["border"]).pack(fill="x", padx=20, pady=4)

        # Nav buttons
        page_specs = [
            ("dashboard","📊   Dashboard",   DashboardPage),
            ("monitor",  "📡   Monitor",     MonitorPage),
            ("mqtt",     "📨   MQTT",        lambda p: MQTTPage(p, tls=False)),
            ("mqtts",    "🔒   MQTTS (TLS)", lambda p: MQTTPage(p, tls=True)),
            ("coap",     "🌐   CoAP",        CoAPPage),
            ("amqp",     "🐰   AMQP",        AMQPPage),
            ("zigbee",   "🐝   Zigbee",      ZigbeePage),
            ("zwave",    "📡   Z-Wave",      ZWavePage),
            ("nfc",      "📱   NFC",         NFCPage),
            ("about",    "ℹ️    About",      AboutPage),
        ]
        self.nav_btns = {}
        self.pages = {}

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=10, pady=8)

        # ---- Content area (created first so pages can be parented to it) ----
        self.content = ctk.CTkFrame(self, fg_color=PAL["bg"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # Build pages — failures become a visible error page (not silent)
        import traceback as _tb
        for key, label, cls in page_specs:
            try:
                page = cls(self.content)
                page.grid(row=0, column=0, sticky="nsew")
                page.grid_remove()
                self.pages[key] = page
            except Exception as e:
                err_text = _tb.format_exc()
                print(f"[!] Page '{key}' failed to build:\n{err_text}")
                ep = ctk.CTkFrame(self.content, fg_color=PAL["bg"])
                ep.grid(row=0, column=0, sticky="nsew")
                ep.grid_remove()
                c = ctk.CTkFrame(ep, fg_color=PAL["card"], corner_radius=10,
                                 border_width=1, border_color=PAL["err"])
                c.pack(fill="both", expand=True, padx=24, pady=24)
                ctk.CTkLabel(c, text=f"⚠  Page '{label.strip()}' failed to load",
                             font=ctk.CTkFont(size=20, weight="bold"),
                             text_color=PAL["err"]).pack(padx=20, pady=(20,8), anchor="w")
                ctk.CTkLabel(c, text=f"{type(e).__name__}: {e}",
                             font=ctk.CTkFont(family="Consolas", size=12),
                             text_color=PAL["warn"]).pack(padx=20, pady=(0,12), anchor="w")
                tbx = ctk.CTkTextbox(c, fg_color="#0d0d16", text_color=PAL["text"],
                                     font=ctk.CTkFont(family="Consolas", size=10),
                                     border_width=1, border_color=PAL["border"])
                tbx.pack(fill="both", expand=True, padx=20, pady=(0,20))
                tbx.insert("1.0", err_text)
                self.pages[key] = ep

        # Build nav buttons
        for key, label, _ in page_specs:
            btn = ctk.CTkButton(nav, text=label, anchor="w", height=40,
                                font=ctk.CTkFont(size=13),
                                fg_color="transparent",
                                text_color=PAL["muted"],
                                hover_color=PAL["card"],
                                corner_radius=6,
                                command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", pady=2)
            self.nav_btns[key] = btn

        # Library status footer
        ctk.CTkFrame(sidebar, height=1, fg_color=PAL["border"]).pack(fill="x", padx=20, pady=(8,4))
        sf = ctk.CTkFrame(sidebar, fg_color="transparent")
        sf.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(sf, text="LIBRARIES",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w")
        for name, ok in [("paho-mqtt",MQTT_OK),("aiocoap",COAP_OK),
                         ("pika",AMQP_OK),("ndeflib",NDEF_OK),
                         ("matplotlib",MPL_OK)]:
            r = ctk.CTkFrame(sf, fg_color="transparent")
            r.pack(fill="x", pady=0)
            ctk.CTkLabel(r, text="●", text_color=PAL["ok"] if ok else PAL["err"],
                         font=ctk.CTkFont(size=11)).pack(side="left")
            ctk.CTkLabel(r, text=name, font=ctk.CTkFont(size=10),
                         text_color=PAL["text"] if ok else PAL["muted"]).pack(side="left", padx=4)

        # Author footer
        ctk.CTkFrame(sidebar, height=1, fg_color=PAL["border"]).pack(fill="x", padx=20, pady=(10,6))
        af = ctk.CTkFrame(sidebar, fg_color="transparent")
        af.pack(fill="x", padx=20, pady=(0,18))
        ctk.CTkLabel(af, text="DEVELOPED BY",
                     font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=PAL["muted"]).pack(anchor="w")
        ctk.CTkLabel(af, text="Dr. Mohammed Tawfik",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=PAL["accent2"]).pack(anchor="w", pady=(2,0))
        ctk.CTkLabel(af, text="Cybersecurity & Cloud Computing",
                     font=ctk.CTkFont(size=10), text_color=PAL["muted"]).pack(anchor="w")
        ctk.CTkLabel(af, text="✉  kmkhol01@gmail.com",
                     font=ctk.CTkFont(size=10), text_color=PAL["muted"]).pack(anchor="w", pady=(3,0))

        self.show_page("dashboard")

    def show_page(self, key):
        for p in self.pages.values():
            p.grid_remove()
        if key in self.pages:
            self.pages[key].grid()
        for k, b in self.nav_btns.items():
            if k == key:
                b.configure(fg_color=PAL["accent"], text_color="white")
            else:
                b.configure(fg_color="transparent", text_color=PAL["muted"])


if __name__ == "__main__":
    App().mainloop()
