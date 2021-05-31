import os
import re
import sys
import csv
import time
import math
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication,
    QStyle,
    QWidget,
    QPushButton,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QMessageBox,
)

from PyQt5.QtCore import (
    Qt,
    QObject,
    QRunnable,
    QThreadPool,
    pyqtSlot,
    pyqtSignal,
)

from PyQt5.QtGui import QPixmap, QPainter, QPen, QIcon


class LogParserSignals(QObject):
    """ Defines the signals available from a running worker thread."""

    zone = pyqtSignal(str)
    loc = pyqtSignal(tuple)


class LogScannerSignals(QObject):
    """ Defines the signals available from a running worker thread."""

    logfile = pyqtSignal(Path)


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


class EQLogScanner(QRunnable):
    """
    Worker thread, inherits from QRunnable to handler worker thread setup,
    signals and wrap-up.
    """

    def __init__(self, parent_signals, eqlog_dir, *args, **kwargs):
        super(EQLogScanner, self).__init__()
        # Store constructor arguments (re-used for processing)
        self._stopped = False
        self.args = args
        self.kwargs = kwargs
        self.signals = LogScannerSignals()
        self.parent_signals = parent_signals
        self.parent_signals.terminate.connect(self.stop)
        self.eqlogscan_dir = eqlog_dir
        self.current_logfile = None

    def __del__(self):
        self.stop()

    def stop(self):
        self._stopped = True

    @pyqtSlot()
    def run(self):
        """ Scan log dir to find most recently modified file. """

        print(f"Scanner thread started for dir: {self.eqlogscan_dir}...")
        eqlog_format = "eqlog_*.txt"
        # Scan every 2 seconds
        scan_interval = scan_counter = 20
        while not self._stopped:
            if scan_counter < scan_interval:
                scan_counter += 1
                time.sleep(0.1)
                continue
            scan_counter = 0
            eqlog_files = Path(self.eqlogscan_dir).glob(eqlog_format)
            last_modified = max(
                eqlog_files, default=None, key=lambda f: f.stat().st_mtime
            )
            if last_modified != self.current_logfile and last_modified is not None:
                # Store resolved path as current logfile and emit
                self.current_logfile = last_modified.resolve()
                self.signals.logfile.emit(self.current_logfile)

        print(f"Scanner thread stopped for dir: {self.eqlogscan_dir}.")


class EQLogParser(QRunnable):
    """
    Worker thread, inherits from QRunnable to handler worker thread setup,
    signals and wrap-up.
    """

    def __init__(self, parent_signals, log_file, *args, **kwargs):
        super(EQLogParser, self).__init__()
        # Store constructor arguments (re-used for processing)
        self._stopped = False
        self.args = args
        self.kwargs = kwargs
        self.signals = LogParserSignals()
        self.parent_signals = parent_signals
        self.parent_signals.terminate.connect(self.stop)
        self.log_file = log_file
        # Can use a timer in the worker thread for periodic checks, or something
        # self.show_status = QTimer()
        # self.show_status.timeout.connect(self.parser_status)
        # self.show_status.start(2000)

    def __del__(self):
        self.stop()

    def stop(self):
        self._stopped = True

    @pyqtSlot()
    def run(self):

        """ Parse log file for updated zone and loc data. """
        print(f"Parser thread started for file: {self.log_file}...")
        logfile_path = self.log_file
        # Define regex patterns to use for log line matching
        zone_pattern = re.compile(r"^\[.*\] You have entered ([\w\s']+)\.$")
        loc_pattern = re.compile(
            r"^\[.*\] Your Location is (\-?\d+\.\d+), (\-?\d+\.\d+), (\-?\d+\.\d+)$"
        )

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
        print(f"Parser thread stopped for file: {self.log_file}.")


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

        self.title = "Dude, Where's My Guild???"
        self.setWindowTitle(self.title)
        self.setWindowIcon(QIcon(os.path.join("icons", "DWMG.png")))
        outer_layout = QVBoxLayout()
        tool_layout = QHBoxLayout()
        map_layout = QVBoxLayout()
        data_layout = QVBoxLayout()
        button_layout = QVBoxLayout()

        # WINDOW VARIABLES, could be used for persistance between sessions
        self.on_top = False

        # TOOL BAR
        self.button_log_folder = QPushButton()
        self.button_log_folder.setIcon(
            QApplication.style().standardIcon(QStyle.SP_DialogOpenButton)
        )
        self.button_log_folder.setToolTip("Select EQ or log folder")
        self.button_log_folder.pressed.connect(self.select_eqlog_dir)
        self.button_on_top = QPushButton()
        self.button_on_top.setIcon(QIcon(os.path.join("icons", "NotAlwaysOnTop.png")))
        self.button_on_top.setToolTip("Always on top")
        self.button_on_top.pressed.connect(self.always_on_top)

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
        label_prevloc = QLabel("Previous Location:")
        self.label_prevloc = QLabel("")
        button_quit = QPushButton("Quit")
        button_quit.pressed.connect(self.quit_app)

        # LAYOUT SETUP
        tool_layout.addWidget(self.button_log_folder, 0, Qt.AlignLeft)
        tool_layout.addWidget(self.button_on_top, 1, Qt.AlignLeft)
        map_layout.addWidget(self.label_map)
        data_layout.addStretch()
        data_layout.addWidget(label_zone)
        data_layout.addWidget(self.label_currentzone)
        data_layout.addWidget(label_loc)
        data_layout.addWidget(self.label_currentloc)
        data_layout.addWidget(label_prevloc)
        data_layout.addWidget(self.label_prevloc)
        button_layout.addWidget(button_quit)

        outer_layout.addLayout(tool_layout)
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

        self.get_eqlog_dir()
        try:
            self.start_logscanner(self.eqlog_dir)
        except AttributeError:
            print("Error: No eq log dir defined, unable to start log scanner thread")

    def get_zone(self, zone_text):
        for zone in self.zones:
            if zone.zone_name == zone_text:
                return zone
            elif zone.zone_who_name == zone_text:
                return zone
        return None

    def update_zone(self, zone_text):
        # Unset saved loc, as it's no longer valid.
        self.current_loc = None
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

    def update_loc(self, new_loc):
        prev_loc = self.current_loc
        self.current_loc = new_loc
        # Reverse locs to display them in EQ loc format.
        self.label_currentloc.setText(f"{tuple(reversed(new_loc))}")
        if prev_loc is not None:
            self.label_prevloc.setText(f"{tuple(reversed(prev_loc))}")
        if self.current_zone is not None:
            self.draw_map(new_loc, prev_loc)

    def draw_arrow(self, painter, start_point, end_point, size, draw_x=True):
        """ Draw arrow of given size using painter object. """
        start_x, start_y = start_point
        end_x, end_y = end_point

        # Calculate heading vectors.
        x_vec = start_x - end_x
        y_vec = start_y - end_y

        # Calculate magnitude (length) of vector.
        mag = math.sqrt((x_vec ** 2) + (y_vec ** 2))

        # Calculate unit vectors.
        try:
            x_unit_vec = x_vec / mag
            y_unit_vec = y_vec / mag
        except ZeroDivisionError:
            x_unit_vec = x_vec
            y_unit_vec = y_vec

        # Calculate heading bar start for arrow head.
        hb_start_x = round(end_x - (x_unit_vec * size))
        hb_start_y = round(end_y - (y_unit_vec * size))
        hb_start_point = (hb_start_x, hb_start_y)

        # Calculate arrow head.
        arrow_start_point = tuple(
            map(round, self.rotate_point(*end_point, *hb_start_point, 45))
        )
        arrow_end_point = tuple(
            map(round, self.rotate_point(*end_point, *hb_start_point, -45))
        )

        if draw_x:
            # Calculate heading bar end for X.
            hb_end_x = round(end_x + (x_unit_vec * size))
            hb_end_y = round(end_y + (y_unit_vec * size))
            hb_end_point = (hb_end_x, hb_end_y)

            # Calculate cross bar for X.
            cb_start_point = tuple(
                map(round, self.rotate_point(*hb_end_point, *end_point, 90))
            )
            cb_end_point = tuple(
                map(round, self.rotate_point(*hb_end_point, *end_point, 270))
            )

            # Draw red X (marks the spot).
            painter.setPen(QPen(Qt.red, 2))
            painter.drawLine(*hb_start_point, *hb_end_point)
            painter.drawLine(*cb_start_point, *cb_end_point)
        # Draw arrow head.
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(*arrow_start_point, *hb_start_point)
        painter.drawLine(*arrow_end_point, *hb_start_point)
        painter.drawLine(*arrow_start_point, *arrow_end_point)

    def draw_circle(self, painter, point, size):
        """ Draw circle of given size using painter object. """
        x, y = point
        painter.setPen(QPen(Qt.red, 2))
        painter.drawEllipse(
            round(x - size / 2), round(y - size / 2), size, size,
        )

    def draw_map(self, new_loc, prev_loc):
        """ Draw marker on map based on current and previous location """
        # Create a copy of the current map to use for drawing a new map.
        new_map = QPixmap(self.map_base)
        painter = QPainter(new_map)

        # Set marker sizes to odd numbers so shape is even around center pixel.
        circle_marker_size = 11
        cross_marker_size = 9

        # Scale locs to map size using current zone scale factor and offsets.
        map_scale_factor = self.current_zone.map_scale_factor
        map_offset_x = self.current_zone.offset_x
        map_offset_y = self.current_zone.offset_y
        new_x, new_y, _ = new_loc
        scaled_new_x = -new_x / map_scale_factor + map_offset_x
        scaled_new_y = -new_y / map_scale_factor + map_offset_y
        scaled_new_loc = (scaled_new_x, scaled_new_y)
        if prev_loc is not None:
            prev_x, prev_y, _ = prev_loc
            # Abort map drawing if new and prev locs are the same.
            if (new_x, new_y) == (prev_x, prev_y):
                painter.end()
                return
            scaled_prev_x = -prev_x / map_scale_factor + map_offset_x
            scaled_prev_y = -prev_y / map_scale_factor + map_offset_y
            scaled_prev_loc = (scaled_prev_x, scaled_prev_y)

        # Check if new loc is within the map image size.
        map_width = new_map.width()
        map_height = new_map.height()
        if 0 < scaled_new_x < map_width and 0 < scaled_new_y < map_height:
            if prev_loc is not None:
                # Use previous loc to draw an arrow showing movement direction.
                self.draw_arrow(
                    painter,
                    scaled_prev_loc,
                    scaled_new_loc,
                    cross_marker_size,
                    draw_x=True,
                )
            else:
                # Draw a circle at the new location.
                self.draw_circle(painter, scaled_new_loc, circle_marker_size)
        else:
            # Adjust new loc so it's within the map image at the closest edge.
            # Set x to the center of a circle at the map edge, and make the
            # same adjustment to prev loc to maintain accurate movement vector.
            if scaled_new_x < 0:
                if prev_loc is not None:
                    x_shift = scaled_new_x
                    scaled_prev_x -= x_shift - circle_marker_size / 2
                scaled_new_x = circle_marker_size / 2
            elif scaled_new_x > map_width:
                if prev_loc is not None:
                    x_shift = scaled_new_x - map_width
                    scaled_prev_x -= x_shift + circle_marker_size / 2
                scaled_new_x = map_width - circle_marker_size / 2
            if scaled_new_y < 0:
                if prev_loc is not None:
                    y_shift = scaled_new_y
                    scaled_prev_y -= y_shift - circle_marker_size / 2
                scaled_new_y = circle_marker_size / 2
            elif scaled_new_y > map_height:
                if prev_loc is not None:
                    y_shift = scaled_new_y - map_height
                    scaled_prev_y -= y_shift + circle_marker_size / 2
                scaled_new_y = map_height - circle_marker_size / 2

            # Update tuple with new values and draw circle at the map edge.
            scaled_new_loc = (scaled_new_x, scaled_new_y)
            self.draw_circle(painter, scaled_new_loc, circle_marker_size)

            if prev_loc is not None:
                scaled_prev_loc = (scaled_prev_x, scaled_prev_y)
                # Draw arrow head (without X) to show direction with circle.
                self.draw_arrow(
                    painter,
                    scaled_prev_loc,
                    scaled_new_loc,
                    cross_marker_size,
                    draw_x=False,
                )
        painter.end()
        self.label_map.setPixmap(new_map)
        self.label_map.resize(map_width, map_height)
        self.resize(map_width, map_height)

    def rotate_point(self, end_x, end_y, start_x, start_y, degrees):
        """ Return a point after rotating it given end, start, and degrees. """
        rotated_x = start_x + (
            math.cos(self.d_to_r(degrees)) * (end_x - start_x)
            - math.sin(self.d_to_r(degrees)) * (end_y - start_y)
        )
        rotated_y = start_y + (
            math.sin(self.d_to_r(degrees)) * (end_x - start_x)
            + math.cos(self.d_to_r(degrees)) * (end_y - start_y)
        )
        return (rotated_x, rotated_y)

    def d_to_r(self, angle):
        """ Return the radian equivalent of degrees. """
        return angle / 180 * math.pi

    def terminate_logparser(self):
        """ Stop the log parsing thread. """
        try:
            self.logparser_control.terminate.emit()
        except AttributeError:
            pass

    def terminate_logscanner(self):
        """ Stop the log dir scanning thread. """
        try:
            self.logscanner_control.terminate.emit()
        except AttributeError:
            pass

    def start_logparser(self, log_file):
        """ Start a thread to parse log file for mapping updates. """
        self.logparser_control = ParentSignals()
        self.worker_logparser = EQLogParser(self.logparser_control, log_file)
        self.worker_logparser.signals.zone.connect(self.update_zone)
        self.worker_logparser.signals.loc.connect(self.update_loc)
        self.threadpool.start(self.worker_logparser)

    def start_logscanner(self, eqlog_dir):
        """ Start a thread to scan log dir for updated log files. """
        self.logscanner_control = ParentSignals()
        self.worker_logscanner = EQLogScanner(self.logscanner_control, eqlog_dir)
        self.worker_logscanner.signals.logfile.connect(self.change_log_file)
        self.threadpool.start(self.worker_logscanner)

    def change_log_file(self, new_file):
        """ Change log file being parsed. """
        self.terminate_logparser()
        self.start_logparser(new_file)
        print(f"Changed log file to {new_file}")

    def get_eqlog_dir(self):
        """ Get EQ log dir from saved app settings. """
        try:
            # Read log file path from local config file:
            with open("eq_logfile.txt", "rt") as f:
                eq_logfile_path = f.readline().strip()
            print(f"Found eq_logfile.txt, using eq log directory:\n {eq_logfile_path}")
        except Exception:
            print(
                "Unable to read log file location from eq_logfile.txt, "
                "create this file for auto-detection"
            )
        logfile_path = Path(eq_logfile_path)
        if Path.is_dir(logfile_path):
            self.eqlog_dir = Path(logfile_path)
        else:
            print(f"Error: This path is not a directory - {eq_logfile_path}")

    def select_eqlog_dir(self):
        """ Show a dialog box for the user to select their EQ log folder. """

        def contains_eqlogfiles(folder_path) -> bool:
            """ Check if the selected folder contains EQ log files. """
            try:
                next(folder_path.glob("eqlog_*.txt"))
                return True
            except StopIteration:
                return False

        verified_logs_path = None
        while verified_logs_path is None:
            # Present dialog box to select logs folder
            selected_folder = QFileDialog.getExistingDirectory(
                caption="Select EQ Folder or Logs Folder",
                options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )
            if selected_folder == "":
                # User pressed Cancel, close dialog
                return
            else:
                selected_folder_path = Path(selected_folder)
                if selected_folder_path == self.eqlog_dir:
                    currentdir_message = (
                        "You've selected the log folder already in use."
                        "  If you want to change the log directory, "
                        " please select a different folder."
                    )
                    QMessageBox.warning(self, "Notice", currentdir_message)
                if selected_folder_path.joinpath("eqgame.exe").is_file():
                    # EQ directory selected, check for valid Logs folder
                    eqdir_logs_path = selected_folder_path.joinpath("Logs")
                    if contains_eqlogfiles(eqdir_logs_path):
                        verified_logs_path = eqdir_logs_path
                # Check if selected folder contains EQ log files
                if contains_eqlogfiles(selected_folder_path):
                    verified_logs_path = selected_folder_path
                else:
                    nologs_message = (
                        "Please select either your EQ folder or the log"
                        " folder inside it and ensure you have logging"
                        " enabled and logs in the log folder."
                    )
                    # Popup error and have user select another folder
                    QMessageBox.warning(self, "Error", nologs_message)
        # Save new log directory
        self.eqlog_dir = verified_logs_path
        with open("eq_logfile.txt", "w") as f:
            f.write(str(self.eqlog_dir))
        # Re-start log scanner
        self.terminate_logscanner()
        self.start_logscanner(self.eqlog_dir)

    def always_on_top(self):
        """ Toggle always on top window setting. """
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowStaysOnTopHint)
        if self.on_top is True:
            self.on_top = False
            self.button_on_top.setIcon(
                QIcon(os.path.join("icons", "NotAlwaysOnTop.png"))
            )
        else:
            self.on_top = True
            self.button_on_top.setIcon(QIcon(os.path.join("icons", "AlwaysOnTop.png")))
        self.show()

    def quit_app(self):
        """ Stop any started threads before quitting the app window. """
        self.terminate_logparser()
        self.terminate_logscanner()
        app.quit()


app = QApplication([1, "-widgetcount"])
window = MainWindow()
sys.exit(app.exec())
