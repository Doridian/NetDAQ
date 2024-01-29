#!/usr/bin/env python3

from netdaq import NetDAQ, DAQConfigBits, DAQConfiguration, DAQMeasuremenType, DAQRange, DAQChannelConfiguration
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
    bits=DAQConfigBits.INTERVAL_TRIGGER.value | DAQConfigBits.DRIFT_CORRECTION.value | DAQConfigBits.TOTALIZER_DEBOUNCE.value,
    interval_time=1.0,
    alarm_time=1.0,
    phy_channels=[
        DAQChannelConfiguration(
            mtype=DAQMeasuremenType.VDC,
            range=DAQRange.VDC_3V,
        ),
        DAQChannelConfiguration(
            mtype=DAQMeasuremenType.VDC,
            range=DAQRange.VDC_3V,
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
        print("Readings", instrument.get_readings())
        sleep(1)
except KeyboardInterrupt:
    pass

instrument.set_monitor_channel(0)
instrument.stop()

instrument.close()
