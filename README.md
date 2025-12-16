# Fluke 2640A/2645A NetDAQ

## Library usage

This library is undergoing heavy development at the moment and ease of use will be a focus once the whole protocol has been implemented

For now, check out [`netdaq/__main__.py`](netdaq/__main__.py). For running, this requires the instrument's IP as the first argument.

## Reporting issues

Whenever reporting an issue, please add the output of `python3 -m netdaq --info INSTRUMENT_IP` to your issue.

## Instrument manuals

User manual: [https://archive.org/details/FLUKE_2640A_2645A_User](https://archive.org/details/FLUKE_2640A_2645A_User)

Service manual: [https://archive.org/details/FLUKE_2640A_2645A_Service](https://archive.org/details/FLUKE_2640A_2645A_Service)

## Protocol

The protocol has been reverse engineered using the demo version of NetDAQ logger and Wireshark.

See [`PROTOCOL.md`](PROTOCOL.md) for those efforts

## NetDAQ logger demo

[http://download.caltech.se/download/fluke/DAQ/FlukeNetDAQ.exe](http://download.caltech.se/download/fluke/DAQ/FlukeNetDAQ.exe)

**The installer (or parts of it) require 16-bit mode (ex. a Windows XP VM)**. However, once the program is installed, the folder in `Program Files` can just be copied to a Windows 11 machine and it will run just fine.
