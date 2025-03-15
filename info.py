#!/usr/bin/env python3

from lib.netdaq import NetDAQ
from sys import argv
from asyncio import run

async def main():
    print("===== BEGIN INFO =====")
    try:
        instrument = NetDAQ(ip=argv[1], port=4369)
        print("Constructor:", "OK")

        await instrument.connect()
        print("Connect:", "OK")

        await instrument.ping()
        print("Ping:", "OK")

        print("Base channel:", await instrument.get_base_channel())
        print("Version info:", await instrument.get_version_info())
    finally:
        print("====== END INFO ======")

run(main())
