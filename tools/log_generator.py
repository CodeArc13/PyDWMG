import sys
import time
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QMainWindow,
    QVBoxLayout,
    QLabel,
)
from PyQt5.QtCore import (
    QObject,
    Qt,
    QThread,
    pyqtSlot,
    pyqtSignal,
)

GENERATED_LOGFILE = "fake_logfile.txt"

ZONE_NORTH_QEYNOS = "[Sat Feb 13 01:40:54 2021] You have entered North Qeynos."
ZONE_QEYNOS_HILLS = "[Sat Feb 13 01:43:20 2021] You have entered Qeynos Hills."

LOC_SAMPLE_1 = """[Sat Feb 13 15:34:07 2021] Your Location is 1029.46, 127.82, 3.75
[Sat Feb 13 15:34:08 2021] Your Location is 1022.43, 127.91, 3.75
[Sat Feb 13 15:34:08 2021] Your Location is 1015.72, 127.99, 3.75
[Sat Feb 13 15:34:08 2021] Your Location is 1009.34, 128.07, 3.75"""

LOC_SAMPLE_2 = """[Sat Feb 13 15:34:37 2021] Your Location is 175.16, 119.30, 2.75
[Sat Feb 13 15:34:37 2021] Your Location is 168.44, 119.66, 2.75
[Sat Feb 13 15:34:37 2021] Your Location is 162.66, 122.82, 2.75
[Sat Feb 13 15:34:37 2021] Your Location is 159.91, 128.35, 2.75"""

LOC_SAMPLE_3 = """[Sat Feb 13 15:36:21 2021] Your Location is 333.16, 84.96, 3.19
[Sat Feb 13 15:36:21 2021] Your Location is 339.91, 84.21, 3.72
[Sat Feb 13 15:36:21 2021] Your Location is 346.63, 83.47, 4.23
[Sat Feb 13 15:36:21 2021] Your Location is 353.33, 82.72, 4.49"""

LOC_SAMPLE_4 = """[Sat Feb 13 15:37:42 2021] Your Location is 1336.53, -1890.43, -0.59
[Sat Feb 13 15:37:42 2021] Your Location is 1339.75, -1896.28, -0.59
[Sat Feb 13 15:37:43 2021] Your Location is 1343.01, -1902.20, -0.59
[Sat Feb 13 15:37:43 2021] Your Location is 1347.14, -1907.52, -0.59"""

LOGFILE_NORTHQEYNOS = "tools/log_generator_northqeynos.txt"
LOGFILE_QEYNOSHILLS = "tools/log_generator_qeynoshills.txt"
LOGFILE_QH_TO_NQ_QUICK = "tools/log_generator_qh_to_nq_quick.txt"
LOGFILE_QH_TO_NQ_FULL = "tools/log_generator_qh_to_nq_full.txt"


class ParentSignals(QObject):
    """ Defines the signals to pass to a worker thread for parent control """

    terminate = pyqtSignal()


class LogSimulator(QThread):
    """ Worker thread, inherits from QThread """

    def __init__(self, *args, parent_signals=None, sim_name="", **kwargs):
        super(LogSimulator, self).__init__()
        # Store constructor arguments (re-used for processing)
        self._stopped = False
        self.args = args
        self.kwargs = kwargs
        self.parent_signals = parent_signals
        self.parent_signals.terminate.connect(self.stop)
        self.sim_name = sim_name
        # Can use a timer in the worker thread for periodic checks, etc.
        # self.show_status = QTimer()
        # self.show_status.timeout.connect(self.parser_status)
        # self.show_status.start(2000)

    def stop(self):
        print("Log simulation stopped.")
        self._stopped = True

    @pyqtSlot()
    def run(self):
        if self.sim_name == "northqeynos":
            sim_logfile = LOGFILE_NORTHQEYNOS
        elif self.sim_name == "qeynoshills":
            sim_logfile = LOGFILE_QEYNOSHILLS
        elif self.sim_name == "qh_to_nq_quick":
            sim_logfile = LOGFILE_QH_TO_NQ_QUICK
        elif self.sim_name == "qh_to_nq_full":
            sim_logfile = LOGFILE_QH_TO_NQ_FULL
        else:
            return
        print(f"Log simulation {self.sim_name} started...")
        with open(GENERATED_LOGFILE, "at", buffering=1) as w:
            with open(sim_logfile, "rt") as r:
                lines_written = 0
                for line in r.readlines():
                    if self._stopped:
                        # self.signals.finished.emit()
                        return
                    if lines_written >= 4:
                        for _ in range(5):
                            if self._stopped:
                                return
                            time.sleep(1)
                        lines_written = 0
                    w.writelines([line, "\n"])
                    time.sleep(0.1)
                    lines_written += 1
        print("Log simulation finished.")


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        layout = QVBoxLayout()

        label_main = QLabel("\nDWMG Log Generator Tool")
        label_single = QLabel("\nSingle Events:")
        self.button_zone1 = QPushButton("Zone: North Qeynos")
        self.button_zone1.pressed.connect(lambda: self.update_log(ZONE_NORTH_QEYNOS))
        self.button_zone2 = QPushButton("Zone: Qeynos Hills")
        self.button_zone2.pressed.connect(lambda: self.update_log(ZONE_QEYNOS_HILLS))
        self.button_loc1 = QPushButton("Loc Spam 1 (NQ)")
        self.button_loc1.pressed.connect(lambda: self.update_log(LOC_SAMPLE_1))
        self.button_loc2 = QPushButton("Loc Spam 2 (NQ)")
        self.button_loc2.pressed.connect(lambda: self.update_log(LOC_SAMPLE_2))
        self.button_loc3 = QPushButton("Loc Spam 3 (QH)")
        self.button_loc3.pressed.connect(lambda: self.update_log(LOC_SAMPLE_3))
        self.button_loc4 = QPushButton("Loc Spam 4 (QH)")
        self.button_loc4.pressed.connect(lambda: self.update_log(LOC_SAMPLE_4))
        label_simulators = QLabel("\nLog Simulators:")
        self.button_northqeynos = QPushButton("In Zone: North Qeynos")
        self.button_northqeynos.pressed.connect(lambda: self.run_log_sim("northqeynos"))
        self.button_qeynoshills = QPushButton("In Zone: Qeynos Hills")
        self.button_qeynoshills.pressed.connect(lambda: self.run_log_sim("qeynoshills"))
        self.button_qh_to_nq_quick = QPushButton("Zoning: QH to NQ (Quick)")
        self.button_qh_to_nq_quick.pressed.connect(
            lambda: self.run_log_sim("qh_to_nq_quick")
        )
        self.button_qh_to_nq_full = QPushButton("Zoning: QH to NQ (Full)")
        self.button_qh_to_nq_full.pressed.connect(
            lambda: self.run_log_sim("qh_to_nq_full")
        )

        label_simulators_active = QLabel("\nActive Simulation:")
        self.label_active_simulator = QLabel("(None)")
        self.label_active_simulator.setAlignment(Qt.AlignCenter)
        self.label_active_simulator.setStyleSheet(
            "QLabel { background-color : green; color : black; }"
        )
        button_terminate_sim = QPushButton("Terminate Simulation")
        button_terminate_sim.pressed.connect(self.terminate_sim)
        button_quit = QPushButton("Quit")
        button_quit.pressed.connect(self.quit_app)

        layout.addWidget(label_main)
        layout.addWidget(label_single)
        layout.addWidget(self.button_zone1)
        layout.addWidget(self.button_zone2)
        layout.addWidget(self.button_loc1)
        layout.addWidget(self.button_loc2)
        layout.addWidget(self.button_loc3)
        layout.addWidget(self.button_loc4)
        layout.addWidget(label_simulators)
        layout.addWidget(self.button_northqeynos)
        layout.addWidget(self.button_qeynoshills)
        layout.addWidget(self.button_qh_to_nq_quick)
        layout.addWidget(self.button_qh_to_nq_full)
        layout.addWidget(label_simulators_active)
        layout.addWidget(self.label_active_simulator)
        layout.addWidget(button_terminate_sim)
        layout.addWidget(button_quit)

        w = QWidget()
        w.setLayout(layout)

        self.setCentralWidget(w)

        self.show()

    def update_log(self, log_text):
        with open(GENERATED_LOGFILE, "at", buffering=1) as f:
            for line in log_text.splitlines():
                f.writelines([line, "\n"])
                time.sleep(0.1)

    def run_log_sim(self, sim_name):
        self.label_active_simulator.setText(sim_name)
        self.label_active_simulator.setStyleSheet(
            "QLabel { background-color : red; color : black; }"
        )

        self.logsim_control = ParentSignals()
        self.worker_logsim = LogSimulator(
            parent_signals=self.logsim_control, sim_name=sim_name
        )
        self.worker_logsim.started.connect(self.simulator_started)
        self.worker_logsim.finished.connect(self.simulator_finished)
        self.worker_logsim.start()

    def set_buttons_disabled(self, action):
        self.button_zone1.setDisabled(action)
        self.button_zone2.setDisabled(action)
        self.button_loc1.setDisabled(action)
        self.button_loc2.setDisabled(action)
        self.button_loc3.setDisabled(action)
        self.button_loc4.setDisabled(action)
        self.button_northqeynos.setDisabled(action)
        self.button_qeynoshills.setDisabled(action)

    def terminate_sim(self):
        try:
            self.logsim_control.terminate.emit()
        except AttributeError:
            pass

    def simulator_started(self):
        self.set_buttons_disabled(True)

    def simulator_finished(self):
        self.set_buttons_disabled(False)
        self.label_active_simulator.setText("None")
        self.label_active_simulator.setStyleSheet(
            "QLabel { background-color : green; color : black; }"
        )

    def quit_app(self):
        self.terminate_sim()
        app.quit()


app = QApplication([1, ""])
window = MainWindow()
sys.exit(app.exec())
