#!/usr/bin/env python3

from netdaq.netdaq import NetDAQ
from netdaq.config.instrument import DAQConfiguration, DAQConfigTrigger
from netdaq.config.enums import *
from netdaq.config.channels.analog import *
from netdaq.config.channels.computed import *
from netdaq.config.equation import DAQEquation
from netdaq.config.equation_compiler import DAQEQuationCompiler
from asyncio import run, sleep
from datetime import datetime, timedelta
from argparse import ArgumentParser


async def main3():
    eqc = DAQEQuationCompiler()
    print(eqc.compile("1 + 3 + 4 + 5 + 6 + 7d + ln(c5) * -35.3e+8 ** 4 / -ln((-C7))"))
    print(eqc.compile("C1 + C2 + C3 + C4 + C5"))


async def main2():
    eq = DAQEquation()
    print(eq.push_channel(1).push_float(1).add().end().encode())


async def main():
    parser = ArgumentParser(description="NetDAQ Control Utility")
    _ = parser.add_argument("--port", type=int, default=4369, help="Port number of the NetDAQ instrument (default: 4369)")
    _ = parser.add_argument("ip", help="IP address of the NetDAQ instrument")
    _ = parser.add_argument("--info", action="store_true", help="Only display instrument info and exit")
    args = parser.parse_args()

    instrument = NetDAQ(ip=args.ip, port=args.port)
    await instrument.connect()

    if args.info:
        print("===== BEGIN INFO =====")
        try:
            print("Constructor:", "OK")

            await instrument.connect()
            print("Connect:", "OK")

            await instrument.ping()
            print("Ping:", "OK")

            print("Base channel:", await instrument.get_base_channel())
            print("Version info:", await instrument.get_version_info())
        finally:
            print("====== END INFO ======")

    try:
        await instrument.ping()
        print("Base channel", await instrument.get_base_channel())
        print("Version info", await instrument.get_version_info())

        await instrument.wait_for_idle()
        await instrument.stop()
        await instrument.set_monitor_channel(0)

        await instrument.set_time()
        print("Time set!")

        eq = DAQEquation().push_channel(1).push_double(123456789.0).add().end()

        await instrument.set_config(
            DAQConfiguration(
                triggers=[DAQConfigTrigger.INTERVAL],
                interval_time=timedelta(milliseconds=500),
                analog_channels=[
                    # NOTE: Some instruments allow using "None" here to disable earlier channels.
                    #       Some, however, do not. In this case an error will be raised from the set_config call
                    DAQAnalogVDCChannel(
                        range=DAQVDCRange.VDC_3V,
                    ),
                    DAQAnalogVDCChannel(
                        range=DAQVDCRange.VDC_30V,
                    ),
                    DAQAnalogVDCChannel(
                        range=DAQVDCRange.VDC_AUTO,
                    ),
                ],
                computed_channels=[
                    DAQComputedEquationChannel(
                        equation=eq,
                    )
                ],
            )
        )
        print("Config set!")

        date = datetime.now()
        date += timedelta(seconds=10)

        await instrument.reset_totalizer()
        await instrument.start(date)
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
