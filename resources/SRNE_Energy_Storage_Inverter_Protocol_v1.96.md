# SRNE.Solar.Charge.Inverter.MODBUS.Protocol1.96

## Page 1

深圳硕日新能源科技有限公司 Revision Record MODBUS Protocol for Energy Storage
Inverter Revision Record S/N Revision Content Revised byRevised onVer. No. 11.
Two registers (with inverter fault state, charging state, and unique ID) defined
by RGSC are increased. 2. Units of minimum, maximum, and default values are
removed (for protocol conversion code). 3. The BMS enable register and BMS
protocol register are increased. 4. The charging time and discharging time
registers are increased (to achieve timed charging and discharging). 5. The
state register is removed (not available and memory occupied). 6. The protocol
structure is modified (refer to the controller protocol).zhengkk July 14, 2021
V1.4 21. The definition of the current state value (8: battery activation, 9:
manual shutdown, 10: fault) of the machine is modified. 2. The default values of
some loop parameters are set to 4096. When used in the program, 4096 is used as
the default value. 3. The battery type is GEL (3) by default. If there is a
difference in the program, it may be customized according to the customer ID. 4.
The original Baud rate is changed to Parallel Mode. 5. The output priority is 2
(SBU) by default. If there is a difference in the program, it may be customized
according to the customer ID.zhengkkSeptember 16, 2021V1.5 3The Modbus protocol
format specification and the register address table are merged into a single
file. Note:

1. If the version No. on the page is incorrect, you only need to modify the
   table name. The title and version No. at the header are automatically updated
   without manual modification.
2. When releasing the version with neutral packing, you need to replace the
   company name at the page of the two files with "protocol", and do not delete
   the original characters; otherwise, the format will change when the company
   name is added next time.zhengkkSeptember 24, 2021V1.5
3. The protocol is revised, and the register is increased to supports single
   split-phase machine, two-way PV input and three-way AC power input, and
   three-way inverter output data transmission.
4. E218 register address is added to set the derated power of the machine.wangqt
   June 14, 2022 V1.6
5. The time of segmental charging and discharging and their enable settings are
   increased.
6. The settings of grid-connected generation and leakage detection are
   increased.wangzw June 1, 2022 V1.7
7. The single split-phase machine borrows the adjustment parameter addresses of
   the PLL, DF43 and DF44, to adjust the iteration control parameters; and the
   data type is changed to the signed number, and the default value is changed.
8. The maximum value of boost charge time E102 is changed to 900, consistent
   with the range set on the display.
9. The E21F address is added to set the grid-connected PF value.
10. The data annotation error in the E004 battery type and address (12-L13 and
    13-L14) is fixed.
11. The error cumulative charging unit and mismatch of proportion and actual
    quantity of AC power are fixed, and the cumulative charging unit is changed
    to the same as the charging unit on the day, which is AH.
12. The 0×214 address is changed back to the AC power phase-A current
    (generation-3 parallel machine also uses this address as the parallel
    current), and 0×238−0×239 are increased as the power phase-B and phase-C
    wangqt July 28, 2022 V1.7
13. EOOF is used for discharge cutoff SOC setting and is valid in BMS
    communication.
14. E01C is used to set the current for the lithium battery to stop charging.
15. E01D is used to set the SOC for the lithium battery to stop charging.
16. E01E is used to set the low SOC capacity alarm and is valid for BMS
    communication.
17. E01F is used to change the SOC capacity setting of the AC power in SBU mode
    and is valid for BMS communication.
18. E020 is used to change the SOC capacity setting of the inverter in SBU mode
    and is valid for BMS communication.zhengkk August 2, 2022 V1.7
19. E207 is changed to enable the N wire grounding, which is available only for
    some models.
20. The number of historical fault records is increased to 32.zhengkkNovember
    11, 2022V1.80
21. The register for grid-connected voltage protection is increased.
22. Grid-connected active, reactive, and PF registers are increased.
23. Grid-connected power register is increased.
24. The insulation impedance detection enable and threshold setting registers
    are increased.
25. The grid-connected current F02C on the day is increased.zhengkkFebruary 13,
    2023V1.90
26. The PV output priority is increased.
27. Grid-connected parameters are independently placed in group 08.zhengkk March
    7, 2023 V1.91

---

## Page 2

深圳硕日新能源科技有限公司 Revision Record 11 1. The DC load switch is
increased. zhengkk March 8, 2023 V1.92 121. Diesel engine operating mode and
diesel engine charging current setting parameters are increased. 2. The function
settings of battery participating in grid connection are increased. 3. The
grid-connected active power is changed to the actual power. 4. Diesel engine
voltage calibration coefficient is increased.zhengkk August 4, 2023 V1.93 131.
The battery temperature register 0×0103 is increased. 2. 0×E037 register is
changed to an operating mode register. 3. 0×E03A is modified to enable battery
temperature compensation. 4. The SOC value corresponding to the charge and
discharge period (0×E03B−0×E040) is added. 5. 0×E204 is changed to bms
communication fault stop register. 6. Diesel engine rated power setting 0×E221
is increased. 7. The CT ratio register 0×E42B is increased. 8. Anti-reverse and
anti-error power setting register 0×E42C is increased.zhengkkOctober 8,
2023V1.94 141. A/B/C phase home load register is increased. 2. The battery
voltage determination register for the timed charging and discharging period is
increased. 3. The maximum power register for timed discharging is increased. 4.
The normal network latency register is increased. 5. The register for
normal/reconnected power rise rate is increased. 6. The register for network
voltage frequency range is increased.zhengkkJanuary 4, 2024V1.95 151. The
maximum power register for timed charging is increased. 2. The register for
timed charging source selection is increased.zhengkkJanuary 11, 2024V1.96

---

## Page 3

深圳硕日新能源科技有限公司 Format Specification of the MOD Format Specification
of the MODBUS Protocol for Energy Storage Inverter

1. Document Description This document defines the content of RS485 communication
   protocol for the Company's energy storage inverters, including RS485
   communication frame format, Modbus register address definition, quantity
   calibration, etc. The protocol follows the Modubus-RTU protocol and supports
   03, 06, and 10 function codes. The maximum number of read-write registers at
   a time is 32.
2. Serial Communication Parameters "9,600, n, 8, 1" indicates a baud rate of
   9,600, with 8 data bits, and no parity check. There are one host and multiple
   slaves in RS485 connection mode. The default address of the inverter is 1,
   which can be set. It supports 255 universal address. When a host and an
   inverter are connected one to one, 255 can be used to communicate with the
   inverter. The address that the inverter responds to is the actual address.
3. Data Format Slave IP Address Function Code Data Length or Content CRC Check 1
   byte 1 byte N bytes 2 bytes Slave IP address range: 01H to FEH Host IP
   broadcast address: 0 Universal address: FFH03HReading multiple registers
   Command relatedCheck range: all data from the slave IP address to the CRC
   check; Transmission order: The CRC calculates the result as 16-bit data. In
   actual transmission, the low byte is passed first, and the high byte is
   passed later.06H Writing a single register 10HWriting multiple registers
   Miscellane ousInvalid 3.1 Reading the data frame format Frame format sent by
   the host: Slave IP Address Function Code Data Field CRC Check 1 byte 1 byte 4
   bytes 2 bytes Actual address 03HHigh byte of register addressLow byte of
   register addressN high bytes of registers, usually 00HN low bytes of
   registers (N<=32) CRC_L CRC_H 1 3 02H 00H 00H 20H 45H AAH Data frame format
   returned from the slave IP: Slave IP Address Function Code Data Field CRC
   Check 1 byte 1 byte(2*N+1) bytes 2 bytes 1 byte 1 byte1 byte1 byte1 byte…
   Actual address 03HByte length of the returned dataReturned data CRC_L CRC_H
   Register 1 valueRegister 2 value… High byteLow byteHigh byteLow byte… Error
   frame format returned from the slave IP: Slave IP Address Function Code Error
   Code CRC Check 1 byte 1 byte 1 byte 2 bytes Actual address 83H See the error
   code table. CRC_LCRC_H 3.2 Writing multiple data frame formats 3/18

---

## Page 4

深圳硕日新能源科技有限公司 Format Specification of the MOD Frame format sent by
the host: Slave IP Address Function Code Data Field CRC Check 1 byte 1 byte5+2*N
bytes2 bytes 1 byte 1 byte 1 byte1 byte1 byte 2*N bytes Actual address
10HRegister address Register countData LengthFor the value of N registers, the
high byte precedes the low byte. 高字节在前CRC_L CRC_H High byte Low byteHigh
byteLow byte2*N Response frame format returned from the slave IP: Slave IP
Address Function Code Data length CRC Check 1 byte 1 byte 1 byte 1 byte 1 byte1
byte 2 bytes Actual address 10HRegister address Register count High byte Low
byteHigh byteLow byteCRC_LCRC_H Error frame format returned from the slave IP:
Slave IP Address Function Code Error Code CRC Check 1 byte 1 byte 1 byte 2 bytes
Actual address 90H See the error code table. CRC_LCRC_H 3.3 Writing a single
data frame format Frame format sent by the host: Slave IP Address Function Code
Data Field CRC Check 1 byte 1 byte 1 byte 1 byte 1 byte1 byte 2 bytes Actual
address 06HRegister address Register value CRC_LCRC_HHigh byte Low byteHigh
byteLow byte Response frame format returned from the slave IP: Slave IP Address
Function Code Data Field CRC Check 1 byte 1 byte 1 byte 1 byte 1 byte1 byte 2
bytes Actual address 06HRegister address Register valueCRC_LCRC_HHigh byte Low
byteHigh byteLow byte Error frame format returned from the slave IP: Slave IP
Address Function Code Error Code CRC Check 1 byte 1 byte 1 byte 2 bytes Actual
address 86H See the error code table. CRC_LCRC_H 3.4 Error code table Code Name
Meaning 01H Illegal command The slave may not support this command. 02H Illegal
data address The register address requested by the host is out of the legal
register address range defined by the slave. 03H Illegal data value The register
value requested by the host is out of the register value range defined by the
slave. 04H Operation failure The parameter write operation is invalid for the
parameter setting, or the slave does not support the command. 05H Password error
The password is error for the address validation. 06H Data frame errorThe length
of the data frame sent by the host is incorrect, and the CRC check bit in RTU
format is different from that calculated by the slave. 07H Parameter read-only
Parameters changed during the host write operation are read-only. 08HParameters
cannot be modified during operation The parameters that are modified during the
host write operation are the those that cannot be changed during running. 09H
Password protection When the host is reading or writing, the system is reported
to be locked if the password is set and locked. 0AH Length error The number of
read/write registers exceeds the upper limit 32. 4/18

---

## Page 5

深圳硕日新能源科技有限公司 Format Specification of the MOD 0BH Permission denied
There is no permission to perform this operation 4. CRC Check Computation The
CRC domain verifies the content of the entire frame, that is, all data from the
slave IP address to the CRC check. The slave retests the CRC check data and
compares it with the check value in the received data stream to determine the
validity of the received data. The CRC domain consists of two-byte and 16-bit
binary value data. In actual transmission, the low byte is passed first, and the
high byte is passed later. There are three methods to calculate the CRC check
value. If the results of the three methods are the same, you can choose them
freely according to the actual situation. Method 1: cycle computation by bit
unsigned int crc_cal_value(unsigned char*data_value,unsigned char data_length) {
int i; unsigned int crc_value=0xffff; while(data_length--) {
crc_value^=*data_value++; for(i=0;i<8;i++) { if(crc_value&0x0001)
crc_value=(crc_value>>1)^0xa001; else crc_value=crc_value>>1; } }
return(crc_value); } Method 2: byte lookup table /_CRC value of the high byte_/
static unsigned int auchCRCHi[] = { 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80,
0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01,
0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80,
0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01,
0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1,
0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40,
0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00,
0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0,
0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81,
0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01,
0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0,
0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81,
0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41,
0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00,
0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1,
0x81, 0x40, }; 5/18

---

## Page 6

深圳硕日新能源科技有限公司 Format Specification of the MOD /_CRC value of the
low byte_/ static unsigned int auchCRCLo[] = { 0x00, 0xC0, 0xC1, 0x01, 0xC3,
0x03, 0x02, 0xC2, 0xC6, 0x06, 0x07, 0xC7, 0x05, 0xC5, 0xC4, 0x04, 0xCC, 0x0C,
0x0D, 0xCD, 0x0F, 0xCF, 0xCE, 0x0E, 0x0A, 0xCA, 0xCB, 0x0B, 0xC9, 0x09, 0x08,
0xC8, 0xD8, 0x18, 0x19, 0xD9, 0x1B, 0xDB, 0xDA, 0x1A, 0x1E, 0xDE, 0xDF, 0x1F,
0xDD, 0x1D, 0x1C, 0xDC, 0x14, 0xD4, 0xD5, 0x15, 0xD7, 0x17, 0x16, 0xD6, 0xD2,
0x12, 0x13, 0xD3, 0x11, 0xD1, 0xD0, 0x10, 0xF0, 0x30, 0x31, 0xF1, 0x33, 0xF3,
0xF2, 0x32, 0x36, 0xF6, 0xF7, 0x37, 0xF5, 0x35, 0x34, 0xF4, 0x3C, 0xFC, 0xFD,
0x3D, 0xFF, 0x3F, 0x3E, 0xFE, 0xFA, 0x3A, 0x3B, 0xFB, 0x39, 0xF9, 0xF8, 0x38,
0x28, 0xE8, 0xE9, 0x29, 0xEB, 0x2B, 0x2A, 0xEA, 0xEE, 0x2E, 0x2F, 0xEF, 0x2D,
0xED, 0xEC, 0x2C, 0xE4, 0x24, 0x25, 0xE5, 0x27, 0xE7, 0xE6, 0x26, 0x22, 0xE2,
0xE3, 0x23, 0xE1, 0x21, 0x20, 0xE0, 0xA0, 0x60, 0x61, 0xA1, 0x63, 0xA3, 0xA2,
0x62, 0x66, 0xA6, 0xA7, 0x67, 0xA5, 0x65, 0x64, 0xA4, 0x6C, 0xAC, 0xAD, 0x6D,
0xAF, 0x6F, 0x6E, 0xAE, 0xAA, 0x6A, 0x6B, 0xAB, 0x69, 0xA9, 0xA8, 0x68, 0x78,
0xB8, 0xB9, 0x79, 0xBB, 0x7B, 0x7A, 0xBA, 0xBE, 0x7E, 0x7F, 0xBF, 0x7D, 0xBD,
0xBC, 0x7C, 0xB4, 0x74, 0x75, 0xB5, 0x77, 0xB7, 0xB6, 0x76, 0x72, 0xB2, 0xB3,
0x73, 0xB1, 0x71, 0x70, 0xB0, 0x50, 0x90, 0x91, 0x51, 0x93, 0x53, 0x52, 0x92,
0x96, 0x56, 0x57, 0x97, 0x55, 0x95, 0x94, 0x54, 0x9C, 0x5C, 0x5D, 0x9D, 0x5F,
0x9F, 0x9E, 0x5E, 0x5A, 0x9A, 0x9B, 0x5B, 0x99, 0x59, 0x58, 0x98, 0x88, 0x48,
0x49, 0x89, 0x4B, 0x8B, 0x8A, 0x4A, 0x4E, 0x8E, 0x8F, 0x4F, 0x8D, 0x4D, 0x4C,
0x8C, 0x44, 0x84, 0x85, 0x45, 0x87, 0x47, 0x46, 0x86, 0x82, 0x42, 0x43, 0x83,
0x41, 0x81, 0x80, 0x40, }; /_function returns CRC as an unsigned short_/
/_parameter puchMsg: the message used to calculate CRC_/ /_parameter usDataLen:
the number of bytes in the message_/ unsigned int CRC16(unsigned int *
puchMsg,unsigned int usDataLen) { unsigned int uchCRCHi = 0xFF ; /_high byte
initialization of CRC_/ unsigned int uchCRCLo = 0xFF ; /_low byte initialization
of CRC_/ unsigned int uIndex ; /_CRC lookup table index_/ while (usDataLen--)
/_complete the entire message buffer_/ { uIndex = uchCRCLo ^ *puchMsg++ ;
/_CalcCRC_/ uchCRCLo = uchCRCHi ^ auchCRCHi[uIndex] ; uchCRCHi =
auchCRCLo[uIndex] ; } return (uchCRCHi << 8 | uchCRCLo) ; } Method 3: word
lookup table Static unsigned int tblCRC[] = {
0x0000,0xC1C0,0x81C1,0x4001,0x01C3,0xC003,0x8002,0x41C2,
0x01C6,0xC006,0x8007,0x41C7,0x0005,0xC1C5,0x81C4,0x4004,
0x01CC,0xC00C,0x800D,0x41CD,0x000F,0xC1CF,0x81CE,0x400E,
0x000A,0xC1CA,0x81CB,0x400B,0x01C9,0xC009,0x8008,0x41C8,
0x01D8,0xC018,0x8019,0x41D9,0x001B,0xC1DB,0x81DA,0x401A,
0x001E,0xC1DE,0x81DF,0x401F,0x01DD,0xC01D,0x801C,0x41DC,
0x0014,0xC1D4,0x81D5,0x4015,0x01D7,0xC017,0x8016,0x41D6,
0x01D2,0xC012,0x8013,0x41D3,0x0011,0xC1D1,0x81D0,0x4010,
0x01F0,0xC030,0x8031,0x41F1,0x0033,0xC1F3,0x81F2,0x4032,
0x0036,0xC1F6,0x81F7,0x4037,0x01F5,0xC035,0x8034,0x41F4,
0x003C,0xC1FC,0x81FD,0x403D,0x01FF,0xC03F,0x803E,0x41FE,
0x01FA,0xC03A,0x803B,0x41FB,0x0039,0xC1F9,0x81F8,0x4038,
0x0028,0xC1E8,0x81E9,0x4029,0x01EB,0xC02B,0x802A,0x41EA,
0x01EE,0xC02E,0x802F,0x41EF,0x002D,0xC1ED,0x81EC,0x402C,
0x01E4,0xC024,0x8025,0x41E5,0x0027,0xC1E7,0x81E6,0x4026,
0x0022,0xC1E2,0x81E3,0x4023,0x01E1,0xC021,0x8020,0x41E0,
0x01A0,0xC060,0x8061,0x41A1,0x0063,0xC1A3,0x81A2,0x4062,
0x0066,0xC1A6,0x81A7,0x4067,0x01A5,0xC065,0x8064,0x41A4,
0x006C,0xC1AC,0x81AD,0x406D,0x01AF,0xC06F,0x806E,0x41AE,
0x01AA,0xC06A,0x806B,0x41AB,0x0069,0xC1A9,0x81A8,0x4068,
0x0078,0xC1B8,0x81B9,0x4079,0x01BB,0xC07B,0x807A,0x41BA,
0x01BE,0xC07E,0x807F,0x41BF,0x007D,0xC1BD,0x81BC,0x407C,
0x01B4,0xC074,0x8075,0x41B5,0x0077,0xC1B7,0x81B6,0x4076,
0x0072,0xC1B2,0x81B3,0x4073,0x01B1,0xC071,0x8070,0x41B0,
0x0050,0xC190,0x8191,0x4051,0x0193,0xC053,0x8052,0x4192,
0x0196,0xC056,0x8057,0x4197,0x0055,0xC195,0x8194,0x4054,
0x019C,0xC05C,0x805D,0x419D,0x005F,0xC19F,0x819E,0x405E,
0x005A,0xC19A,0x819B,0x405B,0x0199,0xC059,0x8058,0x4198,
0x0188,0xC048,0x8049,0x4189,0x004B,0xC18B,0x818A,0x404A,
0x004E,0xC18E,0x818F,0x404F,0x018D,0xC04D,0x804C,0x418C,
0x0044,0xC184,0x8185,0x4045,0x0187,0xC047,0x8046,0x4186,
0x0182,0xC042,0x8043,0x4183,0x0041,0xC181,0x8180,0x4040, }; /_function returns
CRC as an unsigned short_/ /_parameter puchMsg: the message used to calculate
CRC_/ /_parameter usDataLen: the number of bytes in the message_/ unsigned int
CRC16(unsigned int * puchMsg,unsigned int usDataLen) { unsigned int uchCRCHi =
0xFF ; /_high byte initialization of CRC_/ unsigned int uchCRCLo = 0xFF ; /_low
byte initialization of CRC_/ unsigned int uIndex ; /_CRC lookup table index_/
unsigned int hi,low; while (usDataLen--) /_complete the entire message buffer_/
{ uIndex = uchCRCLo ^ *puchMsg++ ; /_CalcCRC_/ hi = tblCRC[uIndex] >> 8; low =
tblCRC[uIndex] & 0xff; uchCRCLo = uchCRCHi ^ hi; uchCRCHi = low; } return
(uchCRCHi << 8 | uchCRCLo) ; }6/18

---

## Page 7

深圳硕日新能源科技有限公司 Format Specification of the MODStatic unsigned int
tblCRC[] = { 0x0000,0xC1C0,0x81C1,0x4001,0x01C3,0xC003,0x8002,0x41C2,
0x01C6,0xC006,0x8007,0x41C7,0x0005,0xC1C5,0x81C4,0x4004,
0x01CC,0xC00C,0x800D,0x41CD,0x000F,0xC1CF,0x81CE,0x400E,
0x000A,0xC1CA,0x81CB,0x400B,0x01C9,0xC009,0x8008,0x41C8,
0x01D8,0xC018,0x8019,0x41D9,0x001B,0xC1DB,0x81DA,0x401A,
0x001E,0xC1DE,0x81DF,0x401F,0x01DD,0xC01D,0x801C,0x41DC,
0x0014,0xC1D4,0x81D5,0x4015,0x01D7,0xC017,0x8016,0x41D6,
0x01D2,0xC012,0x8013,0x41D3,0x0011,0xC1D1,0x81D0,0x4010,
0x01F0,0xC030,0x8031,0x41F1,0x0033,0xC1F3,0x81F2,0x4032,
0x0036,0xC1F6,0x81F7,0x4037,0x01F5,0xC035,0x8034,0x41F4,
0x003C,0xC1FC,0x81FD,0x403D,0x01FF,0xC03F,0x803E,0x41FE,
0x01FA,0xC03A,0x803B,0x41FB,0x0039,0xC1F9,0x81F8,0x4038,
0x0028,0xC1E8,0x81E9,0x4029,0x01EB,0xC02B,0x802A,0x41EA,
0x01EE,0xC02E,0x802F,0x41EF,0x002D,0xC1ED,0x81EC,0x402C,
0x01E4,0xC024,0x8025,0x41E5,0x0027,0xC1E7,0x81E6,0x4026,
0x0022,0xC1E2,0x81E3,0x4023,0x01E1,0xC021,0x8020,0x41E0,
0x01A0,0xC060,0x8061,0x41A1,0x0063,0xC1A3,0x81A2,0x4062,
0x0066,0xC1A6,0x81A7,0x4067,0x01A5,0xC065,0x8064,0x41A4,
0x006C,0xC1AC,0x81AD,0x406D,0x01AF,0xC06F,0x806E,0x41AE,
0x01AA,0xC06A,0x806B,0x41AB,0x0069,0xC1A9,0x81A8,0x4068,
0x0078,0xC1B8,0x81B9,0x4079,0x01BB,0xC07B,0x807A,0x41BA,
0x01BE,0xC07E,0x807F,0x41BF,0x007D,0xC1BD,0x81BC,0x407C,
0x01B4,0xC074,0x8075,0x41B5,0x0077,0xC1B7,0x81B6,0x4076,
0x0072,0xC1B2,0x81B3,0x4073,0x01B1,0xC071,0x8070,0x41B0,
0x0050,0xC190,0x8191,0x4051,0x0193,0xC053,0x8052,0x4192,
0x0196,0xC056,0x8057,0x4197,0x0055,0xC195,0x8194,0x4054,
0x019C,0xC05C,0x805D,0x419D,0x005F,0xC19F,0x819E,0x405E,
0x005A,0xC19A,0x819B,0x405B,0x0199,0xC059,0x8058,0x4198,
0x0188,0xC048,0x8049,0x4189,0x004B,0xC18B,0x818A,0x404A,
0x004E,0xC18E,0x818F,0x404F,0x018D,0xC04D,0x804C,0x418C,
0x0044,0xC184,0x8185,0x4045,0x0187,0xC047,0x8046,0x4186,
0x0182,0xC042,0x8043,0x4183,0x0041,0xC181,0x8180,0x4040, }; /_function returns
CRC as an unsigned short_/ /_parameter puchMsg: the message used to calculate
CRC_/ /_parameter usDataLen: the number of bytes in the message_/ unsigned int
CRC16(unsigned int * puchMsg,unsigned int usDataLen) { unsigned int uchCRCHi =
0xFF ; /_high byte initialization of CRC_/ unsigned int uchCRCLo = 0xFF ; /_low
byte initialization of CRC_/ unsigned int uIndex ; /_CRC lookup table index_/
unsigned int hi,low; while (usDataLen--) /_complete the entire message buffer_/
{ uIndex = uchCRCLo ^ *puchMsg++ ; /_CalcCRC_/ hi = tblCRC[uIndex] >> 8; low =
tblCRC[uIndex] & 0xff; uchCRCLo = uchCRCHi ^ hi; uchCRCHi = low; } return
(uchCRCHi << 8 | uchCRCLo) ; } 4. Unit and Dimension Description Physical
Quantity UnitMagnificatio nDescription Voltage (including AC and DC)V 10 16-bit
unsigned integer ranging from 0 to 65,535, corresponding to 0 V to 6,553.5 V
Current (including AC and DC)A 1016-bit unsigned integer ranging from 0 to
65,535, corresponding to 0 A to 6,553.5 A 16-bit signed integer ranging from
-32,767 to 32,767, corresponding to -3,276.7 A to 3,276.7 A 7/18

---

## Page 8

深圳硕日新能源科技有限公司 Format Specification of the MOD Frequency Hz 100
16-bit unsigned integer ranging from 0 to 65,535, corresponding to 0 Hz to
655.35 Hz Power (including AC and DC)W 1 16-bit unsigned integer ranging from 0
to 65,535, corresponding to 0 W to 65,535 W Power factor / 100016-bit signed
integer ranging from -32,767 to 32,767 (e.g., 998 indicates a power factor of
0.998; and -900 (0×FC7C) indicates a power factor of -0.900.) AC side capacity
kWh 1016-bit unsigned integer ranging from 0 to 65,535, corresponding to 0 kWh
to 6,553.5 kWh; 32-bit unsigned integer ranging from 0 to 4,294,967,295,
corresponding to 0 kWh to 429,496,729.5 kWh; (e.g., 1 indicates 0.1 kWh and 10
indicates 1 KWH) Battery side capacity AH 116-bit unsigned integer ranging from
0 to 65,535, corresponding to 0 AH to 65,535 AH; 32-bit unsigned integer ranging
from 0 to 4,294,967,295, corresponding to 0 AH to 4,294,967,295 AH Temperature
°C 1016-bit signed integer ranging from -32,767 to 32,767, corresponding to
-3,276.7°C to 3,276.7°C Battery set voltage V 10All battery set voltages in this
protocol are in the unified dimension of 12 V batteries, that is, all battery
set voltages are converted to the corresponding voltage of 12 V. If the rated
voltage of the battery is 48 V and the actual set voltage is 57.6 V, the set
value is 57.6 V/4=14.4 V, and the value converted for the register is
14.4*10=144. Note: When 32-bit data occupies two registers, the data is stored
in the register in small-endian mode, that is, the low bytes of data are in the
low address of the register, and the high bytes are in the high address of the
register. If the 32-bit data 0×12345678 is stored at 0×0001 and 0×0002, the
order in the register table is 0×0001=0×5678 and 0×0002=0×1234. 8/18

---

## Page 9

深圳硕日新能源科技有限公司 MODBUS Protocol for Energy Stor MODBUS Protocol for
Energy Storage Inverter - Register Address Table Note:

1. The register displayed in gray font is invalid for the energy storage
   inverter.
2. Magnification refers to the multiple of the actual value than the register
   value. If the magnification is 0.1, the actual value is the register value
   multiplied by 0.1. AddressLength Name English Name R/WMagnif
   icationUnitDisplay FormatSigned/Unsign edMinimu mMaximu mDefault Remark P00
   Product Information Area A 1 小版本号 MinorVersion R 1 - %d Unsigned Reserved
   B 1 产品类型 MachType R 1 - %d UnsignedProduct type 00 (domestic controller)
   01 (controller for street light) 03 (grid-connected inverter) 04 (all-in-one
   solar charger inverter) 05 (power frequency off-grid) C 8 保留
   ProductInfoReversed01 R 1 - %s Unsigned Reserved 14 2 软件版本
   SoftWareVersion R 1 - %d Unsigned0×0014: APP version (e.g.,100 for V1.00)
   0×0015: BOOTLOADER version (e.g.,100 for V1.00), reserved 16 2 硬件版本
   HardWareVersion R 1 - %d Unsigned0×0016: control panel version (e.g.,100 for
   V1.00) 0×0017: power amplifier board version (e.g.,100 for V1.00), reserved
   18 2 保留 ProductInfoReversed02 R 1 - %x Unsigned Reserved 1A 1
   控制器、设备地址 Rs485Addr R 1 - %d Unsigned Rs485 address, which is
   read-only 1B 1 机型编码 MachModelNum2 R 1 - %d Unsigned 1C 2 RS485协议版本
   RS485Version R 1 - %x Unsigned0×001C: protocol version (e.g.,100 for V1.00)
   0×001D: reserved 1E 2 生产日期 ManufactureDate R 1 - %x Unsigned0×001E: high
   byte: year, low byte: month 0×001F: high byte: day, low byte: hour 20 1
   产地编码 ProductAreaCode R 1 - %x Unsigned0: Shenzhen 1: Dongguan 21 20
   软件编译时间 CpuBuidTime R 1 - %s UnsignedString format, with the low bytes
   of each register valid and the high bytes invalid 35 20 产品序列号字符串
   ProductSNStr R 1 - %s UnsignedString format, with the low bytes of each
   register valid and the high bytes invalid 49 1 保留 ProductInfoReversed03 R
   1 - %x Unsigned P01 DC Data Area 100 1 蓄电池电量SOC BatSoc R 1 - %d Unsigned
   Percentage of remaining battery power 101 1 蓄电池电压 BatVolt R 0.1 V %.1fV
   Unsigned Battery voltage (e.g., 485 for 48.5 V) 102 1 电池电流 ChargeCurr R
   0.1 A %.1fA SignedBattery current (e.g., 500 for 50.0A) Current greater than
   0 indicates discharging; and current less than 0 indicates charging. 103 1
   电池温度 DeviceBatTemper R 0.1 °C %.1f℃ Signed Battery temperature 104 1 保留
   DcDataRevserved00 R 0.1 V %.1fV Unsigned Reserved 105 1 保留
   DcDataRevserved01 R 0.01 A %.2fA Unsigned Reserved 106 1 保留
   DcDataRevserved02 R 1 W %d Unsigned Reserved 107 1 太阳能板1电压 Pv1Volt R
   0.1 V %.1fV Unsigned Voltage of PV panel 1 108 1 太阳能板1电流 Pv1Curr R 0.1
   A %.1fA Unsigned Current of PV panel 1 109 1 太阳能板1功率 Pv1ChargePower R 1
   W %d Unsigned Power of PV panel 1 10A 1 太阳能板总功率 PvTotalPower R 1 - %d
   Unsigned Total PV power 10B 1 电池充电状态 ChargeState R 1 - %d
   Unsigned0×0000: Charge off 0×0001: Quick charge 0×0002: Const voltage charge
   0×0004: Float charge 0×0005: Reserved 0×0006: Li battery activate 0×0008:
   Full 10C 2 保留 DcDataRevserved04 R 1 - %d Unsigned Reserved 10E 1 充电总功率
   ChargePower R 1 W %dW Unsigned PV charging power + AC charging power 10F 1
   太阳能板2电压 Pv2Volt R 0.1 V %.1fV Unsigned Voltage of PV panel 2 110 1
   太阳能板2电流 Pv2Curr R 0.1 A %.1fA Unsigned Current of PV panel 2 111 1
   太阳能板2功率 Pv2ChargePower R 1 W %d Unsigned Power of PV panel 2 P02
   Inverter Data Area 200 4 当前故障位 CurrErrReg R 1 - %x UnsignedEach fault
   bit represents a fault, with a total of 64 bits. This register is used by the
   internal debugging. 204 4 当前故障码 CurrFcode R 1 - %d UnsignedThere are
   four addresses. Each address stores a fault code corresponding to the current
   fault. Four fault codes can be displayed at the same time. 0 indicates no
   fault. If there are two faults, battery under-voltage and inverter overload,
   the following information is displayed: 0×204: 01 0×205: 14 0×206: 00 0×207:
   00 208 4 保留 ReservedInvData0 R 2 - %x Unsigned Reserved 20C 3 当前时间
   SysDateTime RW 1 - %zdt Unsigned0×020C: high byte: year, low byte: month
   0×020D: high byte: day, low byte: hour 0×020E: high byte: minute, low byte:
   second The register can be set to adjust the RTC clock. 20F 1 并网倒计时
   GridOnRemainTime R 1 s %d Unsigned 9/18

---

## Page 10

深圳硕日新能源科技有限公司 MODBUS Protocol for Energy Stor AddressLength Name
English Name R/WMagnif icationUnitDisplay FormatSigned/Unsign edMinimu mMaximu
mDefault Remark 210 1 机器当前状态 MachineState R 1 - %d Unsigned0: Power-on
delay 1: Standby state 2: Initialization 3: Soft start 4: AC power operation 5:
Inverter operation 6: Inverter to AC power 7: AC power to inverter 8: Battery
activation 9: Manual shutdown 10: Fault Split-phase all-in-one machines and
European standard single-phase 8−12K machines are as follows: 0: Initialization
1: Standby state 2: AC power operation 3: Inverter operation 211 1
密码保护状态标志 PriorityFlag R 1 - %d Unsigned0: Users have not entered
password 1: The password of users is entered 4: The password of the manufacturer
is entered 212 1 总母线电压 BusVoltSum R 0.1 V %.1fV Unsigned 213 1 电网A相电压
GridVoltA R 0.1 V %.1fV Unsigned AC power phase-A voltage 214 1 电网A相电流
GridCurrA R 0.1 A %.1fA Unsigned AC power phase-A current 215 1 电网频率
GridFreq R 0.01 Hz %.2fHz Unsigned AC power frequency 216 1 逆变A相电压 InvVoltA
R 0.1 V %.1fV Unsigned Inverter phase-A output voltage 217 1 逆变A相电流
InvCurrA R 0.1 A %.1fA Unsigned Inverter phase-A inductive current 218 1
逆变频率 InvFreq R 0.01 Hz %.2fHz Unsigned 219 1 负载A相电流 LoadCurrA R 0.1 A
%.1fA Unsigned Load side phase-A current 21A 1 负载PF LoadPF R 0.01 - %.2f
Signed Unused 21B 1 负载A相有功功率 LoadActivePowerA R 1 W %dW Unsigned Phase-A
load active power 21C 1 负载A相视在功率 LoadApparentPowerA R 1 VA %dVA Unsigned
Phase-A load apparent power 21D 1 逆变直流分量 InvDcVolt R 1 mV %dmV Signed
Unused 21E 1 市电充电电流 LineChgCurr R 0.1 A %.1fA Unsigned Charging current
from the AC power on the battery side 21F 1 A相负载率 LoadRatioA R 1 % %d%
Unsigned Phase-A load ratio 220 1 散热片A温度 Tempera R 0.1 °C %.1f℃ Signed
Cooling-fin DC-DC temperature 221 1 散热片B温度 Temperb R 0.1 °C %.1f℃ Signed
Cooling-fin DC-AC temperature 222 1 散热片C温度 Temperc R 0.1 °C %.1f℃ Signed
Transformer temperature 223 1 环境温度 Temperd R 0.1 °C %.1f℃ Signed Ambient
temperature 224 1 PV 充电电流 Ibuck1 R 0.1 A %.1fA Unsigned Charging current
from the PV power on the battery side 225 1 并机负载平均电流 ParallCurrRms R 0.1
A %.1fA Unsigned High-pressure parallel use 226 1 逆变器故障状态(RV)
Invfaultstate R 1 - %d Unsigned Available for customized models only 227 1
充电状态(RV) ChargeStatus R 1 - %d Unsigned Available for customized models only
228 1 正母线电压 PBusVolt R 0.1 V %.1fV UnsignedSuitable for the split-phase
all-in-one machine and European standard machine of 10 kW 229 1 负母线电压
NBusVolt R 0.1 V %.1fV UnsignedSuitable for the split-phase all-in-one machine
and European standard machine of 10 kW 22A 1 电网B相电压 GridVoltB R 0.1 V %.1fV
Unsigned AC power phase-B voltage 22B 1 电网C相电压 GridVoltC R 0.1 V %.1fV
Unsigned AC power phase-C voltage 22C 1 逆变B相电压 InvVoltB R 0.1 V %.1fV
Unsigned Inverter phase-B output voltage 22D 1 逆变C相电压 InvVoltC R 0.1 V
%.1fV Unsigned Inverter phase-C output voltage 22E 1 逆变B相电流 InvCurrB R 0.1
A %.1fA Unsigned Inverter phase-B inductive current 22F 1 逆变C相电流 InvCurrC R
0.1 A %.1fA Unsigned Inverter phase-C inductive current 230 1 负载B相电流
LoadCurrB R 0.1 A %.1fA Unsigned Load side phase-B current 231 1 负载C相电流
LoadCurrC R 0.1 A %.1fA Unsigned Load side phase-C current 232 1 负载B相有功功率
LoadActivePowerB R 1 W %dW Unsigned 233 1 负载C相有功功率 LoadActivePowerC R 1 W
%dW Unsigned 234 1 负载B相视在功率 LoadReactivePowerB R 1 VA %dVA Unsigned 235 1
负载C相视在功率 LoadReactivePowerC R 1 VA %dVA Unsigned 236 1 B相负载率
LoadRatioB R 1 % %d% Unsigned Phase-B load ratio 237 1 C相负载率 LoadRatioC R 1
% %d% Unsigned Phase-C load ratio 238 1 电网B相电流 GridCurrB R 0.1 A %.1fA
Unsigned AC power phase-B current 239 1 电网C相电流 GridCurrC R 0.1 A %.1fA
Unsigned AC power phase-C current 23A 1 A相电网有功功率 GridActivePowerA R 1 A
%dW SignedGreater than 0 for power of grid connection; Less than 0 for power of
grid consumption 23B 1 B相电网有功功率 GridActivePowerB R 1 A %dW SignedGreater
than 0 for power of grid connection; Less than 0 for power of grid consumption
23C 1 C相电网有功功率 GridActivePowerC R 1 A %dW SignedGreater than 0 for power
of grid connection; Less than 0 for power of grid consumption 23D 1
A相电网视在功率 GridApparentPowerA R 1 VA %dVA Unsigned 23E 1 B相电网视在功率
GridApparentPowerB R 1 VA %dVA Unsigned 23F 1 C相电网视在功率 GridApparentPowerC
R 1 VA %dVA Unsigned 240 1 A相HomeLoad功率 HomeLoadActivePowerA R 1 W %dW
Unsigned 241 1 B相HomeLoad功率 HomeLoadActivePowerB R 1 W %dW Unsigned 242 1
C相HomeLoad功率 HomeLoadActivePowerC R 1 W %dW Unsigned 243 1 保留
ReservedInvData2 R 1 W %dW Unsigned P03 Device Control Area DF00 1 开关机控制
CmdPowerOnOff W 1 - %x Unsigned0: Off 1: on Others: no action DF01 1 复位控制
CmdMachineReset W 1 - %x Unsigned1. Reset Others: no action DF02 1 恢复出厂值
CmdRestoreFactorySetting W 1 - %x Unsigned0×AA: restoring 0×BB: clear the
statistics (power statistics) 0×CC: clearing the fault history Others: no action
Restore factory set values to clear all cumulative data and restore parameters
to the default state, and restart to take effect. DF03 1 保留 CmdReserved00 W
1 - %x Unsigned Reserved DF04 1 保留 CmdReserved01 W 1 - %x Unsigned Reserved
DF05 1 保留 CmdReserved02 W 1 - %x Unsigned Reserved DF06 2 固件升级命令
UpgradeCmd W 1 - %x Unsigned Firmware upgrade command DF08 1 保留 CmdReserved03
W 1 - %x Unsigned Reserved DF09 3 保留 CmdReserved04 W 1 - %x Unsigned Reserved
DF0C 1 保留 CmdReserved05 W 1 - %x Unsigned Reserved DF0D 1 立即均衡充电指令
BattEqualChgImmediate W 1 %d Unsigned0: disabled 1: enabled 10/18

---

## Page 11

深圳硕日新能源科技有限公司 MODBUS Protocol for Energy Stor AddressLength Name
English Name R/WMagnif icationUnitDisplay FormatSigned/Unsign edMinimu mMaximu
mDefault Remark P05 Setting Area for Battery-related Parameters E000 1 保留
BatParmReserved0 RW 1 - %d Unsigned 0 1 0 E001 1 光伏最大充电电流设置
PvChgCurrSet RW 0.1 A %dA Unsigned 0 150 80PV charging current limit.
Generation-1 machine: 50 A, generation-2 machine: 60 A, and generation-3
machine: 80 A−100 A E002 1 蓄电池标称容量 BatRateCap RW 1 AH %dAH Unsigned 0 400
100 E003 1 电池额定电压（只读） BatRateVolt RW 1 V %dV Unsigned 12 255 4812: 12
V 24: 24 V 36: 36 V 48: 48 V E004 1 蓄电池类型 BatTypeSet RW 1 - %d Unsigned 0
14 60: User define 1: SLD 2: FLD 3: GEL 4: Lithium iron phosphate x 14 5:
Lithium iron phosphate x 15 6: Lithium iron phosphate x 16 7: Lithium iron
phosphate x 7 8: Lithium iron phosphate x 8 9: Lithium iron phosphate x 9 10:
Ternary lithium x 7 11: Ternary lithium x 8 12: Ternary lithium x 13 13: Ternary
lithium x 14 E005 1 超压电压 BatOverVolt RW 0.1 V %.1fV Unsigned 9 15.5
15.5Battery charging over-voltage protection point (converted to the voltage
corresponding to 12 V, followed by the same battery voltage) E006 1 充电限制电压
BatChgLimitVolt RW 0.1 V %.1fV Unsigned 9 15.5 14.4 Over-charging protection
voltage E007 1 均衡充电电压 BatConstChgVolt RW 0.1 V %.1fV Unsigned 9 15.5 14.4
Equalizing charging voltage E008 1 提升充电电压/过充电压 BatImprovChgVolt RW 0.1
V %.1fV Unsigned 9 15.5 14.4Lead-acid battery is prohibited from boost charge,
and lithium battery is prohibited from over-charging voltage. E009 1
浮充充电电压 BatFloatChgVolt RW 0.1 V %.1fV Unsigned 9 15.5 14 For lead-acid
battery E00A 1 提升充电返回电压 BatImprovChgBackVolt RW 0.1 V %.1fV Unsigned 9
15.5 13.2After the battery enters floating charging, the battery voltage is
lower than the judged point again, and the battery enters boost charge again.
E00B 1 过放返回电压 BatOverDischgBackVolt RW 0.1 V %.1fV Unsigned 9 15.5
12.6After the battery is protected from over-discharge and under-voltage, it is
returned to the discharged state. E00C 1 欠压警告电压 BatUnderVolt RW 0.1 V
%.1fV Unsigned 9 15.5 11 Alarming of low battery voltage without load cut-off
E00D 1 过放电压 BatOverDischgVolt RW 0.1 V %.1fV Unsigned 9 15.5 12.2 Alarming
of low battery voltage with load cut-off E00E 1 放电限制电压 BatDischgLimitVolt
RW 0.1 V %.1fV Unsigned 9 15.5 11.2During the battery over-discharge delay, the
battery voltage is lower than the judged point, and then the load is off at
once. E00F 1 放电截止SOC BatStopSOC RW 1 - %d% Unsigned 0 100 5 Discharge
cut-off SOC E010 1 过放延时时间 BatOverDischgDelayTime RW 1 S %dS Unsigned 0 120
60 E011 1 均衡充电时间 BatConstChgTime RW 1 Min %dmin Unsigned 0 900 120 E012 1
提升充电时间 BatImprovChgTime RW 1 Min %dmin Unsigned 10 900 120 E013 1
均衡充电间隔 BatConstChgGapTime RW 1 day %dDay Unsigned 0 255 30 E014 1
温度补偿系数 CoeffTemperCompen RW 1 mV/°C/2 V%d Signed 0 10 5 Invalid E015 1
充电上限温度 ChgMaxTemper RW 1 °C %d Signed -40 100 60 Invalid E016 1
充电下限温度 ChgMinTemper RW 1 °C %d Signed -40 100 -30 Invalid E017 1
放电上限温度 DisChgMaxTemper RW 1 °C %d Signed -40 100 60 Invalid E018 1
放电下限温度 DisChgMinTemper RW 1 °C %d Signed -40 100 -30 Invalid E019 1
加热启动温度 HeatBatStartTemper RW 1 °C %d Signed -40 100 0 Invalid E01A 1
加热停止温度 HeatBatStopTemper RW 1 °C %d Signed -40 100 5 Invalid E01B 1
市电切换电压 BatSwitchDcVolt RW 0.1 V %.1fV Unsigned 9 15.5 11.5The load is
switched to the AC power when the battery voltage falls below this judged point.
E01C 1 停止充电电流 StopChgCurrSet RW 0.1 A %.1fA Unsigned 0 10 2Only the
lithium battery is effective, and when the current of constant-voltage charging
state is lower than this value, the charging is stopped. E01D 1 停止充电容量
StopChgSocSet RW 1 % %d Unsigned 0 100 100When the SOC capacity is greater than
or equal to this value, charging is stopped, and it is valid for BMS
communication. E01E 1 SOC低告警 BatSocLowAlarm RW 1 % %d Unsigned 0 100 15With
the alarming of low SOC capacity, it is valid for BMS communication. E01F 1
切换市电SOC容量点 BatSocSwToLine RW 1 % %d Unsigned 0 100 10In SBU mode, the AC
power is applied when the SOC capacity is less than or equal to the value. E020
1 切换电池SOC容量点 BatSocSwToBatt RW 1 % %d Unsigned 1 100 100In SBU mode, the
inverter is applied when the SOC capacity is greater than or equal to the value.
E021 1 保留 BatParmReserved1 RW 1 - %d Unsigned E022 1 逆变切换电压
BattVoltSwToInv RW 0.1 V %.1fV Unsigned 9 15.5 14When the battery voltage is
higher than the judged point, the inverter is switched back. E023 1
均衡充电超时时间 BattEqualChgTimeout RW 1 min %dmin Unsigned 5 900 240
Increment+5 E024 1 锂电池激活电流 LiBattActiveCurrSet RW 0.1 A %.1fA Unsigned 0
20 8 E025 1 BMS充电限流模式设置 BMSChgLCMode RW 1 %d Unsigned 0 2 1 E026 1
1段开始充电时间 ChargeStartTime1 RW 1 h/m %d Unsigned 0 5947 0 Hours and
minutes: 23*256+59=5,947 E027 1 1段结束充电时间 ChargeEndTime1 RW 1 h/m %d
Unsigned 0 5947 0 Hours and minutes: 23*256+59=5,947 E028 1 2段开始充电时间
ChargeStartTime2 RW 1 h/m %d Unsigned 0 5947 0 Hours and minutes:
23*256+59=5,947 E029 1 2段结束充电时间 ChargeEndTime2 RW 1 h/m %d Unsigned 0
5947 0 Hours and minutes: 23*256+59=5,947 E02A 1 3段开始充电时间
ChargeStartTime3 RW 1 h/m %d Unsigned 0 5947 0 Hours and minutes:
23*256+59=5,947 E02B 1 3段结束充电时间 ChargeEndTime3 RW 1 h/m %d Unsigned 0
5947 0 Hours and minutes: 23*256+59=5,947 E02C 1 分段充电使能 OnTimeChargeEn RW
1 - %d Unsigned 0 1 0 0: disabled; 1: enabled E02D 1 1段开始放电时间
DischgStartTime1 RW 1 h/m %d Unsigned 0 5947 0 Hours and minutes:
23*256+59=5,947 E02E 1 1段结束放电时间 DischgEndTime1 RW 1 h/m %d Unsigned 0
5947 0 Hours and minutes: 23*256+59=5,947 E02F 1 2段开始放电时间
DischgStartTime2 RW 1 h/m %d Unsigned 0 5947 0 Hours and minutes:
23*256+59=5,947 E030 1 2段结束放电时间 DischgEndTime2 RW 1 h/m %d Unsigned 0
5947 0 Hours and minutes: 23*256+59=5,947 E031 1 3段开始放电时间
DischgStartTime3 RW 1 h/m %d Unsigned 0 5947 0 Hours and minutes:
23*256+59=5,947 E032 1 3段结束放电时间 DischgEndTime3 RW 1 h/m %d Unsigned 0
5947 0 Hours and minutes: 23*256+59=5,947 E033 1 分段放电使能 OnTimeDischgEn RW
1 - %d Unsigned 0 1 0 0: disabled; 1: enabled E034 3 保留 BatParmReserved2 RW
1 - %d Unsigned 0 - 0 E037 1 工作模式 InvToGridEn RW 1 - %d Unsigned 0 3 00:
off-grid mode (banned) 1: grid-connected mode 2: ACout anti-reverse flow 3: ACin
anti-reverse flow E038 1 漏电流检测使能 LeakageCurrDtcEn RW 1 - %d Unsigned 0 1
0 0: disabled; 1: enabled 11/18

---

## Page 12

深圳硕日新能源科技有限公司 MODBUS Protocol for Energy Stor AddressLength Name
English Name R/WMagnif icationUnitDisplay FormatSigned/Unsign edMinimu mMaximu
mDefault Remark E039 1 PV输出优先级设置 PvPowerPrioritySet RW 1 %d Unsigned 0 2
0 0: charging priority 1: load priority E03A 1 电池温度补偿使能 BattTemperCompEn
RW 1 - %d Unsigned 0 1 0 0: disabled 1: enabled E03B 1 充电时段1停止充电SOC
TimedChg1StopSOC RW 1 % %d Unsigned 0 100 100During charging period, the
charging is stopped when SOC is greater than the specified value. E03C 1
充电时段2停止充电SOC TimedChg2StopSOC RW 1 % %d Unsigned 0 100 100 E03D 1
充电时段3停止充电SOC TimedChg3StopSOC RW 1 % %d Unsigned 0 100 100 E03E 1
放电时段1停止放电SOC TimedDchg1StopSOC RW 1 % %d Unsigned 0 100 80During
discharging period, the discharging is stopped when SOC is less than the
specified value. E03F 1 放电时段2停止放电SOC TimedDchg2StopSOC RW 1 % %d
Unsigned 0 100 60 E040 1 放电时段3停止放电SOC TimedDchg3StopSOC RW 1 % %d
Unsigned 0 100 10 E041 1 充电时段1停止充电电压 TimedChg1StopVolt RW 0.1 W %.1fV
Unsigned 40.0V 59.5V 52.0V 1,200: 12,000 W E042 1 充电时段2停止充电电压
TimedChg2StopVolt RW 0.1 W %.1fV Unsigned 40.0V 59.5V 54.0V E043 1
充电时段3停止充电电压 TimedChg3StopVolt RW 0.1 W %.1fV Unsigned 40.0V 59.5V
57.6V E044 1 放电时段1停止放电电压 TimedDchg1StopVolt RW 0.1 W %.1fV Unsigned
40.0V 59.5V 50.0V E045 1 放电时段2停止放电电压 TimedDchg2StopVolt RW 0.1 W %.1fV
Unsigned 40.0V 59.5V 48.0V E046 1 放电时段3停止放电电压 TimedDchg3StopVolt RW
0.1 W %.1fV Unsigned 40.0V 59.5V 46.0V E047 1 定时放电时段1最大放电功率W
TimedDchg1MaxPower RW 10 W %d Unsigned 0 12000 6000 E048 1
定时放电时段2最大放电功率W TimedDchg2MaxPower RW 10 W %d Unsigned 0 12000 6000
E049 1 定时放电时段3最大放电功率W TimedDchg3MaxPower RW 10 W %d Unsigned 0 12000
6000 E04A 1 定时放电时段1最大充电功率W TimedChg1MaxPower RW 10 W %d Unsigned 0
12000 6000 E04B 1 定时放电时段2最大充电功率W TimedChg2MaxPower RW 10 W %d
Unsigned 0 12000 6000 E04C 1 定时放电时段3最大充电功率W TimedChg3MaxPower RW 10
W %d Unsigned 0 12000 6000 E04D 1 定时充电能量来源选择 TimedChgSource RW 1 %d
Unsigned 0 7 0Bit00: AC power during the charging period 1, 0: disabled, 1:
enabled Bit01: electric generator during the charging period 1, 0: disabled, 1:
enabled Bit02: AC power during the charging period 2, 0: disabled, 1: enabled
Bit03: electric generator during the charging period 2, 0: disabled, 1: enabled
Bit04: AC power during the charging period 3, 0: disabled, 1: enabled Bit05:
electric generator during the charging period 3, 0: disabled, 1: enabled P07
User Setting Area for Inverter Parameters E200 1 逆变器485地址设置 Rs485AddrSet
RW 1 - %d Unsigned 1 254 1 Integer (1 to 254) E201 1 并机模式 ParallMode RW 1 -
%d Unsigned 0 7 00: single machine 1: single-phase parallel 2: two-phase
parallel 3: two-phase parallel 120 4: two-phase parallel 180 5: three-phase A 6:
three-phase B 7: three-phase C E202 1 用户密码设置值 PassWordSet W 1 - %d
Unsigned 0 65535 0The password consists of four decimal digits. If the parameter
is 0, there is no password. Keyboard passwords can be changed by keyboard and
communication. E203 1 密码输入 PassWordInput W 1 - %d Unsigned 0 65535 0 E204 1
输出优先级 OutputPriority RW 1 - %d Unsigned 0 2 10: solar 1: line 2: sbu E205 1
市电充电电流限制 IbattLineChgLimit RW 0.1 A %.1fA Unsigned 0 200 60 Maximum
charging current limit for AC power charging E206 1 均衡充电使能
BattEqualChgEnable RW 1 V %d Unsigned 0 1 0 E207 1 NPE地线短接功能使能
N_G_FuncEn RW 1 %d Unsigned 0 1 0N and PE ground cable short circuit enabled
(only available on some models) E208 1 输出电压（默认220V） OutputVoltSet RW 0.1
V %.1fV Unsigned 100 264 120 E209 1 输出频率（默认50Hz） OutputFreqSet RW 0.01
Hz %.2fHz Unsigned 45 65 50 E20A 1 最大充电电流 MaxChgCurr RW 0.1 A %.1fA
Unsigned 0 200 80 E20B 1 AC输入范围 AcVoltRange RW 1 %d Unsigned 0 1 10: wide
band (APL) 1: narrow band (UPS) E20C 1 节能模式 PowerSavingMode RW 1 %d Unsigned
0 1 00: disabled 1: enabled E20D 1 过载自动重启 AutoRestartOvLoad RW 1 %d
Unsigned 0 1 10: disabled 1: enabled E20E 1 过温自动重启 AutoRestartOvTemper RW
1 %d Unsigned 0 1 10: disabled 1: enabled E20F 1 充电优先级 ChgSourcePriority RW
1 %d Unsigned 0 3 20: PV priority (AC power charging available when PV fails) 1:
AC power priority (PV charging available when AC power fails) 2: hybrid mode (AC
power and PV charging at the same time, with PV priority) 3: PV only E210 1
告警控制 AlarmEnable RW 1 %d Unsigned 0 1 10: disabled 1: enabled E211 1
输入源中断时告警使能 AlarmEnWhenSourceLoss RW 1 %d Unsigned 0 1 10: disabled 1:
enabled E212 1 过载旁路使能 BypEnableWhenOvLoad RW 1 %d Unsigned 0 1 10:
disabled 1: enabled E213 1 记录故障码 RecordFaultEnable RW 1 %d Unsigned 0 1 10:
disabled 1: enabled E214 1 BMS故障停机使能 BmsErrStopEnable RW 1 %d Unsigned 0 1
00: disabled 1: enabled E215 1 BMS使能 BmsCommEnable RW 1 %d Unsigned 0 2 00:
disabled 1: 485-BMS enabled 2: CAN-BMS enabled E216 1 直流负载控制 DcLoadSwitch
RW 1 %d Unsigned 0 1 0 0: off, 1: on E217 1 保留 InvParamSetReserved01 RW 1 %d
Unsigned 0 0 0 Reserved E218 1 机器降额功率 DeratePower RW 1 %.001fW Unsigned
1000 15000 0 Reduction of machine power rating E219 1 保留 InvParamSetReserved02
R 1 %d Unsigned 0 1 0 12/18

---

## Page 13

深圳硕日新能源科技有限公司 MODBUS Protocol for Energy Stor AddressLength Name
English Name R/WMagnif icationUnitDisplay FormatSigned/Unsign edMinimu mMaximu
mDefault Remark E21A 1 发电机启动充电禁止 GeneratorChgDisable R 1 %d Unsigned 0
1 0 Generator charging by default (can be disabled) E21B 1 BMS协议
Rs485BmsProtocol RW 1 %d Unsigned 0 30 7 E21C 1 旁路最大输入电流 MaxLineCurrent
RW 0.1 %.1fA Unsigned 0 100 40 Only for some custom models (ancient style ship
of RGSC) E21D 1 旁路最大输入功率 MaxLinePower RW 1 %d Unsigned 0 65535 50Peak
clipping power of grid 50: 500 W E21E 1 单机分相AC接线类型 OutputPhaseSet RW 1
%d Unsigned 0 2 0Only for single split-phase machine; 0: single-phase
connection, 1: three-phase connection, 2: split-phase connection E21F 1
柴油机工作模式 GenWorkMode RW 1 %d Unsigned 0 1 0 E220 1 柴油机充电电流
GenChgMaxCurr RW 0.1 A %.1fA Unsigned 0 100 40 E221 1 柴油机额定功率
GenRatePower RW 1 %d Unsigned 0 65535 6000 P08 Setting Area for Inverter
Grid-connection Parameters E400 1 并网有功功率设置 GridActivePowerSet RW 1 W %d
Unsigned 0 65000 0 E401 1 并网功率因数设置 GridPfSet RW 0.001 %.3f Signed -1 1
1Only suitable for models supporting grid-connection, with the adjustment range
of -80−100 and 80−100 E402 1 并网无功功率设置 GridQset RW 1 % %d Signed -100 100
0 Grid-connection reactive power setting E403 1 并网标准设置 GridStandard RW 1
%d Signed 0 100 100 Grid-connection standard setting E404 1 电网欠压保护点1
GridUVLevel1 RW 0.1 V %.1f Unsigned 0 270 184 E405 1 电网欠压保护点1延迟时间
GridUVTime1 RW 20 mS %d Unsigned 20 600000 120 E406 1 电网欠压保护恢复点1
GridUVResumLevel1 RW 0.1 V %.1f Unsigned 0 270 198 E407 1
电网欠压保护恢复点1延迟时间 GridUVResumTime1 RW 20 mS %d Unsigned 20 600000 120
E408 1 电网欠压保护点2 GridUVLevel2 RW 0.1 V %.1f Unsigned 0 270 184 E409 1
电网欠压保护点2延迟时间 GridUVTime2 RW 20 mS %d Unsigned 20 600000 120 E40A 1
电网欠压保护恢复点2 GridUVResumLevel2 RW 0.1 V %.1f Unsigned 0 270 198 E40B 1
电网欠压保护恢复点2延迟时间 GridUVResumTime2 RW 20 mS %d Unsigned 20 600000 120
E40C 1 电网过压保护点1 GridOVLevel1 RW 0.1 V %.1f Unsigned 0 270 280 E40D 1
电网过压保护点1延迟时间 GridOVTime1 RW 20 mS %d Unsigned 20 600000 120 E40E 1
电网过压保护恢复点1 GridOVResumLevel1 RW 0.1 V %.1f Unsigned 0 320 270 E40F 1
电网过压保护恢复点1延迟时间 GridOVResumTime1 RW 20 mS %d Unsigned 20 600000 120
E410 1 电网过压保护点2 GridOVLevel2 RW 0.1 V %.1f Unsigned 0 320 280 E411 1
电网过压保护点2延迟时间 GridOVTime2 RW 20 mS %d Unsigned 20 600000 120 E412 1
电网过压保护恢复点2 GridOVResumLevel2 RW 0.1 V %.1f Unsigned 0 320 270 E413 1
电网过压保护恢复点2延迟时间 GridOVResumTime2 RW 20 mS %d Unsigned 20 600000 120
E414 1 电网欠频保护点1 GridUFLevel1 RW 0.01 Hz %.2f Unsigned 0 65 47 E415 1
电网欠频保护点1延迟时间 GridUFTime1 RW 20 mS %d Unsigned 20 600000 120 E416 1
电网欠频保护恢复点1 GridUFResumLevel1 RW 0.01 Hz %.2f Unsigned 0 65 48 E417 1
电网欠频保护恢复点1延迟时间 GridUFResumTime1 RW 20 mS %d Unsigned 20 600000 120
E418 1 电网欠频保护点2 GridUFLevel2 RW 0.01 Hz %.2f Unsigned 0 65 47 E419 1
电网欠频保护点2延迟时间 GridUFTime2 RW 20 mS %d Unsigned 20 600000 120 E41A 1
电网欠频保护恢复点2 GridUFResumLevel2 RW 0.01 Hz %.2f Unsigned 0 65 48 E41B 1
电网欠频保护恢复点2延迟时间 GridUFResumTime2 RW 20 mS %d Unsigned 20 600000 120
E41C 1 电网过频保护点1 GridOFLevel1 RW 0.01 Hz %.2f Unsigned 0 65 52.5 E41D 1
电网过频保护点1延迟时间 GridOFTime1 RW 20 mS %d Unsigned 20 600000 120 E41E 1
电网过频保护恢复点1 GridOFResumLevel1 RW 0.01 Hz %.2f Unsigned 0 65 51 E41F 1
电网过频保护恢复点1延迟时间 GridOFResumTime1 RW 20 mS %d Unsigned 20 600000 120
E420 1 电网过频保护点2 GridOFLevel2 RW 0.01 Hz %.2f Unsigned 0 65 52.5 E421 1
电网过频保护点2延迟时间 GridOFTime2 RW 20 mS %d Unsigned 20 600000 120 E422 1
电网过频保护恢复点2 GridOFResumLevel2 RW 0.01 Hz %.2f Unsigned 0 65 51 E423 1
电网过频保护恢复点2延迟时间 GridOFResumTime2 RW 20 mS %d Unsigned 20 600000 120
E424 1 并网重启动时间，单位秒 ReConnectGridTime RW 1 S %d Unsigned 0 600 60 E425
1 绝缘阻抗检测使能 IsoCheckEn RW 1 %d Unsigned 0 1 1 E426 1 绝缘阻抗检测阈值
IsoProtectPoint RW 1 %d Unsigned 10 65535 15 E427 1 电网功能位使能
GridFuncEnable RW 1 %d Unsigned 0 65535 0 E428 1 用户模式 GridStandUserMode RW 1
%d Unsigned 0 1 0 E429 1 参数自检步骤 Cei021AutoTestStep RW 1 %d Unsigned 0
65535 0 E42A 1 电池参与并网使能 BattForGridPowerEn RW 1 %d Unsigned 0 3 00:
Battery is not discharged. 1: Battery discharges to UPS loads. 2: Battery
discharges to home loads. 3: Grid connection participates in electricity sales.
E42B 1 CT变比 ExCtRatio RW 1 %d Unsigned 0 5000 1000 E42C 1 防逆流误差功率
ZeroExportPower RW 1 W %d Unsigned 0 500 20When it is in the anti-reverse
current function, the input target power is set for the grid. E42D 1
并网重连功率上升速率 ReConnPowerRamp RW 1 S %d Unsigned 0 1000 60 Rising rate of
reconnection power E42E 1 有功-PF使能 WattPFCurveEnable RW 1 %d Unsigned 0 1 0
E42F 1 高低压穿越 HLVRTEnable RW 1 %d Unsigned 0 1 0 E430 1 参数自检启动命令
Cei021AutoTestStart RW 1 %d Unsigned 0 1 0 E431 1 AFCI使能 AfciEnable RW 1 %d
Unsigned 0 1 0 E432 1 正常连接延时时间 NormalConnDlyTsec RW 1 S %d Signed 0 1000
30 E433 1 正常连接功率上升速率 NormalConnPwrRampTsec RW 1 S %d Unsigned 0 1000
30 E434 1 并网连接最低电压 ConnVoltLow RW 0.1 V %.1f Unsigned 0 320 110 E435 1
并网连接最高电压 ConnVoltHigh RW 0.1 V %.1f Unsigned 0 320 140 E436 1
并网连接最低频率 ConnFreqLow RW 0.01 Hz %.2f Unsigned 40 70 60 E437 1
并网连接最高频率 ConnFreqHigh RW 0.01 Hz %.2f Unsigned 40 70 60 P09 Power
Statistics Historical Data F000 7 PV发电量最近7天历史数据 PVEnergyLast7day R 0.1
kWh %.1fkWh Unsigned The power data for each day occupies one register, so for
example, if today is September 27, the PV power generation data for the last 7
days is as follows: F000: power generation on September 26 (yesterday) F001:
power generation on September 25 (two days ago) F002: power generation on
September 24 ...... F007 7电池充电电量最近7天历史数据 BatChgEnergyLast7day R 1
AH %dAH Unsigned F00E 7电池放电电量最近7天历史数据 BatDisChgEnergyLast7day R 1
AH %dAH Unsigned F015 7市电充电电量最近7天历史数据 LineChgEnergyLast7day R 1 AH
%dAH Unsigned F01C 7负载消耗电量最近7天历史数据 LoadConsumLast7day R 0.1 kWh
%.1fkWh Unsigned F023 7负载从市电消耗电量最近7天历史数
据LoadConsumFromLineLast7day R 0.1 kWh %.1fkWh Unsigned F02A 2 最近一天日期记录
EnergyStatisticsDay R 0.1 kWh %.1fkWh Unsigned F02C 1 当天并网电量
GeneratEnergyToGridToday R 0.1 kWh %.1fkWh Unsigned F02D 1 电池当天充电安时数
BatChgAHToday R 1 AH %d Unsigned Total battery charging for the day (AH) F02E 1
电池当天放电安时数 BatDischgAHToday R 1 AH %d Unsigned Total battery discharging
for the day (AH) F02F 1 当天PV发电量 GeneratEnergyToday R 0.1 kWh %.1fkWh
Unsigned Total PV power generation of the day F030 1 负载当天用电量
UsedEnergyToday R 0.1 kWh %.1fkWh Unsigned Total load power consumption for the
day 13/18

---

## Page 14

深圳硕日新能源科技有限公司 MODBUS Protocol for Energy Stor AddressLength Name
English Name R/WMagnif icationUnitDisplay FormatSigned/Unsign edMinimu mMaximu
mDefault Remark F031 1 总运行天数 WorkDaysTotal R 1 d %d Unsigned F032 2
累计并网电量 GridEnergyTotal R 0.1 kWh %.1fkWh Unsigned Cumulative value of
power generated to the grid F034 2 蓄电池累计充电安时数 BatChgAHTotal R 1 AH %d
Unsigned F036 2 蓄电池累计放电安时数 BatDischgAHTotal R 1 AH %d Unsigned F038 2
PV累计发电量 GeneratEnergyTotal R 0.1 kWh %.1fkWh Unsigned F03A 2 负载累计用电量
UsedEnergyTotal R 0.1 kWh %.1fkWh Unsigned F03C 1 市电当天充电电量
LineChgEnergyTday R 1 AH %d Unsigned AC charging power (AH) for the day F03D 1
负载当天从市电消耗电量 LoadConsumLineTday R 0.1 kWh %.1fkWh Unsigned F03E 1
逆变当天工作时间 InvWorkTimeToday R 1 min %dmin Unsigned F03F 1 旁路当天工作时间
LineWorkTimeTodya R 1 min %dmin Unsigned F040 3 开机时间 PowerOnTime R 1 %d
Unsigned Refer to the time register for the current time format. F043 3
上次均衡充电完成时间 LastEquaChgTime R 1 %d Unsigned Refer to the time register
for the current time format. F046 2 市电累计充电量 LineChgEnergyTotal R 1 AH %d
Unsigned F048 2 负载累计从市电消耗电量 LoadConsumLineTotal R 0.1 kWh %.1fkWh
Unsigned Cumulative load power consumed from the battery side F04A 1
逆变累计工作时间 InvWorkTimeTotal R 1 h %dh Unsigned F04B 1 旁路累计工作时间
LineWorkTimeTotal R 1 h %dh Unsigned F04C 1 市电充电电量kwh LineChgKwHTday R 1
%d Unsigned F04D 1 保留 EnergyReserved3 R 1 %d Unsigned P10 Fault Record F800 16
故障记录0 FaultHistoryRecord00 RW 1 %d Unsigned Each fault record occupies 16
addresses, storing a total of 16 fault records. Internal data format definition
for fault record: (defined by internal offset address) 0x00: Fault code; see the
instruction manual for specific definition of fault code. If the fault code is
0, it means that the fault record is invalid. 0x01−0x03: The time when the fault
code occurs (there is no time for generation-1 machines). 0x04−0x0F: Data
packets captured when a fault occurs, with a total of 12 data.F810 16 故障记录1
FaultHistoryRecord01 RW 1 %d Unsigned F820 16 故障记录2 FaultHistoryRecord02 RW
1 %d Unsigned F830 16 故障记录3 FaultHistoryRecord03 RW 1 %d Unsigned F840 16
故障记录4 FaultHistoryRecord04 RW 1 %d Unsigned F850 16 故障记录5
FaultHistoryRecord05 RW 1 %d Unsigned F860 16 故障记录6 FaultHistoryRecord06 RW
1 %d Unsigned F870 16 故障记录7 FaultHistoryRecord07 RW 1 %d Unsigned F880 16
故障记录8 FaultHistoryRecord08 RW 1 %d Unsigned F890 16 故障记录9
FaultHistoryRecord09 RW 1 %d Unsigned F8A0 16 故障记录10 FaultHistoryRecord10 RW
1 %d Unsigned F8B0 16 故障记录11 FaultHistoryRecord11 RW 1 %d Unsigned F8C0 16
故障记录12 FaultHistoryRecord12 RW 1 %d Unsigned F8D0 16 故障记录13
FaultHistoryRecord13 RW 1 %d Unsigned F8E0 16 故障记录14 FaultHistoryRecord14 RW
1 %d Unsigned F8F0 16 故障记录15 FaultHistoryRecord15 RW 1 %d Unsigned F900 16
故障记录16 FaultHistoryRecord16 RW 1 %d Unsigned F910 16 故障记录17
FaultHistoryRecord17 RW 1 %d Unsigned F920 16 故障记录18 FaultHistoryRecord18 RW
1 %d Unsigned F930 16 故障记录19 FaultHistoryRecord19 RW 1 %d Unsigned F940 16
故障记录20 FaultHistoryRecord20 RW 1 %d Unsigned F950 16 故障记录21
FaultHistoryRecord21 RW 1 %d Unsigned F960 16 故障记录22 FaultHistoryRecord22 RW
1 %d Unsigned F970 16 故障记录23 FaultHistoryRecord23 RW 1 %d Unsigned F980 16
故障记录24 FaultHistoryRecord24 RW 1 %d Unsigned F990 16 故障记录25
FaultHistoryRecord25 RW 1 %d Unsigned F9A0 16 故障记录26 FaultHistoryRecord26 RW
1 %d Unsigned F9B0 16 故障记录27 FaultHistoryRecord27 RW 1 %d Unsigned F9C0 16
故障记录28 FaultHistoryRecord28 RW 1 %d Unsigned F9D0 16 故障记录29
FaultHistoryRecord29 RW 1 %d Unsigned F9E0 16 故障记录30 FaultHistoryRecord30 RW
1 %d Unsigned F9F0 16 故障记录31 FaultHistoryRecord31 RW 1 %d Unsigned FA00 16
意大利参数测试记录 AutoTestRecord RW 1 %d Unsigned FA10 1 保留 RecordReserved0 R
1 %d Unsigned FA11 1 保留 RecordReserved1 R 1 %d Unsigned END Note: The
0×0438−0×439 is the online upgrade command entry address. 14/18

---

## Page 15

MODBUS Register Area Start AddressEnd AddressLength Area 000AH 00FFH
00F6HProduct parameter information area 0100H 01FFH 0100HDevice live message
data area 0200H 02FFH 0100HDevice live message data area 0300H 6FFFH 6D00H
Reserve area 7000H 7FFFH 1000HDevice live message data area 8000H DFFFH 6000H
Reserve area DF00H DF1FH 0020H Device control area DF20H DFFFH 00E0H Debug data
area E000H E0FFH 0100HUser setting area for controller parameters E100H E1FFH
0100HFactory setting area for inverter parameters E200H E2FFH 0100HUser setting
area for inverter parameters E300H E3FFH 0100HFactory setting area for
controller parameters E800H E8FFH 0100HGrid-connected product parameter
information area E900H E97FH 0080HUser setting area for grid- connected inverter
parameters E980H EA7FH 00FFHFactory setting area for grid-connected inverter
parameters EA80H EAFFH 0080HFactory setting area for energy storage inverter
parameters F000H F7FFH 0800H Historical data F800H FFFFH 0800H Historical data
Data Area of Grid-connected/Off-grid/Energy Storage Inverter Grid-connected
inverter data area: 0x7000−0x70FF (256 W) Energy storage inverter data area:
0x7100−0x717F (128 W) Reserve area: 0x7180−0xDEFF (28,032 W) Device control
area: 0xDF00−0xDF1F (32 W)

---

## Page 16

Debug data area: 0xDF20−0xDFFF (224 W) Area occupied by other devices:
0xE000−0xE7FF (2,048 W) Product parameter information area: 0xE800−0xE8FF (256
W) User parameter setting area: 0xE900−0xE97F (128 W) Grid-connected inverter
parameter area: 0xE980−0xEA7F (256 W) Energy storage inverter parameter area:
0xEA80−0xEAFF (128 W) Reserve area: 0xEB00−0xEFFF (1,280 W) Area occupied by
other devices: 0xF000−0xE7FF (2,048 W) Historical record of
grid-connected/energy storage inverter: 0xF800−0xFFFF

---

## Page 17

MODBUS Register Area Device Type Domestic controller, all-in-one solar charger
inverter, off-grid inverter, street light controller Domestic controller,
all-in-one solar charger inverter, street light controller All-in-one solar
charger inverter, off-grid inverter Reserved (lithium battery&BMS)
Grid-connected/Energy storage inverter Grid-connected/Energy storage inverter
General General Domestic controller, all-in-one solar charger inverter, off-grid
inverter, street light controller All-in-one solar charger inverter, off-grid
inverter All-in-one solar charger inverter, off-grid inverter Domestic
controller, street light controller Grid-connected/Energy storage inverter
Grid-connected/Energy storage inverter Grid-connected inverter Energy storage
inverter Domestic controller Grid-connected/Off-grid/Energy storage inverter
Data Area of Grid-connected/Off-grid/Energy Storage Inverter Grid-connected
inverter data area: 0x7000−0x70FF (256 W) Energy storage inverter data area:
0x7100−0x717F (128 W) Reserve area: 0x7180−0xDEFF (28,032 W) Device control
area: 0xDF00−0xDF1F (32 W)

---

## Page 18

Debug data area: 0xDF20−0xDFFF (224 W) Area occupied by other devices:
0xE000−0xE7FF (2,048 W) Product parameter information area: 0xE800−0xE8FF (256
W) User parameter setting area: 0xE900−0xE97F (128 W) Grid-connected inverter
parameter area: 0xE980−0xEA7F (256 W) Energy storage inverter parameter area:
0xEA80−0xEAFF (128 W) Reserve area: 0xEB00−0xEFFF (1,280 W) Area occupied by
other devices: 0xF000−0xE7FF (2,048 W) Historical record of
grid-connected/energy storage inverter: 0xF800−0xFFFF

---
