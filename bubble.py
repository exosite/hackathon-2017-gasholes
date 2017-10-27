import time
import math

# assume a constant speed in lieu of being able to measure this
speed = 0.03/3600*5280*12 # inches/second
# internal diameter of piping
internal_d = 0.25 # inches

# when the script starts, used to calculate the bubble rate over the session
system_start = time.time()

# in_bubble is a boolean describing the current state of the pipe
# if a bubble is present => 1, else => 0
in_bubble = False

# lists containing the timestamps of a bubble starting and ending
starts = []
finishes = []

# initial values for the number of bubbles and the volume of those bubbles
bubble_count = 0
bubble_volume_total = 0

#fermentation volume in liters
fermentation_volume = 0
fermentation_volume = input("how many liters are you brewing? ")
fermentation_volume = int(fermentation_volume)

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
  bubbles = len([b for b in starts if b >= time.time() - 30])
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
  gm_per_liter = eth_mol * 46
  gm_per_ml = gm_per_liter / 100

  return gm_per_ml

# main loop
while True:
  # manually enter each time to test script
  in_bubble = input("are you in a bubble? True/False: ")
  in_bubble = bool(in_bubble)

  # handle new bubble
  if in_bubble == True and len(starts) == len(finishes):
    # put the current time in the starts list
    starts.append(time.time())
    # increment bubble count
    bubble_count += 1

  # handle bubble that is now gone
  if in_bubble == False and len(starts) != len(finishes):
    # put the current time in the finishes list
    finishes.append(time.time())
    # get the length of the bubble
    length = bubble_length(
      speed,
      starts[bubble_count - 1],
      finishes[bubble_count - 1]
    )
    # get the volume of the bubble
    volume = bubble_volume(length, internal_d)
    # add volume to total volume counter
    bubble_volume_total += cubic_in_to_liters(volume)
    print(volume)

  # get avg bubble rate over the entire session
  # could be improved by looking at a rolling average
  rate = bubble_rate(30)

  # get abv of the beer
  abv = vol_co2_to_abv(bubble_volume_total, fermentation_volume)
  # print("starts: ", len(starts))
  # print("finishes: ", len(finishes))
  print("total Co2 volume (L): ", bubble_volume_total)
  print("bubble_rate (bubbles/s): ", rate)
  print("abv (%): ", abv)

