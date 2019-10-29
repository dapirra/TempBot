import threading
import time

import PySimpleGUIWx as sg
import discord
import wmi

NAME = 'TempBot'
TOKEN = 'NjM4NjE5OTEzMTY2MjU4MTg2.XbfXOw.QTRJT7hADaYt_QgEnZ7CQPDsAnA'
ICON = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAn1BMVEVHcEyVoqjR4+uywcgWGBnU3+drdHh8h4s9QkROVFfF1t3V4em6ytHN3eQMDQ40OTvK2+PX2+JhaWx5g4dxe39ma21+h4tWWFmGkJVtc3aCjZKVoqfmPTnpRUHlOTXafn7e8vvnfX3tamjrfX3mjI7mTUrmd3fimJvinaDkYF/jdXXrX13qcG+XZGPSaGfnqKx9YmKmZWTefn7omZvEZ2Z/KQCEAAAAHHRSTlMAn+SyBfFffyg40f6+4wEf3PlNeGugn6CfoH6f9oJbWAAAAGtJREFUGNNjYAADFhE2PgZkIKWgwIYiwGisz44qoKSMKiBuII8qII2uQtLQCFVAzEQRVUBCD01AVBfVUE5WbR1eDiQBLjVZWRVmBJ+FW0ZGRpUJSYWAppycFg+SgJCgugYrJ7KpHOzC/BAWAF9YBtSJcOPLAAAAAElFTkSuQmCC'
ICON_URL = 'http://icons.iconarchive.com/icons/google/noto-emoji-travel-places/128/42650-thermometer-icon.png'
bot: discord.Client
tray: sg.SystemTray


class HardwareInfo:
    def __init__(self):
        w = wmi.WMI(namespace=r'root\OpenHardwareMonitor')
        sensor_info = w.Sensor()

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
                    self.cpu_temps[cpu_num] = sensor.Value
                elif name == 'GPU Core':
                    self.gpu_temp = sensor.Value
                elif name == 'CPU Package':
                    self.cpu_package_temp = sensor.Value
            elif sensor.SensorType == 'Load':
                if name.startswith('CPU Core'):
                    cpu_num = int(name[-1])
                    self.cpu_usage[cpu_num] = sensor.Value
                elif name == 'CPU Total':
                    self.cpu_total = sensor.Value
                elif name == 'Memory':
                    self.memory_percent = sensor.Value
                elif name == 'GPU Memory':
                    self.gpu_memory_percent = sensor.Value
            elif sensor.SensorType == 'Data':
                if name == 'Used Memory':
                    self.memory_used = sensor.Value
                elif name == 'Available Memory':
                    self.memory_available = sensor.Value


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
            embed = discord.Embed(color=0xff0000)
            embed.set_author(name=NAME, icon_url=ICON_URL)
            embed.add_field(name='GPU Core', value='30°C', inline=False)
            embed.add_field(name='CPU Core # 1', value='37°C', inline=True)
            embed.add_field(name='CPU Core # 2', value='38°C', inline=True)
            embed.add_field(name='CPU Core # 3', value='37°C', inline=True)
            embed.add_field(name='CPU Core # 4', value='36°C', inline=True)
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
