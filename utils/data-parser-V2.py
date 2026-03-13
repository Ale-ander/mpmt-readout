import csv
import sys

def crc32(word: int) -> int:    # calcola il CRC di una riga da 32 bit del pacchetto
    step_1 = (word >> 16) ^ (word & 0xFFFF)
    step_2 = (step_1 >> 8) ^ (step_1 & 0xFF)
    return (step_2 >> 4) ^ (step_2 & 0xF)

def crc32check(arr) -> str:     # prende in input un array contenente le varie righe del
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

def get_prefix(word):
    return (word >> 30) & 0b11  # get data type from first 2 bits

def extract_subhit(sub_word):
    Timestamp = ((sub_word >> 15) & 0X7FFF) * 8
    TDCcoarse = ((sub_word >> 4) & 0X7F) * 4
    TDCstart = ((sub_word >> 11) & 0XF) * 0.254
    TDCstop = (sub_word & 0XF) * 0.254
    ToT = TDCcoarse - TDCstop + TDCstart
    return {
        'timestamp': (Timestamp << 4) + TDCstart,
        'TDCcoarse': TDCcoarse,
        'TDCstart': TDCstart,
        'TDCstop': TDCstop,
        'ToT': ToT
    }

def type_decode(event_type) -> str:
    if event_type == 0:
        return 'PMT_event'
    elif event_type == 1:
        return 'Pedestal event'
    elif event_type == 2:
        return 'LED event'
    elif event_type == 3:
        return 'Calibration event'
    else:
        return 'PPS'

def extract_data(packet):
    header = packet[0]
    second = packet[1]
    tail = packet[-1]
    subhits = packet[2:-1]

    channel = int(((header >> 22) & 0X1F)) + 1
    event_type = type_decode((header >> 27) & 0X7)
    subhits_number = header & 0xF
    rate = ['OK' if (header & 0X200000) > 0 else 'TOO HIGH'][0]
    energy = (tail >> 4) & 0XFFF
    TDCcoarse = ((second >> 4) & 0X7F) * 4
    TDCstart = ((second >> 11) & 0XF) * 0.250
    TDCstop = (second & 0XF) * 0.250
    ToT = TDCcoarse - TDCstop + TDCstart
    timestmp_reco = (((header >> 4) & 0X7FFF) << 15) + ((second >> 15) & 0X7FFF) + (((tail >> 16) & 0X3FFF) << 30)
    timestamp = timestmp_reco * 4 + TDCstart
    FIFO = ['Empty' if ((header >> 19) & 1) == 0 else 'Full'][0]
    CRC = crc32check(packet)

    return {
        'channel': channel,
        'event_type': event_type,
        'subhits_number': subhits_number,
        'rate': rate,
        'subhits_measures': [extract_subhit(pkg) for pkg in subhits],
        'energy': energy,
        'TDCcoarse': TDCcoarse,
        'TDCstart': TDCstart,
        'TDCstop': TDCstop,
        'ToT': ToT,
        'timestamp_raw': timestmp_reco,
        'timestamp': timestamp,
        'FIFO': FIFO,
        'CRC': CRC
    }

def parse_hex_file_to_csv(input_txt, filename):

    with open(f"{filename}.csv", 'w', newline='') as csvfile:  # write CSV
        writer = csv.writer(csvfile)
        writer.writerow(["Hieararchy", "Channel", "Event type", "Subhits number", "Rate", "Energy", "Coarse[ns]", "TDC start[ns]",
                  "TDC stop[ns]", "ToT[ns]", "Timestamp_raw", "Timestamp[ns]", "Delta Time[ns]", "FIFO State", "CRC"])

    with open(input_txt, 'r') as f:
        hex_lines = f.read().split()

    words = [int(h, 16) for h in hex_lines if h.strip()] # convert from words to int

    packets = []
    packet = []
    subhits = False

    for word in words:
        prefix = get_prefix(word)

        if prefix == 0b10: # head
            if subhits:
                print("Warning: head without previous tail", hex(word))
                packet.clear()
            packet = [word]         # start creating packet
            subhits = True

        elif prefix == 0b11: #tail
            if subhits:
                packet.append(word)
                packets.append(packet)
                packet = []
                subhits = False
            else:
                if word == 0xfc000000:
                    print("Warning: corrupted package, error tail found", hex(word))
                else:
                    print("Warning: tail without head", hex(word))

        else:
            if subhits:
                packet.append(word)
            else:
                print("Warning: word out of package", hex(word))

    write_buffer_to_csv(packets, filename)
    print(f"{len(packets)} packets decoded")
    packets.clear()

def write_buffer_to_csv(packets, filename):
    with open(f"{filename}.csv", 'a', newline='') as csvfile:  # write CSV
        writer = csv.writer(csvfile)

        previous_timestamp = [0] * 19
        
        for pkt in packets:
            event_type = type_decode((pkt[0] >> 27) & 0X7)
            if event_type == 'PPS':
                print('PPS event')
            else:
                values = extract_data(pkt)

                if previous_timestamp[values['channel']] == 0:
                    delta = 0
                else:
                    delta = values['timestamp'] - previous_timestamp[values['channel']]
                previous_timestamp[values['channel']] = values['timestamp']
                
                # Hits
                writer.writerow(['Main', values['channel'], values['event_type'], values['subhits_number'], values['rate'], values['energy'],
                                  values['TDCcoarse'], values['TDCstart'], values['TDCstop'], values['ToT'], values['timestamp_raw'], values['timestamp'],
                                  delta, values['FIFO'], values['CRC']])

                # Subhits
                for subvalues in values['subhits_measures']:
                    writer.writerow(
                        ['Sub', values['channel'], '', '', '', '', subvalues['TDCcoarse'], subvalues['TDCstart'],
                         subvalues['TDCstop'], subvalues['ToT'], values['timestamp']+subvalues['timestamp'], '', '', ''])

def main():
    parse_hex_file_to_csv(''.join(sys.argv[1]), sys.argv[2])

if __name__ == "__main__":
    main()
