#!/usr/bin/env python3

from netdaq import NetDAQ
from sys import argv

instrument = NetDAQ(argv[1], 4369)
instrument.connect()

instrument.ping()
print("Base channel", instrument.get_base_channel())
print("Version info", instrument.get_version_info())

instrument.wait_for_idle()
instrument.stop()

print("LC version", instrument.get_lc_version())

instrument.set_time()
print("Time set!")

# Configure channels

# 0x71
# 0x67
# 0x64 .....

# 0x76
# 0x68

instrument.close()
