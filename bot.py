import threading
import time

import PySimpleGUIWx as sg
import discord
import pythoncom
import wmi

NAME = 'TempBot'
TOKEN = 'NjM4NjE5OTEzMTY2MjU4MTg2.XbfXOw.QTRJT7hADaYt_QgEnZ7CQPDsAnA'
ICON = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAn1BMVEVHcEyVoqjR4+uywcgWGBnU3+drdHh8h4s9QkROVFfF1t3V4em6ytHN3eQMDQ40OTvK2+PX2+JhaWx5g4dxe39ma21+h4tWWFmGkJVtc3aCjZKVoqfmPTnpRUHlOTXafn7e8vvnfX3tamjrfX3mjI7mTUrmd3fimJvinaDkYF/jdXXrX13qcG+XZGPSaGfnqKx9YmKmZWTefn7omZvEZ2Z/KQCEAAAAHHRSTlMAn+SyBfFffyg40f6+4wEf3PlNeGugn6CfoH6f9oJbWAAAAGtJREFUGNNjYAADFhE2PgZkIKWgwIYiwGisz44qoKSMKiBuII8qII2uQtLQCFVAzEQRVUBCD01AVBfVUE5WbR1eDiQBLjVZWRVmBJ+FW0ZGRpUJSYWAppycFg+SgJCgugYrJ7KpHOzC/BAWAF9YBtSJcOPLAAAAAElFTkSuQmCC'
ICON_URL = 'https://cdn.discordapp.com/avatars/638619913166258186/c267c2a4334d13f6f4e05409064adc75.webp'
bot: discord.Client
tray: sg.SystemTray


class HardwareInfo:
    def __init__(self):
        w = wmi.WMI(namespace=r'root\OpenHardwareMonitor')
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
                    self.cpu_temps[cpu_num] = f'{sensor.Value} °C'
                elif name == 'GPU Core':
                    self.gpu_temp = f'{sensor.Value} °C'
                elif name == 'CPU Package':
                    self.cpu_package_temp = f'{sensor.Value} °C'
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
                    self.ram_used = f'{round(sensor.Value, 1)} GB'
                elif name == 'Available Memory':
                    self.ram_available = f'{round(sensor.Value, 1)} GB'

        self.cpu_cores = len(self.cpu_temps)

        for device in device_info:
            if device.HardwareType == 'CPU':
                self.cpu_name = device.Name
            elif device.HardwareType == 'RAM':
                self.ram_name = device.Name
            elif device.HardwareType == 'Mainboard':
                self.mother_board_name = device.Name
            elif device.HardwareType.upper().startswith('GPU'):
                self.gpu_name = device.Name


class TempBot(discord.Client):
    started = False

    async def startup(self):
        self.started = True

    async def on_ready(self):
        print('Logged in as', self.user)
        if not self.started:
            await self.startup()

    async def on_message(self, message: discord.Message):
        msg = message.content.lower()

        if msg == '!temp':

            pythoncom.CoInitialize()  # Prevents crash that occurs bc not on main thread
            hardware = HardwareInfo()

            if hardware.failed_to_load:
                pass  # TODO: Display Error
                return

            embed = discord.Embed(color=0xff0000)
            embed.set_author(name=NAME, icon_url=ICON_URL)
            embed.add_field(name='CPU Info', value=hardware.cpu_name, inline=False)
            embed.add_field(name='CPU Package Temp', value=hardware.cpu_package_temp, inline=True)
            embed.add_field(name='CPU Total Usage', value=hardware.cpu_total_usage, inline=True)
            for i in range(1, hardware.cpu_cores + 1):
                embed.add_field(name=f'CPU Core # {i} Temp', value=hardware.cpu_temps[i], inline=True)
            for i in range(1, hardware.cpu_cores + 1):
                embed.add_field(name=f'CPU Core # {i} Usage', value=hardware.cpu_usage[i], inline=True)
            embed.add_field(name='RAM Info', value=hardware.ram_name, inline=False)
            embed.add_field(name='RAM Used', value=hardware.ram_percent_used, inline=True)
            embed.add_field(name='RAM Available', value=hardware.ram_available, inline=True)
            embed.add_field(name='RAM Remaining', value=hardware.ram_used, inline=True)
            embed.add_field(name='GPU Info', value=hardware.gpu_name, inline=False)
            embed.add_field(name='GPU Core', value=hardware.gpu_temp, inline=True)
            embed.add_field(name='GPU Memory Used', value=hardware.gpu_memory_percent_used, inline=True)
            await message.channel.send(embed=embed)


def main():
    global bot, tray

    def discord_thread():
        bot.run(TOKEN)

    bot = TempBot()
    threading.Thread(target=discord_thread, name='DiscordThread').start()

    tray_menu = ['menu', [
        'Exit'
    ]]

    tray = sg.SystemTray(
        menu=tray_menu,
        data_base64=ICON,
        tooltip=NAME
    )

    while not bot.started:  # Wait for bot to login
        time.sleep(0.25)

    while True:  # Handle Tray events
        event = tray.Read()
        if event == '__TIMEOUT__':
            continue
        elif event == 'Exit':
            tray.Hide()
            bot.started = False
            bot.loop.create_task(bot.close())
            break


if __name__ == '__main__':
    main()
