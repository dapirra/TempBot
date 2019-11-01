import asyncio
import threading
from datetime import datetime, timedelta

import PySimpleGUIWx as sg
import discord
import pythoncom
import win32gui
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

    async def on_ready(self):
        print('Logged in as', self.user)

    async def on_message(self, message: discord.Message):
        msg = message.content.lower()

        if msg == '!temp':
            temp_msg: discord.Message = None
            finish_at = datetime.now() + timedelta(minutes=5)
            while datetime.now() < finish_at:
                pythoncom.CoInitialize()  # Prevents crash that occurs bc not on main thread
                hw = HardwareInfo()

                if hw.failed_to_load:
                    embed = discord.Embed(title='Error:', color=0xff0000,
                                          description='Open Hardware Monitor is not running.')
                    embed.set_author(name=NAME, icon_url=ICON_URL)
                    if temp_msg:
                        await temp_msg.edit(embed=embed)
                    else:
                        temp_msg = await message.channel.send(embed=embed)
                    await asyncio.sleep(5)
                    continue

                embed = discord.Embed(color=0xff0000)
                embed.set_author(name=NAME, icon_url=ICON_URL)
                embed.add_field(name='CPU Info:', inline=False,
                                value=f'{hw.cpu_name}: **{hw.cpu_package_temp}** | **{hw.cpu_total_usage}**\n\u200b')
                for i in range(1, hw.cpu_cores + 1):
                    embed.add_field(name=f'CPU Core #{i}', value=f'{hw.cpu_temps[i]} | {hw.cpu_usage[i]}', inline=True)
                    if i % 2 == 0:
                        embed.add_field(name='\u200b', value='\u200b', inline=True)  # Blank field
                embed.add_field(name='\u200b\nGPU Info:', value=f'{hw.gpu_name}: **{hw.gpu_temp}**', inline=False)
                embed.add_field(name='\u200b\nRAM Info:', inline=False,
                                value=f'{hw.ram_name}: {hw.ram_percent_used} | {hw.ram_used}/{hw.ram_total} GB')

                if temp_msg:
                    await temp_msg.edit(embed=embed)
                else:
                    temp_msg = await message.channel.send(embed=embed)
                await asyncio.sleep(5)


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

    if HardwareInfo().failed_to_load:
        win32gui.MessageBox(None, 'Open Hardware Monitor must be running for !temp to work.', 'Warning', 48)

    while True:  # Handle Tray events
        event = tray.Read()
        if event == 'Exit':
            tray.Hide()
            bot.loop.create_task(bot.close())
            break


if __name__ == '__main__':
    main()
