# log parser basics 101
# get log file location and... read it.
from pathlib import Path
from time import sleep
import re


""" New mission for you! We need a new def that works like this reverse one 
with the buffering and starting towards the end but needs to save its last read location 
and then use that as a starting location for the next read.
The reason for this is so we can get lines from the last location in forward order,
not reverse like we currently have, and the reason for this is so we can increase the sleep time 
on the main loop without starting to miss log updates.
(This maybe overkill, as it works fine with a 0.1 second pause using next() with the current reverse def
 although I have not tested it with lots of log spam like in EC, 
 but this is the same sleep time as the full VB code, and that has worked on multiple computers.)

The current reverse one will be perfect for initialising characters and map switching, so that the data is 
instantly displayed.

"""


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
        IF the file has i ncreased in size:
            Read the last line from the log and print it
            Update current file size
        Sleep for a bit
"""
# [Thu Feb 14 12:36:32 2013] Your Location is 4027.73, -2795.26, -56.74
# Old Regex("^(\D{4}\s\D{3}\s\d{2}\s\d{2}:\d{2}:\d{2}\s\d{4}] Your Location is)")
# is the new slicing Regex faster than this?
# D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt


def main():
    log = "D:\\Games\\EQLite\\Logs\\eqlog_Cleri_P1999Green.txt"
    pattern = re.compile("Your Location is")
    # print(next(reverse_readline(log)))  # print the last line
    current_size = get_logsize(log)
    # last_readline = ""
    while True:  # make escapable!
        if current_size != get_logsize(log):
            last_readline = next(reverse_readline(log))
            if pattern.fullmatch(last_readline, 27, 43):
                print(last_readline)

            """ broken multi-line read code (see long comment up top) """
            # last_loc = ""
            # while True:  # make escapable!
            #     if current_size != get_logsize(log):
            #         readback_limit = 10  # prevents too much looping through spam
            #         line_num = 0
            #         for line in reverse_readline(log):
            #             # ?Loop and break till we find the last loc(multiline read)

            #             if line_num <= readback_limit:
            #                 if line == last_loc:  # break if same line found
            #                     break
            #                 elif (
            #                     pattern.fullmatch(line, 27, 43) and line != last_loc
            #                 ):  # at position of 'You Location is', is this faster/easier?
            #                     print(line, end="\n")
            #                     last_loc = line
            #                     # break  # if there is any pattern match then break
            #                 line_num += 1
            #             else:
            #                 break

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
