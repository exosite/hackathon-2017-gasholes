#!/usr/bin/env python

from time import sleep
import automationhat as hat
import threading, Queue

class PhotoDiode(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.name = self.__class__.__name__
        self.q_in = Queue.Queue()
        self.q_out = Queue.Queue()

    def _read(self):
        return hat.analog.one.read()
    def run(self):

        init_val = self._read()
        while True:
            self.q_out.put(self._read())
            sleep(0.05)
def main():
    photosensor = PhotoDiode()
    photosensor.start()
    while True:
        print(photosensor.q_out.get())

if __name__ == '__main__':
    main()