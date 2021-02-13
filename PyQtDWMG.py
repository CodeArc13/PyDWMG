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
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    result
        object data returned from processing, anything

    """

    result = pyqtSignal(object)


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
                    x, y, z = loc_pattern.findall(line)[0]
                    # print(f"x: {x} y: {y} z: {z}") # Log loc to console
                    self.signals.result.emit(f"x: {x} y: {y} z: {z}")
                except IndexError:
                    pass


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        layout = QVBoxLayout()

        self.l = QLabel("Start")
        b = QPushButton("Quit")
        b.pressed.connect(self.quit_app)
        self.t = QPushButton("Terminate Log Parser")
        self.t.pressed.connect(self.terminate_logparser)

        layout.addWidget(self.l)
        layout.addWidget(b)
        layout.addWidget(self.t)

        w = QWidget()
        w.setLayout(layout)

        self.setCentralWidget(w)

        self.show()

        self.threadpool = QThreadPool()
        print(
            "Multithreading with maximum %d threads" % self.threadpool.maxThreadCount()
        )

        self.start_workers()

    def update_label(self, text):
        self.l.setText(text)

    def terminate_logparser(self):
        self.logparser_control.terminate.emit()
        self.t.setDisabled(True)

    def start_workers(self):
        self.logparser_control = ParentSignals()
        self.worker_logfile = EQLogParser(self.logparser_control)
        self.worker_logfile.signals.result.connect(self.update_label)
        self.threadpool.start(self.worker_logfile)

    def quit_app(self):
        self.terminate_logparser()
        sys.exit(app.quit())


app = QApplication([])
window = MainWindow()
sys.exit(app.exec())
