#!/usr/bin/env python

import automationhat as hat
import threading, Queue

import time
import math
class PhotoDiode(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.name = self.__class__.__name__
        self.q_out = Queue.Queue()
        self._kill = False

    def _read(self):
        return hat.analog.one.read()

    def get_nominal_level(self):
        level = 0.0
        for i in range(0,1000):
            tmp = self._read()
            time.sleep(0.1)
            if tmp < self._read():
                level = tmp
        return level

    def run(self):

        nominal_level = self.get_nominal_level()
        while not self._kill:
            val = self._read()
            if val > nominal_level * 1.1:

                self.q_out.put(True)
            self.q_out.put(False)
            time.sleep(0.05)


#############################



class Bubble(threading.Thread):
    def __init__(self, frmtn_vol):
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
        self.bubble_rate = 0
        self.q_in = Queue.Queue()
        self._kill = False

        def bubble_length(speed, start_time, finish_time):
            # calculate the length of the bubble using the speed and the time delta
            # from start to finish
            return speed * (finish_time - start_time)

        def bubble_volume(bubble_length, internal_d): # cubic inches
            volume = math.pi * (internal_d / 2) ** 2 * bubble_length 
            return volume

        def cubic_in_to_liters(cubic_inches):
            # convert Co2 volume in cubic inches to liters
            liters = 0.016387064 * cubic_inches
            return liters

        def bubble_rate(rolling_seconds):
            # rolling avg bubbles per second
            bubbles = len([b for b in self.starts if b >= time.time() - 30])
            return bubbles/rolling_seconds

        def vol_co2_to_abv(vol_co2, fermentation_volume):
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
            while not self._kill:

                self.in_bubble = self.q_in.get(timeout=1.0)
                # handle new bubble
                if self.in_bubble == True and len(self.starts) == len(self.finishes):
                    # put the current time in the starts list
                    self.starts.append(time.time())
                    # increment bubble count
                    self.bubble_count += 1

                # handle bubble that is now gone
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
                self.bubble_rate = self.bubble_rate(30)

                # get abv of the beer
                self.abv = self.vol_co2_to_abv(self.bubble_volume_total, self.fermentation_volume)
                # print("starts: ", len(starts))
                # print("finishes: ", len(finishes))
                # print("total Co2 volume (L): ", bubble_volume_total)
                # print("bubble_rate (bubbles/s): ", rate)
                # print("abv (%): ", abv)



############################


def main(vol):
    photosensor = PhotoDiode()
    photosensor.start()

    bubble = Bubble(vol)
    bubble.start()
    try:
        while True:
            bubble.q_in.put(photosensor.q_out.get(timeout = 1.0))
    except KeyboardInterrupt:
        photosensor._kill = True
        bubble._kill = True

if __name__ == '__main__':
    fermentation_volume = input("What is the fermentation volume (in Liters)? ")
    main(fermentation_volume)