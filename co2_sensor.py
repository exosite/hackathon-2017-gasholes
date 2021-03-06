#!/usr/bin/env python

# pylint: disable=C0325,R0201,C0111

WORKING_ON_BEAGLEBONE = True
if not WORKING_ON_BEAGLEBONE:
    import automationhat as hat
else:
    import Adafruit_BBIO.ADC as ADC

import threading, Queue

import time
import math
import json

from exo.device import Device

class Murano(threading.Thread, Device):
    # total co2 volume
    # abv
    # beer temp
    # bubble rate
    # bubble total
    # start time
    # brew volume
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.name = self.__class__.__name__
        Device.__init__(self, "Gasholes-v1", 'gasholes.cfg')
        self.activate_device()
        print("Got cik: {}".format(self.cik()))
        self.q_in = Queue.Queue()
        self._kill = False

    def run(self):
        print("Starting exosite thread...")
        while not self._kill:
            print("Murano write status: {}".format(self.http_write('raw_data', self.q_in.get())))

class PhotoDiode(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.name = self.__class__.__name__
        self.q_out = Queue.Queue()
        self._kill = False
        if WORKING_ON_BEAGLEBONE:
            print("Setting up ADC for beaglebone...")
            ADC.setup()

    def _read(self):
        if WORKING_ON_BEAGLEBONE:
            val = ADC.read('P9_39')
            # print("Reading from beaglebone: {}".format(val))
            return val
        return hat.analog.one.read()

    def get_nominal_level(self):
        level = 0.0
        for _ in range(0, 450):
            tmp = self._read()
            time.sleep(0.01)
            if tmp < self._read():
                level = tmp
        print("Found nominal level: {}".format(level))
        return level

    def run(self):

        nominal_level = self.get_nominal_level()
        while not self._kill:
            val = self._read()
            if WORKING_ON_BEAGLEBONE:
                multiplier = 1.1
            else:
                multiplier = 1.1
            if val >= nominal_level * multiplier:
                self.q_out.put(True)
            else:
                # print("No bubble")
                self.q_out.put(False)
            time.sleep(0.05)


#############################



class Bubble(threading.Thread):
    def __init__(self, frmtn_vol, murano_thread_q):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.name = self.__class__.__name__
        
        # assume a constant speed in lieu of being able to measure this
        self.speed = 0.03/3600*5280*12 # inches/second
        # internal diameter of piping
        self.internal_d = 0.25 # inches

        # when the script starts, used to calculate the bubble rate over the session
        self.system_start = time.time()

        # in_bubble is a boolean describing the current state of the pipe
        # if a bubble is present => 1, else => 0
        self.in_bubble = False

        # lists containing the timestamps of a bubble starting and ending
        self.starts = []
        self.finishes = []

        # initial values for the number of bubbles and the volume of those bubbles
        self.bubble_count = 0
        self.bubble_volume_total = 0

        #fermentation volume in liters
        self.fermentation_volume = frmtn_vol
        self.abv = 0
        self.q_in = Queue.Queue()
        self.murano_thread_q = murano_thread_q
        self._kill = False
        print("Bubble thread initialized...")

    def bubble_length(self, speed, start_time, finish_time):
        # calculate the length of the bubble using the speed and the time delta
        # from start to finish
        return speed * (finish_time - start_time)

    def bubble_volume(self, bubble_length, internal_d): # cubic inches
        volume = math.pi * (internal_d / 2) ** 2 * bubble_length 
        return volume

    def cubic_in_to_liters(self, cubic_inches):
        # convert Co2 volume in cubic inches to liters
        liters = 0.016387064 * cubic_inches
        return liters

    def bubble_rate(self, rolling_seconds):
        # rolling avg bubbles per second
        bubbles = len([b for b in self.starts if b >= time.time() - rolling_seconds])
        return bubbles/float(rolling_seconds)

    def vol_co2_to_abv(self, vol_co2, fermentation_volume):
        # convert volume of co2 in liters to moles of co2
        # 0.042mole/liter calculated by RTP (room temperature and 1 atmosphere): 24 liters/mole
        co2_mol = vol_co2 * 0.042

        # then we know the for every mole of co2 then there the same amount of ethanol
        eth_mol = co2_mol

        # then convert to concentration of ethanol
        eth_conc = eth_mol/fermentation_volume

        # then convert that to %abv 46 (gm/mole)
        gm_per_liter = eth_conc * 46
        gm_per_ml = gm_per_liter / 100

        return gm_per_ml

    def run(self):
        # main loop
        print("Starting bubble loop...")
        while not self._kill:
            try:
                self.in_bubble = self.q_in.get(timeout=1.0)
                # print("In bubble? {}".format(self.in_bubble))
            except Queue.Empty:
                continue
            # handle new bubble - am I in a bubble now, and I wasn't before?
            if self.in_bubble == True and len(self.starts) == len(self.finishes):
                # put the current time in the starts list
                self.starts.append(time.time())
                # increment bubble count
                self.bubble_count += 1

            # handle bubble that is now gone - am I not in a bubble and was I before?
            if self.in_bubble == False and len(self.starts) != len(self.finishes):
                # put the current time in the finishes list
                self.finishes.append(time.time())
                # get the length of the bubble
                length = self.bubble_length(
                    self.speed,
                    self.starts[self.bubble_count - 1],
                    self.finishes[self.bubble_count - 1]
                )
                # get the volume of the bubble
                volume = self.bubble_volume(length, self.internal_d)
                # add volume to total volume counter
                self.bubble_volume_total += self.cubic_in_to_liters(volume)
                # print(volume)

                # get avg bubble rate over the entire session
                # could be improved by looking at a rolling average
                rate = self.bubble_rate(30)

                # get abv of the beer
                self.abv = self.vol_co2_to_abv(self.bubble_volume_total, self.fermentation_volume)

                if WORKING_ON_BEAGLEBONE:
                    beer_temp = ADC.read('P9_37')
                else:
                    beer_temp = hat.analog.one.read()
                blob = {
                    "beer_temperature": (beer_temp*18+5)/10 + 32,
                    "co2_volume": self.bubble_volume_total,
                    "abv": self.abv,
                    "bubble_rate": rate,
                    "bubble_total": self.bubble_count,
                    "start_time": self.system_start,
                    "brew_volume": self.fermentation_volume
                }
                print(json.dumps(blob, indent=2))
                self.murano_thread_q.put(json.dumps(blob))


############################


def main(vol):
    photosensor = PhotoDiode()
    photosensor.start()

    murano = Murano()
    murano.start()

    bubble = Bubble(vol, murano.q_in)
    bubble.start()


    try:
        while True:
            try:
                bubble.q_in.put(photosensor.q_out.get(timeout=1.0))
            except Queue.Empty:
                continue
    except KeyboardInterrupt:
        photosensor._kill = True
        bubble._kill = True
        murano._kill = True

if __name__ == '__main__':

    main(1.89) # liters
