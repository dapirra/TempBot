import wmi
import win32gui

w = wmi.WMI(namespace=r'root\OpenHardwareMonitor')
temperature_infos = w.Sensor()
hardware = w.Hardware()

for device in hardware:
    print(device.Name)

print('-' * 25)
list.sort(temperature_infos)
for sensor in temperature_infos:
    # print(sensor.SensorType, sensor.Name, sensor.Value, sep=': ')
    if sensor.SensorType == 'Temperature':
        print(sensor.Name)
        print(sensor.Value)

print('-' * 25)

# Powershell command: Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace "root/wmi"

# Print temperature with powershell
# w = wmi.WMI(namespace=r'root\wmi')
# temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
# temp = temperature_info.CurrentTemperature
# print(temp)
# print(temp / 10 - 273.15)

print(win32gui.MessageBox(None, 'Hello', 'Yo', 16))
