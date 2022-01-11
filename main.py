#!/usr/bin/env python3

# (C) 2021 Jorge
#
# MQTT-client
# MODBUS-client
#
# 1) push modbus sensor data to MQTT topic
# 2) from MQTT send config commands to modbus
# 3) support home assistant auto discovery / registration
# 4) modbus is serial so must be queue for read or write

import sys
import asyncio
import json
import os
import time
from pprint import pprint
import binascii
import re
import subprocess

#sys.path.insert(1,'/home/pi/nilan/pycts602')

from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager

import paho.mqtt.client as mqtt
import minimalmodbus
from cts602_registers import *

# Defines for MQTT broker
MQTT_CLIENT = os.getenv("MQTT_CLIENT", "pi")
MQTT_SERVER = os.getenv("MQTT_SERVER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USER", "mqtt")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "no-security")


# Defines for MODBUS
MB_PORT = os.getenv("MODBUS_PORT", "/dev/ttyUSB0")
MB_ADDRESS = int(os.getenv("MODBUS_NILAN_SLAVE_ADDRESS", 30))
MB_DEBUG = os.getenv("MODBUS_DEBUG", False)
MB_BAUD = int(os.getenv("MODBUS_SPEED", 19200))
MB_STOPBITS = int(os.getenv("MODBUS_STOPBITS",1))
MB_BYTESIZE = int(os.getenv("MODBUS_BYTESIZE",8))
MB_DEBUG = os.getenv("MODBUS_DEBUG",False)
# MB_EVEN

# Modbus query parameters
MB_SLEEP = int(os.getenv("MODBUS_QUERY_ROUND_SLEEP", 5)) # def 5s
MB_CACHE_REFRESH = int(os.getenv("MODBUS_CACHE_REFRESH", 3600)) # def 1h

# Modbus filters
MB_FILTER = os.getenv("MODBUS_FILTER_NAME", 'Nilan_Time')

# CACHE
CACHE = {}

def getcpuserial():
  # Extract serial from cpuinfo file
  cpuserial = "0000000000000000"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:6]=='Serial':
        cpuserial = line[10:26]
    f.close()
  except:
    cpuserial = "ERROR000000000"

  return cpuserial

def getUSBserial():
  device_re = re.compile(b"Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
  df = subprocess.check_output("lsusb")
  devices = []
  for i in df.split(b'\n'):
    if i:
      info = device_re.match(i)
      if info:
        dinfo = info.groupdict()
        dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
        devices.append(dinfo)
            
  print(devices)

def ha_uniqueid():
    uid = 'nilan2homeassistant' + MB_PORT + ' ' + str(MB_ADDRESS) + ' ' + getcpuserial()
    return binascii.crc32(uid.encode('utf8'))

HA_UNIQUEID = os.getenv("HA_UID", ha_uniqueid())

def cachedirty(index,value):
    if index not in CACHE or index in CACHE and CACHE[index] != value:
        CACHE[index] = value
        print("\tUpdating cache: " + index + "=" + str(value))
        return True
    else:
        return False

def lcdascii(byte):
    if byte in lcdasciitable.keys():
        return lcdasciitable[byte]
    else:
        return chr(byte)

def fetchMulti(nilan, start, amount):
    try:
        nilan.debug = True
        #returnarray = nilan._performCommand(3, '\x00\xC8\x00\x12')
        returnarray = nilan.read_registers(200, 23, 4)
        pprint(returnarray)
    except IOError:
        print("Failed to multi-read from instruments.")
        return None
    
    nilan.debug = MB_DEBUG


def fetch(nilan, reg):
    fc=4 if reg['type'] == 'Input' else 3
    nod=reg['scale'].count('0')
    sign=True
    if reg['name'] == 'Nilan_Control_SeclnState':
        sign=False
    #print("  Number of decimals: ", nod, " - FunctionCode = ", fc)
    try:
        rawvalue=nilan.read_register(reg['address'],number_of_decimals=nod, functioncode=fc, signed=sign)
    except IOError:
        print("Failed to read from instrument.")
        return None

    # to suppress data vs usability I think I am fined with 1 digit resolution
    if nod > 0:
        rawvalue = round(rawvalue,1)
    
    if reg['unit'] == 'text' or reg['unit'] == 'ascii':
        # LSB and MSB to ascii characters
        asc1 = lcdascii(rawvalue % 256)
        asc2 = lcdascii(int(rawvalue / 256) % 256)
        
        return asc1+asc2
    else:
        return rawvalue

def getAll(nilan):

    for x in registers:
        #print(x['address'], " ", x['name'], " \t= ", fetch(nilan, x), x['unit'])
        nilanvalue = fetch(nilan,x)
        
        if nilanvalue == None:
            # Probably exception - returned none so do not cache this
            pass
        
        if cachedirty(x['name'],nilanvalue): # send to MQTT
            #print("Sending..")
            pass
        else:
            #print("Omitting same value")
            pass

def getAllGrouped(nilan):

    for g in groups:
        print("group: " + g['name'])

        fetchMulti(nilan,200,18)
        sys.exit(0)



# Main program

if __name__ == "__main__":
    if MQTT_SERVER is None:
        exit('ERROR: Please configure mandatory environment variable SERVER')

    print("Starting Nilan to HA MQTT bus with HA unique id", HA_UNIQUEID)
    #getUSBserial()

    try: 
        nilan = minimalmodbus.Instrument(MB_PORT, MB_ADDRESS, mode='rtu')
        nilan.serial.baudrate = MB_BAUD
        nilan.serial.bytesize = MB_BYTESIZE
        nilan.serial.stopbits = MB_STOPBITS
        nilan.serial.parity = minimalmodbus.serial.PARITY_EVEN
        #nilan.minimalmodbus.MODE_RTU
        nilan.debug = MB_DEBUG


        for i in range(15):
            print("Round: " + str(i))
            getAllGrouped(nilan)
            time.sleep(MB_SLEEP)
        #pprint.pprint(data)

        
    except IOError:
        print("Failed to do serial modbus")
       
    #pprint.pprint(CACHE) 
    #print json.dumps(data, indent=1)    
    #pprint.pprint(data)
        
    # print out humidity (%)
    #print data['humidity']['value']    
    #print(data)

    #print(list(serial.tools.list_ports.comports()))
    #exit(0)

    #m = Manager()
    #rq = m.Queue()
    #wq = m.Queue()

    #executor = ProcessPoolExecutor()
    #executor.submit(run_get_datas_background, q)

    #loop = asyncio.get_event_loop()
    
    #loop.set_debug(True)
    #loop.run_until_complete(handle_queue(q))


exit

#try:
#    print(instrument.read_register(4143))
#except IOError:
#    print("Failed to read from instrument")



#INTERVAL = int(os.getenv("SCAN_INTERVAL", 30))



#modbus:
#  type: serial
#  method: rtu
#  port: /dev/ttyUSB0
#  baudrate: 19200
#  stopbits: 1
#  bytesize: 8
#  parity: E


"""
/*

./main.py
0   Nilan_Bus_Version   =  11
1   Nilan_App_VersionMajor      =  2. text
2   Nilan_App_VersionMinor      =  37 text
3   Nilan_App_VersionRelease    =  .c text
100   Nilan_Input_UserFunc      =  0
101   Nilan_Input_AirFilter     =  0
102   Nilan_Input_DoorOpen      =  0
103   Nilan_Input_Smoke         =  0
104   Nilan_Input_MotorThermo   =  0
105   Nilan_Input_Frost_Overht          =  0
106   Nilan_Input_AirFlow       =  0
107   Nilan_Input_P_HI          =  0
108   Nilan_Input_P_LO          =  0
109   Nilan_Input_Boil          =  0
110   Nilan_Input_3WayPos       =  0
111   Nilan_Input_DefrostHG     =  0
112   Nilan_Input_Defrost       =  0
113   Nilan_Input_UserFunc_2    =  0
200   Nilan_Input_T0_Controller         =  18.24 °C
201   Nilan_Input_T1_Intake     =  -11.94 °C
202   Nilan_Input_T2_Inlet      =  0.0 °C
203   Nilan_Input_T3_Exhaust    =  0.0 °C
204   Nilan_Input_T4_Outlet     =  0.0 °C
205   Nilan_Input_T5_Cond       =  19.07 °C
206   Nilan_Input_T6_Evap       =  -1.58 °C
207   Nilan_Input_T7_Inlet      =  17.64 °C
208   Nilan_Input_T8_Outdoor    =  -11.94 °C
209   Nilan_Input_T9_Heater     =  0.0 °C
210   Nilan_Input_T10_Extem     =  19.97 °C
211   Nilan_Input_T11_Top       =  52.32 °C
212   Nilan_Input_T12_Bottom    =  44.4 °C
213   Nilan_Input_T13_Retum     =  0.0 °C
214   Nilan_Input_T14_Supply    =  -40.0 °C
215   Nilan_Input_T15_Room      =  20.05 °C
216   Nilan_Input_T16   =  -20.55 °C
221   Nilan_Input_RH    =  23.71 %
222   Nilan_Input_CO2   =  0 ppm
400   Nilan_Alarm_Status        =  0
401   Nilan_Alarm_List_1_ID     =  0
402   Nilan_Alarm_List_1_Date   =  0
403   Nilan_Alarm_List_1_Time   =  0
404   Nilan_Alarm_List_2_ID     =  0
405   Nilan_Alarm_List_2_Date   =  0
406   Nilan_Alarm_List_2_Time   =  0
407   Nilan_Alarm_List_3_ID     =  0
408   Nilan_Alarm_List_3_Date   =  0
409   Nilan_Alarm_List_3_Time   =  0
1000   Nilan_Control_RunAct     =  1
1001   Nilan_Control_ModeAct    =  1
1002   Nilan_Control_State      =  7
1003   Nilan_Control_SeclnState         =  23194 Sec
1200   Nilan_AirTemp_IsSummer   =  0
1201   Nilan_AirTemp_Tempinlet          =  27.0 °C
1202   Nilan_AirTemp_TempCont   =  19.97 °C
1203   Nilan_AirTemp_TempRoom   =  19.97 °C
1204   Nilan_AirTemp_EffPct     =  92.69 %
1205   Nilan_AirTemp_CapSet     =  100.0 %
1206   Nilan_AirTemp_CapAct     =  100.0 %
2000   Nilan_Display_LED_1      =  1
2001   Nilan_Display_LED_2      =  0
2002   Nilan_Display_Text_1_2   =  LÄ ascii
2003   Nilan_Display_Text_3_4   =  MP ascii
2004   Nilan_Display_Text_5_6   =  Ö  ascii
2005   Nilan_Display_Text_7_8   =     ascii
2006   Nilan_Display_Attr_1_8   =  0
2007   Nilan_Display_Text_9_10          =  >2 ascii
2008   Nilan_Display_Text_11_12         =  <  ascii
2009   Nilan_Display_Text_13_14         =  28 ascii
2010   Nilan_Display_Text_15_16         =  °C ascii
2011   Nilan_Display_Attr_9_16          =  0
0   Nilan_Bus_Address   =  30
100   Nilan_Output_AirFlap      =  1
101   Nilan_Output_SmokeFlap    =  1
102   Nilan_Output_BypassOpen   =  0
103   Nilan_Output_BypassClose          =  0
104   Nilan_Output_AirCircPump          =  0
105   Nilan_Output_AirHeatAllo          =  1
106   Nilan_Output_AirHeat_1    =  0
107   Nilan_Output_AirHeat_2    =  0
108   Nilan_Output_AirHeat_3    =  0
109   Nilan_Output_Compressor   =  1
110   Nilan_Output_Compressor2          =  0
111   Nilan_Output_4WayCool     =  0
112   Nilan_Output_HotgasHeat   =  0
113   Nilan_Output_HotgasCool   =  0
114   Nilan_Output_CondOpen     =  1
115   Nilan_Output_CondClose    =  0
116   Nilan_Output_WaterHeat    =  0
117   Nilan_Output_3WayValve    =  0
118   Nilan_Output_CenCircPump          =  0
119   Nilan_Output_CenHeat_1    =  0
120   Nilan_Output_CenHeat_2    =  0
121   Nilan_Output_CenHeat_3    =  0
122   Nilan_Output_CenHeatExt   =  1
123   Nilan_Output_UserFunc     =  0
124   Nilan_Output_UserFunc_2   =  0
125   Nilan_Output_Defrosting   =  0
200   Nilan_Output_ExhaustSpeed         =  55.0 %
201   Nilan_Output_InletSpeed   =  31.0 %
202   Nilan_Output_AirHeatCap   =  0.0 %
203   Nilan_Output_CenHeatCap   =  0.0 %
204   Nilan_Output_CprCap       =  0.0 %
205   Nilan_Output_EarthSpeed   =  0.0 %
300   Nilan_Time_Second         =  20 ss
301   Nilan_Time_Minute         =  19 nn
302   Nilan_Time_Hour   =  21 hh
303   Nilan_Time_Day    =  9 dd
304   Nilan_Time_Month          =  2 mm
305   Nilan_Time_Year   =  2021 yyyy
400   Nilan_Alarm_Reset         =  0
500   Nilan_Program_Select      =  0
600   Nilan_Program_UserFuncAct         =  0
601   Nilan_Program_UserFuncSet         =  1
602   Nilan_Program_UserTimeSet         =  0
603   Nilan_Program_UserVentSet         =  4
604   Nilan_Program_UserTempSet         =  23 °C
605   Nilan_Program_UserOffsSet         =  0 °C
610   Nilan_Program_User2FuncAct        =  0
611   Nilan_Program_User2FuncSet        =  0
612   Nilan_Program_User2TimeSet        =  0
613   Nilan_Program_User2VentSet        =  4
614   Nilan_Program_User2TempSet        =  23 °C
615   Nilan_Program_User2OffsSet        =  0 °C
1000   Nilan_Control_Type       =  19
1001   Nilan_Control_RunSet     =  1
1002   Nilan_Control_ModeSet    =  1
1003   Nilan_Control_VentSet    =  2 Step
1004   Nilan_Control_TempSet    =  28.0 °C
1005   Nilan_Control_ServiceMode        =  0
1006   Nilan_Control_ServicePct         =  50.0 %
1007   Nilan_Control_Preset     =  0
1100   Nilan_AirFlow_AirExchMode        =  0
1101   Nilan_AirFlow_CoolVent   =  0 Step
1200   Nilan_AirTemp_CoolSet    =  4 °C
1201   Nilan_AirTemp_TempMinSum         =  10.0 °C
1202   Nilan_AirTemp_TempMinWin         =  15.0 °C
1203   Nilan_AirTemp_TempMax    =  21.0 °C
1204   Nilan_AirTemp_TempMaxWin         =  28.0 °C
1205   Nilan_AirTemp_TempSummer         =  12.0 °C
1700   Nilan_HotWater_TempSet_T11       =  40.0 °C
1701   Nilan_HotWater_TempSet_T12       =  45.0 °C
1800   Nilan_CentralHeat_HeatExtern     =  -1.0 °C
1910   Nilan_AirQual_RH_VentLo          =  0 Step
1911   Nilan_AirQual_RH_VentHi          =  3 Step
1912   Nilan_AirQual_RH_LimLo   =  30.0 %
1913   Nilan_AirQual_RH_TimeOut         =  60 min
1920   Nilan_AirQual_CO2_VentHi         =  3 Step
1921   Nilan_AirQual_CO2_LimLo          =  600 ppm
1922   Nilan_AirQual_0O2_LimHi          =  800 ppm
2000   Nilan_Display_KeyCode    =  0
*/
"""


