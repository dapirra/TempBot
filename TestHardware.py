import sys
import wmi

"""
This file is used to test if hardware information can be properly read in from Open Hardware Monitor.
"""

hardware_read_failure = False
sensor_read_failure = False
horizonal_line = '-' * 72

print('Test Initiated.')

try:
    w = wmi.WMI(namespace=r'root\OpenHardwareMonitor')
except:
    print('Error: creating WMI object.')
    sys.exit(1)

try:
    hardware_info = w.Hardware()
except:
    print('Error: reading Hardware info.')
    sys.exit(1)

try:
    sensor_info = w.Sensor()
except:
    print('Error: reading Sensor info.')
    sys.exit(1)

if not hardware_info:
    hardware_read_failure = True
    print('Error: Hardware request is null.')

if not sensor_info:
    sensor_read_failure = True
    print('Error: Sensor request is null.')

if not hardware_read_failure:
    list.sort(hardware_info)

    print(horizonal_line)
    print('Printing all Hardware Information:')

    for device in hardware_info:
        print('{:<20}{:<30}'.format(device.HardwareType, device.Name))

if not sensor_read_failure:
    list.sort(sensor_info)

    print(horizonal_line)
    print('Printing all Sensor Information:')
    print('{:<20}{:<20}{:<20}'.format('Name', 'Sensor Type', 'Value'))
    for sensor in sensor_info:
        print('{:<20}{:<20}{:<20}'.format(sensor.Name, sensor.SensorType, sensor.Value))

    print(horizonal_line)

if hardware_read_failure and sensor_read_failure:
    print('Open Hardware Monitor is probably not running')

# Powershell command: Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace 'root/wmi"

# Print temperature with powershell
# w = wmi.WMI(namespace=r'root\wmi')
# temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
# temp = temperature_info.CurrentTemperature
# print(temp)
# print(temp / 10 - 273.15)

print('Test Complete.')
