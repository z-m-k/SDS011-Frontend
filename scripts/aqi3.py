#!/usr/bin/python3
# coding=utf-8
import sys
import json
import time
from sds011 import SDS011
import numpy as np

# CONFIGURATION
SERIALPORT = "/dev/ttyUSB0"  # USB port where SDS011 is
# This will influence the accuracy and speed of readings, keep a good balance
# Less reads = Less precision and fast
# More reads = More precision and slow
# After measurements the sensor, laser and fan will be turn off for 'UPDATE_FREQUENCY' time, this will increase the lifespan of the sensor.
READINGS = 5  # Number of readings, this will not perform an AVG, only the last read will be used as value.
SLEEP_BEFORE_FIRST_READ = 15  # Time to wait in seconds after sensor awake and before the first read. Give sometime for the sensor stabilize
SLEEP_BETWEEN_READS = 2  # Time to sleep in seconds between each read, total read time will be READINGS x SLEEP_BETWEEN_READS.
UPDATE_FREQUENCY = 60  # Update frequency in seconds, new measurements after that time.
# If UPDATE_FREQUENCY = 0, the sensor will never turn off, this will wear your sensor much faster.
# (according to the manufacturer, the lifespan totals approximately 8000 hours).
STORED_READ_NUM = 100  # Maximum number of readings to plot or store, when max is reached, the oldest read will be removed.


def logcmd(text):
    if 'debug' in sys.argv:
        print(text)


# Don't change
DATA_FILE = '/var/www/html/assets/aqi.json'
def get_stats(x):
    m=np.mean(x)
    s=np.std(x)
    conf_width=(1.96*s)/np.sqrt(len(x))
    return {
        'min': np.min(x),
        'max': np.max(x),
        'mean': m,
        'std': s,
        'conf_l': m-conf_width,
        'conf_h': m+conf_width,
    }
if __name__ == "__main__":
    sensor = SDS011(SERIALPORT, use_query_mode=True)
    if 'stop' in sys.argv:
        sensor.sleep()  # Turn off fan and diode
    else:
        while True:
            logcmd("Awaking sensor and wait " + str(SLEEP_BEFORE_FIRST_READ) + "s before query.")
            sensor.sleep(sleep=False)  # Turn on fan and diode
            time.sleep(SLEEP_BEFORE_FIRST_READ)

            values = None
            for t in range(READINGS):
                time.sleep(SLEEP_BETWEEN_READS)
                valuest = sensor.query()
                if valuest is not None and len(valuest) == 2:
                    if values==None:
                        values=[[],[]]
                    values[0].append(valuest[0])
                    values[1].append(valuest[1])
                    logcmd(str(t + 1) + "# PM2.5: " + str(valuest[0]) + ", PM10: " + str(valuest[1]))

            if values is not None and len(values) == 2:
                # open stored data
                with open(DATA_FILE) as json_data:
                    data = json.load(json_data)

                DATA_FILE_DAY = '/var/www/html/air_quality/{}.json'.format(time.strftime("%Y-%m-%d"))
                with open(DATA_FILE_DAY) as json_data:
                    data_day = json.load(json_data)


                new_obs={'pm25': get_stats(values[0]), 'pm10': get_stats(values[0]), 'time': time.strftime("%d-%m-%Y %H:%M:%S")}


                # check if length is more than STORED_READ_NUM and delete first/oldest element
                while len(data) > STORED_READ_NUM:
                    data.pop(0)

                # append new values
                data.append({'pm25': new_obs['pm25']['mean'], 'pm10': new_obs['pm10']['mean'], 'time': new_obs['time']})
                data_day.append({'pm25': new_obs['pm25']['mean'], 'pm10': new_obs['pm10']['mean'], 'time': new_obs['time']})

                # save it
                with open(DATA_FILE, 'w') as outfile:
                    json.dump(data, outfile)
                with open(DATA_FILE_DAY, 'w') as outfile:
                    json.dump(data, outfile)

            if UPDATE_FREQUENCY > 0:
                logcmd("Going to sleep for " + str((UPDATE_FREQUENCY / 60)) + " min...")
                sensor.sleep()  # Turn off fan and diode
                time.sleep(UPDATE_FREQUENCY)
