#!/usr/bin/env python

from time import sleep
import automationhat as hat

while True:
    print("CO2: {}".format(hat.analog.one.read()))