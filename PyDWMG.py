import os
import re
import sys
import csv
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

from PyQt5.QtGui import QPixmap, QPainter


class WorkerSignals(QObject):
    """ Defines the signals available from a running worker thread."""

    zone = pyqtSignal(str)
    loc = pyqtSignal(tuple)


class ParentSignals(QObject):
    """ Defines the signals to pass to a worker thread for parent control """

    terminate = pyqtSignal()


def reverse_readline(filename, buffer_size=1024):
    """A generator that returns the lines of a file in reverse order"""
    SEEK_FILE_END = 2  # seek "whence" value for end of stream

    with open(filename) as fd:
        first_line = None
        offset = 0
        file_size = bytes_remaining = fd.seek(0, SEEK_FILE_END)
        while bytes_remaining > 0:
            offset = min(file_size, offset + buffer_size)
            fd.seek(file_size - offset)
            read_buffer = fd.read(min(bytes_remaining, buffer_size))
            bytes_remaining -= buffer_size
            lines = read_buffer.split("\n")
            if first_line is not None:
                """The first line of the buffer is probably not a complete
                line, so store it and add it to the end of the next buffer.
                Unless there is already a newline at the end of the buffer,
                then just yield it because it is a complete line.
                """
                if read_buffer[-1] != "\n":
                    lines[-1] += first_line
                else:
                    yield first_line
            first_line = lines[0]
            for line_num in range(len(lines) - 1, 0, -1):
                if lines[line_num]:
                    yield lines[line_num]

        if first_line is not None:
            """Current first_line is never yielded in the while loop """
            yield first_line


class Zone:
    def __init__(self, zone_info):
        (
            self.zone_name,
            self.map_filename,
            self.zone_who_name,
            self.zone_alpha_name,
            self.eq_grid_size,
            self.map_grid_size,
            self.offset_x,
            self.offset_y,
        ) = zone_info
        self.eq_grid_size = int(self.eq_grid_size)
        self.map_grid_size = int(self.map_grid_size)
        self.map_scale_factor = self.eq_grid_size / self.map_grid_size
        self.offset_x = float(self.offset_x)
        self.offset_y = float(self.offset_y)

    def __repr__(self):
        return f"Zone({self.zone_name})"


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
        # Read log file path from eq_logfile.txt
        try:
            # Read log file path from local config file:
            with open("eq_logfile.txt", "rt") as f:
                logfile_path = f.readline().strip()
            print(f"Found eq_logfile.txt, using log file location:\n{logfile_path}")
        except Exception:
            print(
                "Unable to read log file location from eq_logfile.txt, create this file for auto-detection"
            )

        # Define regex patterns to use for log line matching
        zone_pattern = re.compile(r"^\[.*\] You have entered ([\w\s']+)\.$")
        loc_pattern = re.compile(
            r"^\[.*\] Your Location is (\-?\d+\.\d+), (\-?\d+\.\d+), (\-?\d+\.\d+)$"
        )
        logfile = open(logfile_path, "rt")

        # Get starting zone before beginning log read loop
        for line in reverse_readline(logfile_path):
            try:
                starting_zone = zone_pattern.findall(line)[0]
                print(f"Found starting zone {starting_zone}")
                self.signals.zone.emit(starting_zone)
                break
            except IndexError:
                pass

        # Start log read loop
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
                        # EQ swaps x and y in its loc printout
                        y, x, z = loc_pattern.findall(line)[0]
                        x, y, z = map(float, [x, y, z])
                        self.signals.loc.emit((x, y, z))
                    except IndexError:
                        pass
        print("Log parser stopped.")


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # INIT STUFF
        app.aboutToQuit.connect(self.quit_app)
        try:
            with open("zone_info.csv") as f:
                zone_csv = csv.reader(f)
                next(zone_csv)  # Skip first line
                self.zones = [Zone(zone_info) for zone_info in zone_csv]
        except FileNotFoundError:
            print("zone_info.csv not found, quitting!")
            sys.exit(1)

        self.title = "Dude, Where's My Guildies???"
        self.setWindowTitle(self.title)
        outer_layout = QVBoxLayout()
        map_layout = QVBoxLayout()
        data_layout = QVBoxLayout()
        button_layout = QVBoxLayout()

        # MAP LABEL
        INITIAL_MAP = "Map_eastcommons.jpg"
        self.label_map = QLabel()
        pixmap = QPixmap(os.path.join(os.getcwd(), "maps", INITIAL_MAP))
        self.label_map.setPixmap(pixmap)
        self.label_map.resize(pixmap.width(), pixmap.height())
        self.resize(pixmap.width(), pixmap.height())

        # BOTTOM TESTING LABELS
        label_zone = QLabel("Zone:")
        self.label_currentzone = QLabel("")
        label_loc = QLabel("Location:")
        self.label_currentloc = QLabel("")
        button_quit = QPushButton("Quit")
        button_quit.pressed.connect(self.quit_app)
        self.button_terminatelogger = QPushButton("Terminate Log Parser")
        self.button_terminatelogger.pressed.connect(self.terminate_logparser)

        # LAYOUT SETUP
        map_layout.addWidget(self.label_map)
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

        self.setMaximumSize(
            outer_layout.geometry().width(), outer_layout.geometry().height()
        )

        self.show()

        self.threadpool = QThreadPool()
        print(
            "Multithreading with maximum %d threads" % self.threadpool.maxThreadCount()
        )

        self.start_workers()

    def get_zone(self, zone_text):
        for zone in self.zones:
            if zone.zone_name == zone_text:
                return zone
            elif zone.zone_who_name == zone_text:
                return zone
        return None

    def update_zone(self, zone_text):
        zone = self.get_zone(zone_text)
        if zone is None:
            self.current_zone = None
            self.label_currentzone.setText(zone_text)
            return None
        self.current_zone = zone
        self.label_currentzone.setText(zone.zone_name)
        pixmap = QPixmap(os.path.join(os.getcwd(), "maps", zone.map_filename))
        self.map_base = pixmap
        self.label_map.setPixmap(pixmap)
        self.label_map.resize(pixmap.width(), pixmap.height())
        self.resize(pixmap.width(), pixmap.height())

    def update_loc(self, loc_tuple):
        try:
            prev_loc = self.current_loc
        except AttributeError:
            pass
        prev_loc = loc_tuple
        new_loc = loc_tuple
        self.current_loc = new_loc
        x, y, z = new_loc
        self.label_currentloc.setText(f"({x}, {y}, {z})")
        if self.current_zone is not None:
            self.draw_map(prev_loc, new_loc)

    def draw_map(self, prev_loc, new_loc):
        px, py, _ = prev_loc
        nx, ny, _ = new_loc
        nx = -nx / self.current_zone.map_scale_factor + self.current_zone.offset_x
        ny = -ny / self.current_zone.map_scale_factor + self.current_zone.offset_y
        new_map = QPixmap(self.map_base)
        painter = QPainter(new_map)
        marker_size = 11
        painter.drawEllipse(
            nx - marker_size / 2, ny - marker_size / 2, marker_size, marker_size
        )
        painter.end()
        self.label_map.setPixmap(new_map)
        self.label_map.resize(new_map.width(), new_map.height())
        self.resize(new_map.width(), new_map.height())

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
