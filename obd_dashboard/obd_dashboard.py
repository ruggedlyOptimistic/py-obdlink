import sys
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel,
    QPushButton, QTextEdit, QDial, QHBoxLayout, QMainWindow
)
from PyQt6.QtCore import QTimer, Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import obd

# Initialize OBD connection
connection = obd.OBD()  # auto-connect


class LiveDataPlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.rpm_vals = []
        self.speed_vals = []
        self.time_vals = []

        layout = QVBoxLayout(self)

        self.canvas = FigureCanvas(plt.Figure())
        layout.addWidget(self.canvas)
        self.ax_rpm = self.canvas.figure.add_subplot(211)
        self.ax_speed = self.canvas.figure.add_subplot(212)

        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plot)
        self.plot_timer.start(1000)

    def update_plot(self):
        if connection.status() != obd.OBDStatus.CAR_CONNECTED:
            return

        t = time.time()
        rpm_resp = connection.query(obd.commands.RPM)
        speed_resp = connection.query(obd.commands.SPEED)

        if rpm_resp.value:
            self.rpm_vals.append(rpm_resp.value.magnitude)
            self.time_vals.append(t)

        if speed_resp.value:
            self.speed_vals.append(speed_resp.value.magnitude)

        # Limit to last 30 points
        self.rpm_vals = self.rpm_vals[-30:]
        self.speed_vals = self.speed_vals[-30:]
        self.time_vals = self.time_vals[-30:]

        self.ax_rpm.clear()
        self.ax_speed.clear()
        self.ax_rpm.plot(self.time_vals, self.rpm_vals, label='RPM')
        self.ax_speed.plot(self.time_vals, self.speed_vals, label='Speed (km/h)')

        self.ax_rpm.set_ylabel("RPM")
        self.ax_speed.set_ylabel("Speed")
        self.ax_speed.set_xlabel("Time")

        self.ax_rpm.legend()
        self.ax_speed.legend()

        self.canvas.draw()


class DtcTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()

        self.dtc_display = QTextEdit()
        self.dtc_display.setReadOnly(True)
        layout.addWidget(QLabel("Current DTCs:"))
        layout.addWidget(self.dtc_display)

        self.refresh_btn = QPushButton("Refresh DTCs")
        self.refresh_btn.clicked.connect(self.refresh_dtcs)
        layout.addWidget(self.refresh_btn)

        self.clear_btn = QPushButton("Clear DTCs")
        self.clear_btn.clicked.connect(self.clear_dtcs)
        layout.addWidget(self.clear_btn)

        self.setLayout(layout)

    def refresh_dtcs(self):
        dtc_response = connection.query(obd.commands.GET_DTC)
        dtcs = dtc_response.value
        self.dtc_display.clear()
        if dtcs:
            for code, desc in dtcs:
                self.dtc_display.append(f"{code}: {desc}")
        else:
            self.dtc_display.setText("No fault codes found.")

    def clear_dtcs(self):
        connection.query(obd.commands.CLEAR_DTC)
        self.dtc_display.append("\nFault codes cleared.")


class GaugeTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        dial_layout = QHBoxLayout()

        self.rpm_dial = QDial()
        self.rpm_dial.setRange(0, 8000)
        self.rpm_dial.setNotchesVisible(True)
        self.rpm_dial.setWrapping(False)
        self.rpm_dial.setReadOnly(True)

        self.speed_dial = QDial()
        self.speed_dial.setRange(0, 200)
        self.speed_dial.setNotchesVisible(True)
        self.speed_dial.setWrapping(False)
        self.speed_dial.setReadOnly(True)

        dial_layout.addWidget(QLabel("RPM"))
        dial_layout.addWidget(self.rpm_dial)
        dial_layout.addWidget(QLabel("Speed (km/h)"))
        dial_layout.addWidget(self.speed_dial)

        layout.addLayout(dial_layout)
        self.setLayout(layout)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_gauges)
        self.update_timer.start(1000)

    def update_gauges(self):
        rpm = connection.query(obd.commands.RPM)
        speed = connection.query(obd.commands.SPEED)

        if rpm.value:
            self.rpm_dial.setValue(int(rpm.value.magnitude))

        if speed.value:
            self.speed_dial.setValue(int(speed.value.magnitude))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OBD Vehicle Dashboard")

        tabs = QTabWidget()
        tabs.addTab(GaugeTab(), "Gauges")
        tabs.addTab(LiveDataPlot(), "Live Data")
        tabs.addTab(DtcTab(), "Fault Codes")

        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
