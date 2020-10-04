#log parser basics 101
#get log file location and... read it.




# basic Al Gore's rhythm

# D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt

def main():
    with open('D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt', 'r') as f:
        #read_data = f.read()
            #?set last read length to be the very end of the log
        for line in f:
            print(line, end='')
            print(f.tell())
        #f.closed #not needed for with block
    pass



if __name__ == "__main__":
    main()


