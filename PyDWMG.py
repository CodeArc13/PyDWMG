# log parser basics 101
# get log file location and... read it.


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


# basic Al Gore's rhythm

# D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt


def main():
    with open("D:\\Games\\EQLite\\Logs\\eqlog_Cleri_P1999Green.txt", "r") as f:
        # read_data = f.read()
        # ?set last read length to be the very end of the log
        for line in f:
            print(line, end="")

        # f.closed #not needed for with block
        print(f.tell())
    pass


if __name__ == "__main__":
    main()
