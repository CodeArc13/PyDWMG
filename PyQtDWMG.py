import pdb
import re
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
    pyqtSlot,
    pyqtSignal,
)

import time


def follow(thefile):
    thefile.seek(0, 2)  # Go to the end of the file
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)  # Sleep briefly
            continue
        yield line


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    """

    result = pyqtSignal(object)


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.kwargs["result_callback"] = self.signals.result

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """
        self.fn(*self.args, **self.kwargs)


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        layout = QVBoxLayout()

        self.l = QLabel("Start")
        b = QPushButton("Quit")
        b.pressed.connect(self.quit_app)

        layout.addWidget(self.l)
        layout.addWidget(b)

        w = QWidget()
        w.setLayout(layout)

        self.setCentralWidget(w)

        self.show()

        self.threadpool = QThreadPool()
        print(
            "Multithreading with maximum %d threads" % self.threadpool.maxThreadCount()
        )

        self.start_workers()

    def check_logfile(self, result_callback):
        # logfile = r"D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt"  # 'r' makes it raw, no need for \\ escapes, thanks!
        logfile_path = "/home/mlakin/opt/storage/LutrisGames/everquest/Sony/EverQuest/Logs/eqlog_Pescetarian_P1999Green.txt"
        zone_pattern = re.compile(r"^\[.*\] You have entered ([\w\s']+)\.$")
        loc_pattern = re.compile(
            r"^\[.*\] Your Location is (\-?\d+\.\d+), (\-?\d+\.\d+), (\-?\d+\.\d+)$"
        )
        logfile = open(logfile_path, "rt")
        for line in follow(logfile):
            try:
                x, y, z = loc_pattern.findall(line)[0]
                print(f"x: {x} y: {y} z: {z}")
                result_callback.emit(f"x: {x} y: {y} z: {z}")
            except IndexError:
                pass

    def update_label(self, text):
        self.l.setText(text)

    def start_workers(self):
        worker_logfile = Worker(self.check_logfile)
        worker_logfile.signals.result.connect(self.update_label)
        self.threadpool.start(worker_logfile)

    def quit_app(self):
        self.threadpool.waitForDone(msecs=1000)
        app.quit()

    # self.l.setText(self.message)
    # worker = Worker()
    # self.threadpool.start(worker)


app = QApplication([])
window = MainWindow()
app.exec_()
