#log parser basics 101
#get log file location and... read it.




# basic Al Gore's rhythm

# D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt

def main():
    with open('D:\Games\EQLite\Logs\eqlog_Cleri_P1999Green.txt', 'r') as f:
        #f.seek(0, 2) #go to end of file #set last read length to be the very end of the log
        #read_data = f.readline()
        #print(read_data)
        print(f.tell())
        for line in f:
            print(line, end='')
        #    print(f.tell())
        print(f.tell())
        #f.closed #not needed for with block
    pass



if __name__ == "__main__":
    main()


