#!/usr/bin/python3

import time
import csv
import sys

def crc32(word: int) -> int: # calcola il CRC di una riga da 32 bit del pacchetto
    step_1 = (word >> 16) ^ (word & 0xFFFF)
    step_2 = (step_1 >> 8) ^ (step_1 & 0xFF)
    return (step_2 >> 4) ^ (step_2 & 0xF)

def crc323check(arr) -> str:     # prende in input un array contenente le varie righe del
    testvalue = (arr[-1] & 0xF)   # pacchetto e verifica il CRC
    crc = crc32(arr[0])
    for i in range(1, len(arr)):
        if i != len(arr)-1:
            crc = crc32(arr[i]) ^ crc
        else:
            crc = crc32(arr[i] & 0xFFFFFFF0) ^ crc
    if crc == testvalue:
        return 'Correct'
    else:
        return 'Transmission error'

def convert():
    STATUS = 0
    Date = time.strftime("%Y-%m-%d")
    single_event = []
    buffer_array = []
    buffer_matrix = []
    Timestamp_old = [0] * 19
    file_name = 'test.csv'

    with open(file_name, 'w') as outFile:
        writer = csv.writer(outFile)
        header = ["Channel", "Event type", "Subhits number", "Energy", "Coarse[ns]", "TDC start[ns]",
                  "TDC stop[ns]", "ToT[ns]", "Timestamp[ns]", "Delta Time[ns]", "Date", "FIFO State", "CRC"]
        writer.writerow(header)

    print('Start conversion')
    NumEvent = 0
    with open(''.join(sys.argv[1]), 'r') as f:
        for line in f:
            try:
                data = int(line, 2)
            except ValueError:
                print("non-ASCII character")
                STATUS = 0
                single_event.clear()
                pass
            if ((data >> 30) & 0X3) == 0X2:  # 10 head bit
                STATUS = 1
                single_event.append(data)
            elif STATUS == 1:
                if ((data >> 30) & 0X3) == 0: # 00 hit message
                    single_event.append(data)
                    STATUS = 2
                else:
                    single_event.clear()
                    STATUS = 0
            elif STATUS == 2:
                if data == 0xFC000000:
                    print('Timeout FAZIA')
                    STATUS = 0
                elif ((data >> 30) & 0X3) == 0X01:  # 11 subhit
                    continue
                elif ((data >> 30) & 0X3) == 0X03: # 11 tail message
                    single_event.append(data)
                    if len(single_event) == 3:
                        channel = int(((single_event[0] >> 22) & 0X1F))
                        TDCstart = (single_event[1] >> 11) & 0XF 
                        TDCstop = single_event[1] & 0XF
                        TDCcoarse = (single_event[1] >> 4) & 0X7F
                        Timestamp = ((((single_event[0] >> 4) & 0X7FFF) << 15) + ((single_event[1] >> 15) & 0X7FFF) + (((single_event[-1] >> 16) & 0X3FFF) << 30)) * 8 + TDCstart * 0.254
                        
                        buffer_array.append(channel + 1)                       # channel
                        buffer_array.append((single_event[0] >> 27) & 0X7)     # event type
                        buffer_array.append(single_event[0] & 0xF)             # subhits number
                        buffer_array.append((single_event[2] >> 4) & 0XFFF)    # energy lg
                        buffer_array.append(TDCcoarse * 8)                     # Coarse
                        buffer_array.append(TDCstart * 0.254)                  # TDC Start
                        buffer_array.append(TDCstop * 0.254)                   # TDC Stop
                        buffer_array.append((TDCcoarse*8) - (TDCstop + TDCstart)*0.254)    # ToT
                        buffer_array.append(Timestamp)                         # Timestamp
                        buffer_array.append(Timestamp - Timestamp_old[channel-1])# Delta Time
                        Timestamp_old[channel-1] = Timestamp
                        buffer_array.append(Date)                              # Date
                        buffer_array.append(['Empty' if ((single_event[0] >> 19) & 1) == 0 else 'Full'][0])       # FIFO State
                        buffer_array.append(crc323check(single_event))         # CRC

                        buffer_matrix.append(buffer_array.copy())

                        buffer_array.clear()
                        single_event.clear()

                        NumEvent = NumEvent + 1
                        if len(buffer_matrix) > 0:
                            print(NumEvent)

                            with open(file_name, 'a') as OutFile:
                                writer = csv.writer(OutFile)
                                writer.writerows(buffer_matrix)

                            buffer_matrix.clear()
                        else:
                            single_event.clear()
                    else:
                        single_event.clear()
                        STATUS = 0
                else:
                    single_event.clear()
                    STATUS = 0

def main():
    convert()

if __name__ == "__main__":
    main()
