# Protocol

## Packet structure (both request and response)
- 0x46 0x45 0x4c 0x58 ("FELX")
- 4-byte sequence ID starting at anything
- 4-byte command ID
- 4-byte whole packet length
- (optional) payload

## Basics
- Response command ID 0x00000000 for success or 0xFFFFFFFF with 4-byte error code
- Response sequence ID == request sequence ID
- All packets are specified MSB-first / BIG endian

## Remaining unknowns
- Any command IDs except the ones documented below
- Everything labelled "UNKNOWN" in this document, a lot of these just seem to be unused/padding or constant parts of packets

## Command IDs
- 0x00000000 = Ping, empty request, empty response
- 0x00000001 = Connection close, empty request, empty response
- 0x00000002 = Status query, empty request, response [0x90/0x84/0x00 (0x90 = initializing, 0x84 = configuring, 0x00 = idle), 0x00, 0x00, 0x00]
- 0x00000003 = Reset, empty request, empty response
- 0x00000004 = get internal errors ? "flxIError" , empty request, 4 bytes response (UNKNOWN)
- 0x00000064 = Request readings, request 4-byte integer maximum readings to return (just use 255), response variable length
- 0x00000067 = START command, request 16-byte "start_request" struct (see below), empty response
- 0x00000068 = STOP command, empty request, empty response
- 0x00000069 = Get time, empty request, response : netdaq_time (see below), 12 bytes
- 0x0000006A = Set time, request: netdaq_time (see below), 12 bytes, empty response
- 0x0000006F = Query spy channel, request 4-byte channel, response 4-byte float value
- 0x00000071 = Clear totalizer, empty request, empty response
- 0x00000072 = Get version info, empty request, response zero-terminated strings [Model name, DMM version, BM version, FA version, BA version]
- 0x00000075 = Set monitor channel, request 4-byte channel number, empty response
- 0x00000076 = Turn off monitor channel, empty request, empty response
- 0x00000077 = Get base channel, empty request, response 4-byte base channel
- 0x0000007C = Enable spy mode, empty request, empty response
- 0x0000007D = Disable spy mode, empty request, empty response
- 0x0000007F = Get LC version (flxLoggerCompatibility), empty request, response zero-terminated string LC version
- 0x00000080 = Get config block, empty request, response see below
- 0x00000081 = Set config block, request see below, empty response

## Various command payloads

### START (flxScansEnable, flxScansEnableAt), 0x67
    ```
    00000CB8  00 00 00 00 ac f4 19 00  58 10 46 00 00 00 00 0d   ........ X.F.....
    ```
First byte is the bool flag "delayed" ; if 0 : scan begins now (rest of the struct is ignored), if 1, scan begins at specified time (shortened version of struct netdaq_time)
```
struct start_request {
	u8 delayed_flag;	// 1 if delayed
	u8 padding[3];	//set to 0

	u8 hours;
	u8 minutes;
	u8 sec;
	u8 month;	//1 to 12
	u8 unused_4;	// DLL leaves this uninitialized
	u8 day;
	u8 year;	// 2-digit == (year % 100)
	u8 unused_7;
}
```
	
### Get/Set time (0x69, 0x6A)
This uses the full netdaq_time struct (12 bytes) :
```
struct netdaq_time {
	u8 hours;
	u8 minutes;
	u8 sec;
	u8 month;	//1 to 12
	u8 unused_4;	// DLL leaves this uninitialized
	u8 day;
	u8 year;	// 2-digit == (year % 100)
	u8 unused_7;
	u32 ms;
}
```

### Readings command payload (0x00000064)

#### Request
```
1 channel
00000E1C  00 00 00 5c                                        ...\
2 channels
00000E1C  00 00 00 52                                        ...R
3 channels
00000D64  00 00 00 4a                                        ...J
6 channels
00000EE8  00 00 00 38                                        ...8
```

- Maximum number of readings to return 4-byte

#### Response

```
No readings
000014B8  00 00 00 20 00 00 00 00  00 00 00 00               ... .... ....

One reading (-0.0112415 VDC on channel 1)
00000B28  00 00 00 20 00 00 00 01  00 00 00 00 00 00 00 10   ... .... ........
00000B38  0b 28 38 01 00 1c 18 02  00 ff 03 e5 00 00 00 00   .(8..... ........
00000B48  00 00 00 00 00 00 00 00  bc 42 6c 3d               ........ .Bl=

Two enabled VDC channels reading
0000125C  00 00 00 24 00 00 00 01  00 00 00 00 00 00 00 10   ...$.... ........
0000126C  0b 2a 07 01 00 1c 18 02  00 ff 03 97 00 00 00 00   .*...... ........
0000127C  00 00 00 00 00 00 00 00  bc 42 db 2b bb c9 6a 3e   ........ .B.+..j>

Six enabled VDC channels, one reading
000006DC  00 00 00 34 00 00 00 01  00 00 00 00 00 00 00 10   ...4.... ........
000006EC  0b 36 03 01 00 1c 18 02  00 ff 03 49 00 00 00 00   .6...... ...I....
000006FC  00 00 00 00 00 00 00 00  bc 45 4c 69 bb d0 fa 7a   ........ .ELi...z
0000070C  bb bb 3b d0 bb d4 35 68  bb b7 0e da bb c6 f9 02   ..;...5h ........

Six enabled VDC channels, two readings
00000FF4  00 00 00 34 00 00 00 02  00 00 00 00 00 00 00 10   ...4.... ........
00001004  0c 00 0c 01 00 1c 18 02  00 ff 00 7e 00 00 00 00   ........ ...~....
00001014  00 00 00 00 00 00 00 00  bc 45 19 fd bb d6 2d a2   ........ .E....-.
00001024  bb ba 86 4a bb d6 05 4c  bb c4 9b ee bb cd d3 b6   ...J...L ........
00001034  00 00 00 10 0c 00 0c 01  00 1c 18 02 00 ff 00 f9   ........ ........
00001044  00 00 00 00 00 00 00 00  00 00 00 00 bc 39 0c 1f   ........ .....9..
00001054  bb c3 e6 6a bb ab 29 52  bb c0 ab 7a bb a5 54 cf   ...j..
```

- Chunk length 4-byte (`28 + (channels * 4)` or `(7 + channels) * 4`)
- Readings in this packet 4-byte
- Readings left on instrument after this query 4-byte
- Repeated chunk for each reading
    - 4-byte UNKNOWN (0x00 0x00 0x00 0x10)
    - Hours, Minutes, Seconds, Month
    - 0x00 (ignore), Day of month, 2-digit-Year, 0x02 (ignore)
    - 4-byte milliseconds, first two bytes 0x00 0xFF (should be ignored)
    - DIO status bitfield 2-byte
    - 2-byte UNKNOWN (not null, changing, likely garbage data)
    - Alarm1 bitmask 4-byte
    - Alarm2 bitmask 4-byte
    - Totalizer count 4-byte
    - Channel values as 32-bit floats

### Configuration command payload (0x00000081)

Packet always has total length of 2508 (0x09CC), 30 channels always present, followed by all equations, padded with null-bytes if needed

#### General config
```
Interval + Alarm, 1.234, 5.678
000001EC  00 00 00 f0 00 00 00 00  00 00 00 00 00 00 00 01   ........ ........
000001FC  00 00 00 ea 00 00 00 00  00 00 00 00 00 00 00 05   ........ ........
0000020C  00 00 02 a6 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
0000021C  00 00 00 64

Interval 1.000
000001BC  00 00 00 70 00 00 00 00  00 00 00 00 00 00 00 01   ...p.... ........
000001CC  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
000001DC  00 00 00 64 00 00 00 00  00 00 00 00 00 00 00 00   ...d.... ........
000001EC  00 00 00 64

Interval 2.000
0000015C  00 00 00 70 00 00 00 00  00 00 00 00 00 00 00 02   ...p.... ........
0000016C  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 05   ........ ........
0000017C  00 00 02 a6 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
0000018C  00 00 00 64

000001AC  00 00 00 70 00 00 00 00  00 00 00 00 00 00 00 02   ...p.... ........
000001BC  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 05   ........ ........
000001CC  00 00 02 a6 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
000001DC  00 00 00 64

Equations

20*log(C1/C2)
02 41 a0 00 00 01 00 01  01 00 02 08 0c 07 00
02 float-20(4B) 01 channel-1(2B) 01 channel-2(2B) 08 0c 07 00

20*log(C2/C1)
02 41 a0 00 00 01 00 02  01 00 01 08 0c 07 00
02 float-20(4B) 01 channel-2(2B) 01 channel-1(2B) 08 0c 07 00
```

- Configuration bits 4-byte
    - Last 9 bits, all others 0
        - External trigger
        - Alarm trigger
        - Interval trigger
        - Totalizer debounce
        - Drift correction (can only be turned off in "Fast")
        - Trigger out
        - Fahrenheit (off for Celsius)
        - Fast (set neither for "Slow")
        - Medium (set neither for "Slow")
- 4-byte UNKNOWN (null)
- 4-byte UNKNOWN (null)
- Interval time whole seconds 4-byte
- Interval time milliseconds 4-byte
- 4-byte UNKNOWN (null)
- 4-byte UNKNOWN (null)
- Alarm time whole seconds 4-byte
- Alarm time milliseconds 4-byte
- 4-byte UNKNOWN (null)
- 4-byte UNKNOWN (null)
- 4-byte UNKNOWN (null)
- 4-byte UNKNOWN (0x00 0x00 0x00 0x64)

#### Per-channel config
```
000001EC              00 00 00 02  00 00 20 01 00 00 00 00            .. .....
000001FC  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
0000020C  00 00 00 00 00 00 00 00  00 00 00 00 3f 80 00 00   ........ ....?...
0000021C  00 00 00 00
```

- Type 4-byte
    - Analog channels
        - 0x00 0x00 0x00 0x00 = OFF
        - 0x00 0x00 0x00 0x01 = Ohms
        - 0x00 0x00 0x00 0x02 = VDC
        - 0x00 0x00 0x00 0x04 = VAC
        - 0x00 0x00 0x00 0x08 = Frequency
        - 0x00 0x00 0x00 0x10 = RTD
        - 0x00 0x00 0x00 0x20 = Thermocouple
        - 0x00 0x01 0x00 0x02 = Current
    - Computed channels
        - 0x00 0x00 0x80 0x01 = Average
        - 0x00 0x00 0x80 0x02 = A - B
        - 0x00 0x00 0x80 0x03 = A - Average
        - 0x00 0x00 0x80 0x04 = Equation (See [`EQUATIONS.md`](EQUATIONS.md))
- Range 4-byte (computed channels use 0x00 0x00 0x00 0x00)
    - VDC
        - 0x00 0x00 0x20 0x01 = 90 mV
        - 0x00 0x00 0x21 0x02 = 300 mV
        - 0x00 0x00 0x23 0x08 = 3 V
        - 0x00 0x00 0x24 0x10 = 30 V
        - 0x00 0x00 0x25 0x20 = Auto
        - 0x00 0x00 0x26 0x40 = 50 V
    - VAC
        - 0x00 0x00 0x30 0x01 = 300 mV
        - 0x00 0x00 0x31 0x02 = 3 V
        - 0x00 0x00 0x32 0x04 = 30 V
        - 0x00 0x00 0x33 0x08 = Auto
    - Ohms 2W
        - 0x00 0x00 0x12 0x04 = 30 kOhm
        - 0x00 0x00 0x13 0x08 = 300 kOhm
        - 0x00 0x00 0x14 0x10 = 3 MOhm
        - 0x00 0x00 0x15 0x20 = Auto
    - Ohms 4W
        - 0x00 0x00 0x10 0x01 = 300 Ohm
        - 0x00 0x00 0x11 0x02 = 3 kOhm
        - 0x00 0x00 0x12 0x04 = 30 kOhm
        - 0x00 0x00 0x13 0x08 = 300 kOhm
        - 0x00 0x00 0x14 0x10 = 3 MOhm
        - 0x00 0x00 0x15 0x20 = Auto
    - Thermocouple
        - 0x00 0x00 0x60 0x01 = J
        - 0x00 0x00 0x61 0x01 = K
        - 0x00 0x00 0x62 0x01 = E
        - 0x00 0x00 0x63 0x01 = T
        - 0x00 0x00 0x64 0x01 = R
        - 0x00 0x00 0x65 0x01 = S
        - 0x00 0x00 0x66 0x01 = B
        - 0x00 0x00 0x67 0x01 = C
        - 0x00 0x00 0x68 0x01 = N
    - RTD 4W
        - 0x00 0x00 0x50 0x20 = Fixed-385
        - 0x00 0x00 0x50 0x21 = Custom-385
    - Frequency
        - 0x00 0x00 0x00 0x00 = Auto
    - Current
        - 0x00 0x00 0x21 0x02 = 4-20 mA
            - Adjust the MxA+B multiplier by `A = A * (1 / Shunt_resistance) * 6250`
            - Adjust MxA+B offset by `B = B - 25`
        - 0x00 0x00 0x25 0x20 = 0-100 mA
            - Adjust the MxA+B multiplier by `A = A * (1 / Shunt_resistance)`
- Extra configuration
    - Analog channels
        - RTD Alpha 32-bit float
        - Shunt resistance / RTD R0 32-bit float
        - Extra configuration 4-byte
            - 0x00 0x00 0x90 0x00 = 2 Wire mode (Ohms 2W)
            - 0x00 0x00 0x90 0x01 = 4 Wire mode (RTD 4W, Ohms 4W)
            - 0x00 0x00 0x00 0x01 = Open Thermocouple detect
            - 0x00 0x00 0x70 0x01 = Current mode (0-100mA, Amps)
            - 0x00 0x00 0x70 0x02 = Current mode (4-20mA, Percent)
    - Computed channels
        - Average
            - 0x00 0x00 0x00 0x00
            - 0x00 0x00 0x00 0x00
            - Averaged channels bitmask 4-byte
        - A - B
            - Channel A 4-byte
            - 0x00 0x00 0x00 0x00
            - Channel B 4-byte
        - A - Average
            - Channel A 4-byte
            - 0x00 0x00 0x00 0x00
            - Averaged channels bitmask 4-byte
        - Equation
            - 0x00 0x00 0x00 0x00
            - 0x00 0x00 0x00 0x00
            - Offset of equation in trailer 4-byte
- Alarm 4-byte
    - Bit pattern (most significant first) of last 5 bits, all others 0:
        - Alarm 2 HI
        - Alarm 2 LO
        - Alarm 1 HI
        - Alarm 1 LO
        - Use channel as alarm trigger
- Alarm 1 level 32-bit float
- Alarm 2 level 32-bit float
- Alarm 1 digital output, 4 byte
    - Bit of alarm index is set (0x01 = DO0, 0x02 = DO1, 0x04 = DO2, ...,  0x80 = DO7, etc)
- Alarm 2 digital output, 4 byte
    - Bit of alarm index is set (0x01 = DO0, 0x02 = DO1, 0x04 = DO2, ...,  0x80 = DO7, etc)
- MxA+B multiplier (A) 32-bit float
- MxA+B offset (B) 32-bit float
