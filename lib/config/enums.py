from enum import Enum


class DAQCommand(Enum):
    PING = 0x00000000
    CLOSE = 0x00000001
    STATUS_QUERY = 0x00000002
    GET_READINGS = 0x00000064
    START = 0x00000067
    STOP = 0x00000068
    SET_TIME = 0x0000006A
    QUERY_SPY = 0x0000006F
    RESET_TOTALIZER = 0x00000071
    GET_VERSION_INFO = 0x00000072
    SET_MONITOR_CHANNEL = 0x00000075
    CLEAR_MONITOR_CHANNEL = 0x00000076
    GET_BASE_CHANNEL = 0x00000077
    ENABLE_SPY = 0x0000007C
    DISABLE_SPY = 0x0000007D
    GET_LC_VERSION = 0x0000007F
    SET_CONFIG = 0x00000081


class DAQConfigBits(Enum):
    MEDIUM_SPEED = 0x0001
    FAST_SPEED = 0x0002
    FAHRENHEIT = 0x0004
    TRIGGER_OUT = 0x0008
    DRIFT_CORRECTION = 0x0010
    TOTALIZER_DEBOUNCE = 0x0020
    INTERVAL_TRIGGER = 0x0040
    ALARM_TRIGGER = 0x0080
    EXTERNAL_TRIGGER = 0x0100


class DAQConfigSpeed(Enum):
    SLOW = 0x0000
    MEDIUM = 0x0001
    FAST = 0x0002


class DAQConfigTrigger(Enum):
    INTERVAL = 0x0040
    ALARM = 0x0080
    EXTERNAL = 0x0100


class DAQConfigAlarm(Enum):
    OFF = 0x00
    HIGH = 0x01
    LOW = 0x02


class DAQAnalogMeasuremenType(Enum):
    OFF = 0x00000000
    Ohms = 0x00000001
    VDC = 0x00000002
    VAC = 0x00000004
    Frequency = 0x00000008
    RTD = 0x00000010
    Thermocouple = 0x00000020
    Current = 0x00010002


class DAQComputedMeasurementType(Enum):
    OFF = 0x00000000
    Average = 0x00008001
    AminusB = 0x00008002
    AminusAvg = 0x00008003
    Equation = 0x00008004


class DAQVDCRange(Enum):
    VDC_90mV = 0x2001
    VDC_300mV = 0x2102
    VDC_3V = 0x2308
    VDC_30V = 0x2410
    VDC_AUTO = 0x2520
    VDC_50V = 0x2640


class DAQVACRange(Enum):
    VAC_300mV = 0x3001
    VAC_3V = 0x3102
    VAC_30V = 0x3204
    VAC_AUTO = 0x3308


class DAQOhmsRange(Enum):
    Ohms_300 = 0x1001
    Ohms_3k = 0x1102
    Ohms_30k = 0x1204
    Ohms_300k = 0x1308
    Ohms_3M = 0x1410
    Ohms_AUTO = 0x1520


class DAQCurrentRange(Enum):
    Current_20mA = 0x2102
    Current_100mA = 0x2520


class DAQThermocoupleRange(Enum):
    TC_J = 0x6001
    TC_K = 0x6101
    TC_E = 0x6201
    TC_T = 0x6301
    TC_R = 0x6401
    TC_S = 0x6501
    TC_B = 0x6601
    TC_C = 0x6701
    TC_N = 0x6801


class DAQRTDRange(Enum):
    RTD_FIXED_385 = 0x5020
    RTD_CUSTOM_385 = 0x5021
