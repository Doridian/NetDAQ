#!/usr/bin/env python3

from netdaq import NetDAQ, DAQConfigTrigger, DAQConfiguration, DAQMeasuremenType, DAQRange, DAQChannelConfiguration, DAQConfigAlarm
from sys import argv
from time import sleep

instrument = NetDAQ(argv[1], 4369)
instrument.connect()

instrument.ping()
print("Base channel", instrument.get_base_channel())
print("Version info", instrument.get_version_info())

instrument.wait_for_idle()
instrument.stop()
instrument.set_monitor_channel(0)

print("LC version", instrument.get_lc_version())

instrument.set_time()
print("Time set!")

instrument.set_config(DAQConfiguration(
    triggers=[DAQConfigTrigger.INTERVAL],
    interval_time=1.0,
    phy_channels=[
        DAQChannelConfiguration(
            mtype=DAQMeasuremenType.VDC,
            range=DAQRange.VDC_3V,
            alarm1_mode=DAQConfigAlarm.LOW,
            alarm1_level=-2.0,
            alarm1_digital=5,
        ),
    ],
    computed_channels=[],
))
print("Config set!")

instrument.reset_totalizer()
instrument.start()
instrument.set_monitor_channel(1)

try:
    while True:
        readings = instrument.get_readings()
        for reading in readings:
            print("Reading", reading.alarm_bitmask, reading.values, "%04x" % reading.dio)
        sleep(1)
except KeyboardInterrupt:
    pass

print("Clean shutdown...")

instrument.set_monitor_channel(0)
instrument.stop()

instrument.close()
print("Done!")
