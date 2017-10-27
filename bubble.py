import time
import math

speed = 0.03/3600*5280*12 # inches/second
internal_d = 0.25 # inches

system_start = time.time()

in_bubble = False
starts = []
finishes = []
bubble_count = 0
bubble_volume_total = 0

#fermentation volume in liters
fermentation_volume = 0

def bubble_length(speed, start_time, finish_time):
  return speed * (finish_time - start_time)

def bubble_volume(bubble_length, internal_d): # cubic inches
  volume = math.pi * (internal_d / 2) ** 2 * bubble_length 
  return volume

def abv():
  return None

def bubble_rate(bubbles, seconds): # bubbles per second
  return bubble_count/seconds

def vol_co2_to_abv(vol_co2, fermentation_volume):
  #convert volume of co2 in liters to moles of co2
  # 0.042mole/liter calculated by RTP (room temperature and 1 atmosphere): 24 liters/mole
  co2_mol = vol_co2 * 0.042

  #then we know the for every mole of co2 then there the same amount of ethanol
  eth_mol = co2_mol

  #then convert to concentration of ethanol
  eth_conc = eth_mol/fermentation_volume

  #then convert that to %abv 46 (gm/mole)
  abv = eth_mol * 46

  return abv


while True:
  fermentation_volume = input("how many liters are you brewing? ")
  vol_co2 = input("enter vol in L")
  print(vol_co2_to_abv(vol_co2, fermentation_volume))
  in_bubble = input("are you in a bubble? True/False: ")
  in_bubble = bool(in_bubble)
  # print(in_bubble)
  if in_bubble == True and len(starts) == len(finishes):
    starts.append(time.time())
    bubble_count += 1
  if in_bubble == False and len(starts) != len(finishes):
    finishes.append(time.time())
    length = bubble_length(
      speed,
      starts[bubble_count - 1],
      finishes[bubble_count - 1]
    )
    volume = bubble_volume(length, internal_d)
    bubble_volume_total += volume
    print(volume)
  rate = bubble_rate(bubble_count, time.time() - system_start)
  print(len(starts), len(finishes), "bubble_rate: ", rate)

# total bubbles
# total volume
# ABV
# 

