import wmi


class HardwareInfo:
    def __init__(self):
        w = wmi.WMI(namespace=r'root\OpenHardwareMonitor')
        cimv2 = wmi.WMI(namespace=r'root\CIMV2')
        sensor_info = w.Sensor()
        device_info = w.Hardware()

        if not sensor_info:
            self.failed_to_load = True
            return

        self.failed_to_load = False
        self.cpu_temps = {}
        self.cpu_usage = {}

        for sensor in sensor_info:
            name: str = sensor.Name
            if sensor.SensorType == 'Temperature':
                if name.startswith('CPU Core'):
                    cpu_num = int(name[-1])
                    self.cpu_temps[cpu_num] = f'{round(sensor.Value)}°C'
                elif name == 'GPU Core':
                    self.gpu_temp = f'{round(sensor.Value)}°C'
                elif name == 'CPU Package':
                    self.cpu_package_temp = f'{round(sensor.Value)}°C'
            elif sensor.SensorType == 'Load':
                if name.startswith('CPU Core'):
                    cpu_num = int(name[-1])
                    self.cpu_usage[cpu_num] = f'{round(sensor.Value, 2)}%'
                elif name == 'CPU Total':
                    self.cpu_total_usage = f'{round(sensor.Value, 2)}%'
                elif name == 'Memory':
                    self.ram_percent_used = f'{round(sensor.Value, 1)}%'
                elif name == 'GPU Memory':
                    self.gpu_memory_percent_used = f'{round(sensor.Value, 1)}%'
            elif sensor.SensorType == 'Data':
                if name == 'Used Memory':
                    self._ram_used = sensor.Value
                elif name == 'Available Memory':
                    self._ram_available = sensor.Value

        self.ram_used = f'{round(self._ram_used, 1)}'
        self.ram_available = f'{round(self._ram_available, 1)}'
        self.ram_total = f'{round(self._ram_used + self._ram_available)}'
        self.cpu_temps_len = len(self.cpu_temps)
        self.cpu_usage_len = len(self.cpu_usage)
        self.cpu_cores = self.cpu_usage_len
        self.os_has_temp = self.cpu_temps_len == self.cpu_usage_len

        for device in device_info:
            if device.HardwareType == 'CPU':
                self.cpu_name = device.Name
            elif device.HardwareType == 'RAM':
                self.ram_name = device.Name
            elif device.HardwareType == 'Mainboard':
                self.mother_board_name = device.Name
            elif device.HardwareType.upper().startswith('GPU'):
                self.gpu_name = device.Name

        self._disk_read = int(cimv2.query(
            'SELECT DiskReadBytesPersec FROM Win32_PerfFormattedData_PerfDisk_PhysicalDisk WHERE NAME LIKE "%Total%"')[0]
            .DiskReadBytesPersec)

        self._disk_write = int(cimv2.query(
            'SELECT DiskWriteBytesPersec FROM Win32_PerfFormattedData_PerfDisk_PhysicalDisk WHERE NAME LIKE "%Total%"')[0]
            .DiskWriteBytesPersec)

        self.disk_read = self.human_file_size(self._disk_read)
        self.disk_write = self.human_file_size(self._disk_write)
        self.attributes = '\n'.join(filter(lambda x: not x.startswith('_'), dir(self)))

    @staticmethod
    def human_file_size(num_bytes: int):
        if num_bytes < 1024:
            return f'{num_bytes} bytes'
        elif num_bytes < 1048576:  # 1024*1024
            return f'{round(num_bytes / 1024, 2)} KB'
        else:
            return f'{round(num_bytes / 1048576, 2)} MB'


if __name__ == '__main__':
    """Used for testing"""
    hw = HardwareInfo()
    print('Breakpoint placeholder')
