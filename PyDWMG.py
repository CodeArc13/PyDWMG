import io
import re
import sys
import time
import numpy
import PySimpleGUI as sg  # our current GUI packge, using for its apparent abilities to be transparent and be borderless
from pathlib import Path
from PIL import Image, ImageTk

TRANSPARENCY = 0.4  # how transparent the window looks. 0 = invisible, 1 = normal window

POLL_FREQUENCY = 100  # how often to update graphs in milliseconds

# colors = ("#23a0a0", "#56d856", "#be45be", "#5681d8", "#d34545", "#BE7C29")


def reverse_readline(filename, skip=None, buffer_size=1024):
    """A generator that returns the lines of a file in reverse order"""
    SEEK_FILE_END = 2  # seek "whence" value for end of stream

    with open(filename) as fd:
        first_line = None
        offset = 0
        file_size = buffer_size = fd.seek(0, SEEK_FILE_END)
        if skip is not None:
            bytes_remaining = buffer_size = file_size - skip
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


def get_logsize(filename):
    return Path(filename).stat().st_size


def update_window(wnd, elem_key, value):  # I think this is what you mean by decoupling
    wnd.element(elem_key).Update(value)


def mouse_over(wnd, e):  # takes window and event
    if e == "Enter":
        print(e)
        wnd.alpha_channel = 1  # make opaque
    if e == "Leave":
        print(e)
        wnd.alpha_channel = TRANSPARENCY  # this will be changed for a variable


def get_img_data(f, maxsize=(1200, 850), first=False):
    """Generate image data using PIL"""
    img = Image.open(f)
    img.thumbnail(maxsize)
    if first:  # tkinter is inactive the first time
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        del img
        return bio.getvalue()
    return ImageTk.PhotoImage(img)


# [Thu Feb 14 12:36:32 2013] Your Location is 4027.73, -2795.26, -56.74
# Old Regex("^(\D{4}\s\D{3}\s\d{2}\s\d{2}:\d{2}:\d{2}\s\d{4}] Your Location is)")
# is the new slicing Regex faster than this?
# D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt


def main(location):
    # def Txt(text, **kwargs): # somones elses code, might be good
    #     return sg.Text(text, font=("Helvetica 8"), **kwargs)

    map_filename = "Qeynoshills.jpg"

    log = r"D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt"  # 'r' makes it raw, no need for \\ escapes, thanks!
    # log = "/home/mlakin/opt/storage/LutrisGames/everquest/Sony/EverQuest/Logs/eqlog_Mezr_P1999Green.txt"
    zone_pattern = re.compile(r"^\[.*\] You have entered ([\w\s']+)\.$")
    loc_pattern = re.compile(
        r"^\[.*\] Your Location is (\-?\d+\.\d+), (\-?\d+\.\d+), (\-?\d+\.\d+)$"
    )
    previous_log_size = 0
    current_loc = previous_loc = None

    sg.theme("Black")
    sg.set_options(element_padding=(0, 0), margins=(1, 1), border_width=0)

    # Red X graphic
    red_x = "R0lGODlhEAAQAPeQAIsAAI0AAI4AAI8AAJIAAJUAAJQCApkAAJoAAJ4AAJkJCaAAAKYAAKcAAKcCAKcDA6cGAKgAAKsAAKsCAKwAAK0AAK8AAK4CAK8DAqUJAKULAKwLALAAALEAALIAALMAALMDALQAALUAALYAALcEALoAALsAALsCALwAAL8AALkJAL4NAL8NAKoTAKwbAbEQALMVAL0QAL0RAKsREaodHbkQELMsALg2ALk3ALs+ALE2FbgpKbA1Nbc1Nb44N8AAAMIWAMsvAMUgDMcxAKVABb9NBbVJErFYEq1iMrtoMr5kP8BKAMFLAMxKANBBANFCANJFANFEB9JKAMFcANFZANZcANpfAMJUEMZVEc5hAM5pAMluBdRsANR8AM9YOrdERMpIQs1UVMR5WNt8X8VgYMdlZcxtYtx4YNF/btp9eraNf9qXXNCCZsyLeNSLd8SSecySf82kd9qqc9uBgdyBgd+EhN6JgtSIiNuJieGHhOGLg+GKhOKamty1ste4sNO+ueenp+inp+HHrebGrefKuOPTzejWzera1O7b1vLb2/bl4vTu7fbw7ffx7vnz8f///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAJAALAAAAAAQABAAAAjUACEJHEiwYEEABniQKfNFgQCDkATQwAMokEU+PQgUFDAjjR09e/LUmUNnh8aBCcCgUeRmzBkzie6EeQBAoAAMXuA8ciRGCaJHfXzUMCAQgYooWN48anTokR8dQk4sELggBhQrU9Q8evSHiJQgLCIIfMDCSZUjhbYuQkLFCRAMAiOQGGLE0CNBcZYmaRIDLqQFGF60eTRoSxc5jwjhACFWIAgMLtgUocJFy5orL0IQRHAiQgsbRZYswbEhBIiCCH6EiJAhAwQMKU5DjHCi9gnZEHMTDAgAOw=="

    # map_elem = sg.Image(data=get_img_data(map_filename, first=True))
    map_elem = sg.Graph(
        canvas_size=(400, 400),
        graph_bottom_left=(0, 0),
        graph_top_right=(400, 400),
        background_color="black",
        key="map_graph",
    )

    layout = [
        [
            sg.Button(
                image_data=red_x,
                button_color=("black", "black"),
                key="Exit",
                tooltip="Closes window",
            ),
        ],
        [sg.Text("Zone", key="zone", size=(30, 1))],
        [sg.Text("Current Loc", key="current_loc", size=(30, 1))],
        [sg.Text("Previous Loc", key="previous_loc", size=(30, 1))],
        [map_elem],
    ]

    # Create Window
    window = sg.Window(
        "PyDWMG",
        layout,
        keep_on_top=True,
        auto_size_buttons=False,
        grab_anywhere=True,
        no_titlebar=False,
        default_button_element_size=(12, 1),
        return_keyboard_events=True,
        alpha_channel=TRANSPARENCY,
        use_default_focus=False,
        finalize=True,
        location=location,
    )

    map_graph = window.Element("map_graph")

    window.bind("<Enter>", "Enter")
    window.bind("<Leave>", "Leave")

    map_graph.DrawImage(filename=map_filename, location=(0, 400))
    map_graph.DrawRectangle((200, 200), (250, 300), line_color="red")

    # main loop
    while True:
        event, values = window.read(
            timeout=POLL_FREQUENCY
        )  # loop throttle control, tested and seems to run code in while loop at the desired interval
        if event in (sg.WIN_CLOSED, "Exit"):
            break

        new_log_size = get_logsize(log)
        if new_log_size != previous_log_size:
            loc1 = loc2 = new_zone = None
            #            file_offset = new_log_size - previous_log_size
            for line in reverse_readline(log, skip=previous_log_size):
                try:
                    new_zone = zone_pattern.findall(line)[0]
                    current_loc = previous_loc = None
                    update_window(window, "zone", new_zone)
                    update_window(window, "current_loc", "no loc")
                    update_window(window, "previous_loc", "no loc")
                    print(f"Zone: {new_zone}")
                    break
                except IndexError:
                    if loc1 is None or loc2 is None:
                        try:
                            x, y, z = loc_pattern.findall(line)[0]
                            if loc1 is None:
                                loc1 = (x, y, z)
                            else:
                                loc2 = (x, y, z)
                        except IndexError:
                            pass
            if loc2 is not None:
                # two locs, set current and previous:
                current_loc = loc1
                previous_loc = loc2
                update_window(window, "current_loc", current_loc)
                update_window(window, "previous_loc", previous_loc)
                print(f"Current loc: {current_loc}\nPrevious loc: {previous_loc}")

            elif loc1 is not None:
                # only one loc, save current as previous and set new current:
                previous_loc = current_loc
                current_loc = loc1
                update_window(window, "current_loc", current_loc)
                update_window(window, "previous_loc", previous_loc)
                print(f"Current loc: {current_loc}\nPrevious loc: {previous_loc}")

            previous_log_size = new_log_size

        # mouse over here
        mouse_over(window, event)
    window.close()

    # sleep here
    # sleep(0.1) # being controlled from gui poll timer
    """ notes from experimentation. Half second sleep caught 65 out of 82 spammed /locs
            0.1 caught 125 out of 125 spammed /locs """


if __name__ == "__main__":
    # when invoking this program, if a location is set on the command line, then the window will be created there. Use x,y with no ( )
    if len(sys.argv) > 1:
        location = sys.argv[1].split(",")
        location = (int(location[0]), int(location[1]))
    else:
        location = (None, None)
    main(location)