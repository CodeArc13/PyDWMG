# log parser basics 101
# get log file location and... read it.
from pathlib import Path
from time import sleep


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


def get_logsize(filename):
    return Path(filename).stat().st_size


# basic Al Gore's rhythm
""" 'real time' reading (With an adjustable sleep variable!)
    Get the current log file size upon opening
    Periodically check file size to see if it has increased 
    (if time period is fast enough we wont have to worry about reading multiple
     lines from the log as there will only ever be one new line(this should see how
     fast the reverse_readline method can go in the case of a lot of spam to the log :p))
        IF the file has increased in size:
            Read the last line from the log and print it
            Update current file size
            Sleep for a bit

"""


# D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt


def main():
    log = "D:\\Games\\EQLite\\Logs\\eqlog_Cleri_P1999Green.txt"
    # print(next(reverse_readline(log)))  # print the last line
    current_size = get_logsize(log)
    last_readline = ""
    while True:  # make escapable!
        if current_size != get_logsize(log):
            last_readline = next(reverse_readline(log))
            print(last_readline)
            current_size = get_logsize(log)
        # sleep here
        sleep(0.1)
        """ notes from experimentation. Half second sleep caught 65 out of 82 spammed /locs
            0.1 caught 125 out of 125 spammed /locs """

    # i = 0
    # for line in reverse_readline(log):
    #     if i >= 10:
    #         break
    #     else:
    #         print(line, end="\n")
    #         i += 1

    #     # f.closed #not needed for with block
    #      """print(f.tell())


if __name__ == "__main__":
    main()
