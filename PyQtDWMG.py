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

import time


class WorkerSignals(QObject):
    """ Defines the signals available from a running worker thread."""

    zone = pyqtSignal(str)
    loc = pyqtSignal(tuple)


class ParentSignals(QObject):
    terminate = pyqtSignal()


class EQLogParser(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    def __init__(self, parent_signals, *args, **kwargs):
        super(EQLogParser, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.parent_signals = parent_signals
        self._stopped = False
        self.parent_signals.terminate.connect(self.stop)
        self.show_status = QTimer()
        self.show_status.timeout.connect(self.parser_status)
        self.show_status.start(2000)

    def __del__(self):
        self._stopped = True

    def stop(self):
        self._stopped = True

    def parser_status(self):
        print("Log parsing thread active...")

    @pyqtSlot()
    def run(self):
        # logfile = r"D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt"  # 'r' makes it raw, no need for \\ escapes, thanks!
        logfile_path = "/home/mlakin/opt/storage/LutrisGames/everquest/Sony/EverQuest/Logs/eqlog_Pescetarian_P1999Green.txt"
        zone_pattern = re.compile(r"^\[.*\] You have entered ([\w\s']+)\.$")
        loc_pattern = re.compile(
            r"^\[.*\] Your Location is (\-?\d+\.\d+), (\-?\d+\.\d+), (\-?\d+\.\d+)$"
        )
        print("starting timer...")
        logfile = open(logfile_path, "rt")
        with open(logfile_path, "rt") as logfile:
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


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        layout = QVBoxLayout()

        label_main = QLabel("Dude, Where's My Guildies???\n")
        label_zone = QLabel("Zone:")
        self.label_currentzone = QLabel("")
        label_loc = QLabel("Location:")
        self.label_currentloc = QLabel("")
        button_quit = QPushButton("Quit")
        button_quit.pressed.connect(self.quit_app)
        self.button_terminatelogger = QPushButton("Terminate Log Parser")
        self.button_terminatelogger.pressed.connect(self.terminate_logparser)

        layout.addWidget(label_main)
        layout.addWidget(label_zone)
        layout.addWidget(self.label_currentzone)
        layout.addWidget(label_loc)
        layout.addWidget(self.label_currentloc)
        layout.addWidget(button_quit)
        layout.addWidget(self.button_terminatelogger)

        w = QWidget()
        w.setLayout(layout)

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
        sys.exit(app.quit())


app = QApplication([])
window = MainWindow()
sys.exit(app.exec())
