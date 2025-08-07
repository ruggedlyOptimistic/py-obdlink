import math
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox

import obd  # python-OBD

# -------------------------
# Config
# -------------------------
WIN_W, WIN_H = 800, 800
GAUGE_CENTER = (WIN_W // 2, WIN_H // 2)
RADIUS = 300
MAX_RPM = 13000            # adjust if your redline differs
START_ANGLE = -120        # needle angle at 0 RPM (degrees)
END_ANGLE = 120           # needle angle at MAX_RPM (degrees)
UPDATE_MS = 5           # refresh interval

# -------------------------
# OBD connection (in main thread)
# -------------------------
try:
    connection = obd.OBD()  # auto connect
except Exception as e:
    connection = None
    print(f"OBD init error: {e}", file=sys.stderr)

# -------------------------
# Gauge widget
# -------------------------
class RpmGauge(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, width=WIN_W, height=WIN_H, bg="#111")
        self.pack(fill="both", expand=True)
        self.cx, self.cy = GAUGE_CENTER
        self.needle = None
        self.current_rpm = 0.0
        self._draw_static_parts()
        self._draw_needle(0.0)

    def _draw_static_parts(self):
        # Outer bezel
        self.create_oval(self.cx - RADIUS, self.cy - RADIUS,
                         self.cx + RADIUS, self.cy + RADIUS,
                         outline="#888", width=6)

        # Inner face
        self.create_oval(self.cx - (RADIUS-15), self.cy - (RADIUS-15),
                         self.cx + (RADIUS-15), self.cy + (RADIUS-15),
                         fill="#1b1b1b", outline="")

        # Title
        self.create_text(self.cx, self.cy + RADIUS*0.45,
                         text="ENGINE RPM", fill="#ddd",
                         font=("Helvetica", 22, "bold"))

        # Tick marks / labels
        self._draw_ticks()

        # Hub
        self.create_oval(self.cx - 14, self.cy - 14,
                         self.cx + 14, self.cy + 14,
                         fill="#bbb", outline="#333", width=2)

    def _draw_ticks(self):
        # Major every 1000 RPM, minor every 500 RPM
        major_step = 1000
        minor_step = 500
        for rpm in range(0, MAX_RPM + minor_step, minor_step):
            angle = self._rpm_to_angle(rpm)
            # tick geometry
            inner = RADIUS - 35 if rpm % major_step == 0 else RADIUS - 20
            outer = RADIUS - 5

            x1, y1 = self._polar(self.cx, self.cy, inner, angle)
            x2, y2 = self._polar(self.cx, self.cy, outer, angle)

            color = "#ddd" if rpm % major_step == 0 else "#777"
            width = 4 if rpm % major_step == 0 else 2
            self.create_line(x1, y1, x2, y2, fill=color, width=width)

            # Label major ticks
            if rpm % major_step == 0:
                lx, ly = self._polar(self.cx, self.cy, RADIUS - 70, angle)
                label = str(rpm // 1000)
                self.create_text(lx, ly, text=label, fill="#eee",
                                 font=("Helvetica", 18, "bold"))

        # Redline arc (last 1000 RPM)
        red_start = self._rpm_to_angle(MAX_RPM - 1000)
        red_end = self._rpm_to_angle(MAX_RPM)
        # Create arc expects degrees start measured anti-clockwise from 3 o'clock.
        # Convert our math-based angles (0°=right, positive CCW) to Tk arc:
        # Tk uses start angle in degrees counterclockwise from 3 o'clock,
        # and extent positive is counterclockwise.
        # We can approximate with an arc covering the segment.
        self.create_arc(self.cx - (RADIUS-10), self.cy - (RADIUS-10),
                        self.cx + (RADIUS-10), self.cy + (RADIUS-10),
                        start=(-red_end), extent=(red_end - red_start),
                        style="arc", outline="#c33", width=10)

        # Units text
        self.create_text(self.cx, self.cy + RADIUS*0.33,
                         text="x1000 r/min", fill="#aaa",
                         font=("Helvetica", 14))

    def _polar(self, cx, cy, r, angle_deg):
        rad = math.radians(angle_deg)
        return (cx + r * math.cos(rad), cy + r * math.sin(rad))

    def _rpm_to_angle(self, rpm):
        rpm_clamped = max(0.0, min(float(rpm), MAX_RPM))
        frac = rpm_clamped / MAX_RPM if MAX_RPM else 0.0
        return START_ANGLE + frac * (END_ANGLE - START_ANGLE)

    def _draw_needle(self, rpm):
        angle = self._rpm_to_angle(rpm)
        # clear previous needle
        if self.needle:
            self.delete(self.needle)

        # needle base and tip
        tip_len = RADIUS - 60
        back_len = 40
        x_tip, y_tip = self._polar(self.cx, self.cy, tip_len, angle)
        x_back, y_back = self._polar(self.cx, self.cy, -back_len, angle)

        self.needle = self.create_line(
            x_back, y_back, x_tip, y_tip,
            fill="#e33", width=6, capstyle="round"
        )

        # digital readout
        self._update_digital_label(rpm)

    def _update_digital_label(self, rpm):
        # remove old digital readout by tagging
        self.delete("rpm_text")
        self.create_text(self.cx, self.cy + RADIUS*0.58,
                         text=f"{int(rpm):,} RPM",
                         fill="#fafafa",
                         font=("Helvetica", 28, "bold"),
                         tags=("rpm_text",))

    def set_rpm(self, rpm):
        self.current_rpm = rpm
        self._draw_needle(rpm)


# -------------------------
# App that polls OBD
# -------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RPM Gauge")
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.configure(bg="#111")

        self.gauge = RpmGauge(self)

        # Status bar
        self.status = tk.Label(self, text="Connecting...",
                               fg="#ddd", bg="#222",
                               font=("Helvetica", 12))
        self.status.pack(side="bottom", fill="x")

        self._stop = False
        self._rpm_value = 0.0

        self._start_polling_thread()
        self.after(UPDATE_MS, self._refresh_gui)

    def _start_polling_thread(self):
        t = threading.Thread(target=self._poll_obd, daemon=True)
        t.start()

    def _poll_obd(self):
        global connection
        last_ok = False
        while not self._stop:
            try:
                if connection and connection.status() == obd.OBDStatus.CAR_CONNECTED:
                    rpm_resp = connection.query(obd.commands.RPM)
                    if rpm_resp and rpm_resp.value is not None:
                        self._rpm_value = float(rpm_resp.value.magnitude)
                        last_ok = True
                    else:
                        # Keep last value if no reading this cycle
                        pass
                else:
                    # Try to (re)connect occasionally if not connected
                    if not connection:
                        connection = obd.OBD()
                    elif connection.status() != obd.OBDStatus.CAR_CONNECTED:
                        # small backoff
                        time.sleep(1)
                time.sleep(0.1)
            except Exception as e:
                # On error, just note disconnected and retry
                last_ok = False
                time.sleep(0.5)

    def _refresh_gui(self):
        # Update gauge & status label
        self.gauge.set_rpm(self._rpm_value)
        if connection and connection.status() == obd.OBDStatus.CAR_CONNECTED:
            self.status.config(text="Connected to vehicle", fg="#9f9")
        else:
            self.status.config(text="Not connected… (check cable/ignition)", fg="#f99")

        if not self._stop:
            self.after(UPDATE_MS, self._refresh_gui)

    def on_close(self):
        self._stop = True
        try:
            if connection:
                connection.close()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
