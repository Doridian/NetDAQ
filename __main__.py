#!/usr/bin/env python3

from netdaq import NetDAQ, DAQConfigTrigger, DAQConfiguration, DAQMeasuremenType, DAQRange, DAQChannelConfiguration, DAQConfigAlarm
from sys import argv
from asyncio import run, sleep

async def main():
    instrument = NetDAQ(argv[1], 4369)
    await instrument.connect()

    try:
        await instrument.ping()
        print("Base channel", await instrument.get_base_channel())
        print("Version info", await instrument.get_version_info())

        await instrument.wait_for_idle()
        await instrument.stop()
        await instrument.set_monitor_channel(0)

        print("LC version", await instrument.get_lc_version())

        await instrument.set_time()
        print("Time set!")

        await instrument.set_config(DAQConfiguration(
            triggers=[DAQConfigTrigger.INTERVAL],
            interval_time=0.25,
            phy_channels=[
                DAQChannelConfiguration(
                    mtype=DAQMeasuremenType.VDC,
                    range=DAQRange.VDC_3V,
                    alarm1_mode=DAQConfigAlarm.LOW,
                    alarm1_level=2.0,
                    alarm1_digital=5,
                    alarm2_mode=DAQConfigAlarm.LOW,
                    alarm2_level=-3.0,
                    alarm2_digital=6,
                ),
            ],
            computed_channels=[],
        ))
        print("Config set!")

        await instrument.reset_totalizer()
        await instrument.start()
        await instrument.set_monitor_channel(1)

        while True:
            readings = await instrument.get_readings()
            print(readings)
            if readings.instrument_queue == 0:
                await sleep(1)
    finally:
        print("Clean shutdown...")
        await instrument.close()
        print("Done!")

run(main())
