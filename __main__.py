#!/usr/bin/env python3

from lib.netdaq import NetDAQ
from lib.config.instrument import DAQConfiguration, DAQConfigTrigger
from lib.config.enums import *
from lib.config.channels.analog import *
from lib.config.equation import DAQEquation
from lib.config.equation_compiler import DAQEQuationCompiler
from sys import argv
from asyncio import run, sleep

async def main3():
    eqc = DAQEQuationCompiler()
    print(eqc.compile("1 + 2 * -35.3 ** 4 / C7"))

async def main2():
    eq = DAQEquation()
    print(eq.push_channel(1).push_float(1).add().end().encode())

async def main():
    instrument = NetDAQ(ip=argv[1], port=4369)
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
            interval_time=0.5,
            analog_channels=[
                DAQAnalogOhmsChannel(
                    range=DAQOhmsRange.Ohms_3k,
                    four_wire=False,
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

run(main3())
