import re
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
    QRunnable,
    QThreadPool,
    QTimer,
    pyqtSlot,
    pyqtSignal,
)

from PyQt5.QtGui import QPixmap


class WorkerSignals(QObject):
    """ Defines the signals available from a running worker thread."""

    zone = pyqtSignal(str)
    loc = pyqtSignal(tuple)


class ParentSignals(QObject):
    """ Defines the signals to pass to a worker thread for parent control """

    terminate = pyqtSignal()


class EQLogParser(QRunnable):
    """
    Worker thread, inherits from QRunnable to handler worker thread setup,
    signals and wrap-up.
    """

    def __init__(self, parent_signals, *args, **kwargs):
        super(EQLogParser, self).__init__()
        # Store constructor arguments (re-used for processing)
        self._stopped = False
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.parent_signals = parent_signals
        self.parent_signals.terminate.connect(self.stop)
        # Can use a timer in the worker thread for periodic checks, or something
        # self.show_status = QTimer()
        # self.show_status.timeout.connect(self.parser_status)
        # self.show_status.start(2000)

    def __del__(self):
        self.stop()

    def stop(self):
        self._stopped = True

    # def parser_status(self):
    #     print("Log parsing thread active...")

    @pyqtSlot()
    def run(self):
        # Static log file path if needed:
        # logfile_path = r"F:\EQLite\Logs\eqlog_Cleri_P1999Green.txt"  # 'r' makes it raw, no need for \\ escapes, thanks!
        # logfile_path = "/home/mlakin/opt/storage/LutrisGames/everquest/Sony/EverQuest/Logs/eqlog_Pescetarian_P1999Green.txt"
        try:
            # Read log file path from local config file:
            with open("eq_logfile.txt", "rt") as f:
                logfile_path = f.readline().strip()
            print(f"Found eq_logfile.txt, using log file location:\n{logfile_path}")
        except Exception:
            print(
                "Unable to read log file location from eq_logfile.txt, create this file for auto-detection"
            )

        zone_pattern = re.compile(r"^\[.*\] You have entered ([\w\s']+)\.$")
        loc_pattern = re.compile(
            r"^\[.*\] Your Location is (\-?\d+\.\d+), (\-?\d+\.\d+), (\-?\d+\.\d+)$"
        )
        logfile = open(logfile_path, "rt")
        with open(logfile_path, "rt") as logfile:
            print("Log parser started...")
            logfile.seek(0, 2)  # Go to the end of the file
            while not self._stopped:
                line = logfile.readline()
                if not line:
                    time.sleep(0.1)  # Sleep briefly
                    continue
                try:
                    new_zone = zone_pattern.findall(line)[0]
                    self.signals.zone.emit(new_zone)
                except IndexError:
                    try:
                        x, y, z = loc_pattern.findall(line)[0]
                        # print(f"x: {x} y: {y} z: {z}") # Log loc to console
                        self.signals.loc.emit((x, y, z))
                    except IndexError:
                        pass
        print("Log parser stopped.")


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.title = "Dude, Where's My Guildies???"
        self.setWindowTitle(self.title)
        outer_layout = QVBoxLayout()
        map_layout = QVBoxLayout()
        data_layout = QVBoxLayout()
        button_layout = QVBoxLayout()

        # label_main = QLabel("Dude, Where's My Guildies???\n")
        label_map = QLabel(self)
        pixmap = QPixmap(r"Maps\Qeynoshills.jpg")
        label_map.setPixmap(pixmap)
        label_map.resize(pixmap.width(), pixmap.height())
        self.resize(pixmap.width(), pixmap.height())
        label_zone = QLabel("Zone:")
        self.label_currentzone = QLabel("")
        label_loc = QLabel("Location:")
        self.label_currentloc = QLabel("")
        button_quit = QPushButton("Quit")
        button_quit.pressed.connect(self.quit_app)
        self.button_terminatelogger = QPushButton("Terminate Log Parser")
        self.button_terminatelogger.pressed.connect(self.terminate_logparser)

        # layout.addWidget(label_main)
        map_layout.addWidget(label_map)
        data_layout.addStretch()
        data_layout.addWidget(label_zone)
        data_layout.addWidget(self.label_currentzone)
        data_layout.addWidget(label_loc)
        data_layout.addWidget(self.label_currentloc)
        button_layout.addWidget(button_quit)
        button_layout.addWidget(self.button_terminatelogger)

        outer_layout.addLayout(map_layout)
        outer_layout.addLayout(data_layout)
        outer_layout.addLayout(button_layout)

        w = QWidget()
        w.setLayout(outer_layout)

        self.setCentralWidget(w)

        self.show()

        self.threadpool = QThreadPool()
        print(
            "Multithreading with maximum %d threads" % self.threadpool.maxThreadCount()
        )

        self.start_workers()

    def update_zone(self, zone_text):
        self.current_zone = zone_text
        self.label_currentzone.setText(zone_text)

    def update_loc(self, loc_tuple):
        self.current_loc = loc_tuple
        x, y, z = loc_tuple
        self.label_currentloc.setText(f"({x}, {y}, {z})")

    def terminate_logparser(self):
        self.button_terminatelogger.setDisabled(True)
        self.logparser_control.terminate.emit()

    def start_workers(self):
        self.logparser_control = ParentSignals()
        self.worker_logfile = EQLogParser(self.logparser_control)
        self.worker_logfile.signals.zone.connect(self.update_zone)
        self.worker_logfile.signals.loc.connect(self.update_loc)
        self.threadpool.start(self.worker_logfile)

    def quit_app(self):
        self.terminate_logparser()
        app.quit()


app = QApplication([1, "-widgetcount"])
window = MainWindow()
sys.exit(app.exec())
