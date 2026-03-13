#!/usr/bin/env python3

import zmq
import sys

context = zmq.Context()

frontend = context.socket(zmq.ROUTER)
frontend.bind("tcp://*:5555")

filename = sys.argv[2] + '.txt'

outFile = open(filename, 'w')
outFile.close()
nMeasure = 0
result = 0
results = []
while nMeasure < int(sys.argv[1]):
    message = frontend.recv_multipart()
    print(f"Message {nMeasure+1} received")
    for part in message:
        if len(part) != 1:
            i = 0
            for b in part:
                result += b << (24 - i * 8)
                i = i + 1
                if (i % 4) == 0:
                    with open(filename, 'a') as f:
                        f.write(f"{result:08x}\n")
                    result = 0
                    i = 0
    nMeasure = nMeasure + 1
