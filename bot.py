import asyncio
import threading
import traceback
from datetime import datetime, timedelta

import PySimpleGUIWx as sg
import discord
import pythoncom
import win32gui
import wmi
import wx
import wx.lib.newevent

from protected_vars import TOKEN

NAME = 'TempBot'
ICON = b'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAAAn1BMVEVHcEyVoqjR4+uywcgWGBnU3+drdHh8h4s9QkROVFfF1t3V4em6ytHN3eQMDQ40OTvK2+PX2+JhaWx5g4dxe39ma21+h4tWWFmGkJVtc3aCjZKVoqfmPTnpRUHlOTXafn7e8vvnfX3tamjrfX3mjI7mTUrmd3fimJvinaDkYF/jdXXrX13qcG+XZGPSaGfnqKx9YmKmZWTefn7omZvEZ2Z/KQCEAAAAHHRSTlMAn+SyBfFffyg40f6+4wEf3PlNeGugn6CfoH6f9oJbWAAAAGtJREFUGNNjYAADFhE2PgZkIKWgwIYiwGisz44qoKSMKiBuII8qII2uQtLQCFVAzEQRVUBCD01AVBfVUE5WbR1eDiQBLjVZWRVmBJ+FW0ZGRpUJSYWAppycFg+SgJCgugYrJ7KpHOzC/BAWAF9YBtSJcOPLAAAAAElFTkSuQmCC'
ICON_URL = 'https://cdn.discordapp.com/avatars/638619913166258186/c267c2a4334d13f6f4e05409064adc75.webp'
QUESTION_URL = 'https://i.imgur.com/Q7DqarN.png'  # https://imgur.com/a/Nf494H0
INFO_URL = 'https://i.imgur.com/A3YXJzs.png'
RED = 0xff0000
HELP_MSG = '''TempBot is designed to display hardware information of the computer that it is running on.

**!temp**
> TempBot will display hardware information for 5 minutes.

**!temp go**
> TempBot will display hardware information indefinitely (until '!temp stop' is run).

**!temp for x**
> TempBot will display hardware information for x amount of minutes.

**!temp stop**
> TempBot will stop updating the message that displays hardware information.

**!temp get x**
> TempBot will get 1 hardware attribute in particular (useful for debugging). Type '!temp get attributes' to see a list of attributes.

**!temp help**
> Displays this help message.

**!temp exit**
> Shuts TempBot down.
'''
bot: discord.Client
tray: sg.SystemTray


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


class TempBot(discord.Client):
    STOP = False
    temp_msg = None  # Union [discord.Message, None]
    initial_login = True

    async def on_ready(self):
        print('Logged in as', self.user)
        if self.initial_login:
            pythoncom.CoInitialize()  # Prevents crash that occurs bc not on main thread
            self.initial_login = False

    @staticmethod
    def plain_embed(title=None, description=None, name=NAME):
        embed = discord.Embed(title=title, description=description, color=RED)
        embed.set_author(name=name, icon_url=ICON_URL)
        return embed

    @staticmethod
    def temp_embed(hw, footer=None):
        if hw.failed_to_load:
            return TempBot.plain_embed('Error:', 'Please start Open Hardware Monitor to see hardware status. '
                                                 "This message will automatically update once it's started.")

        embed = discord.Embed(color=RED)
        embed.set_author(name=NAME, icon_url=ICON_URL)
        try:
            embed.add_field(name='CPU Info:', inline=False,
                            value=f'{hw.cpu_name}: **{hw.cpu_total_usage}**\n\u200b')
        except AttributeError:
            embed.add_field(name='CPU Info:', inline=False,
                            value=f'{hw.cpu_name}\n\u200b')

        for i in range(1, hw.cpu_cores + 1):
            embed.add_field(name=f'CPU Core #{i}', value=f'{hw.cpu_usage[i]}', inline=True)
            if i % 2 == 0:
                embed.add_field(name='\u200b', value='\u200b', inline=True)  # Blank field
        try:
            embed.add_field(name='\u200b\nGPU Info:', value=f'{hw.gpu_name}: **{hw.gpu_temp}**', inline=False)
        except AttributeError:
            pass
        embed.add_field(name='\u200b\nRAM Info:', inline=False,
                        value=f'{hw.ram_name}: {hw.ram_percent_used} | {hw.ram_used}/{hw.ram_total} GB')
        embed.add_field(name='\u200b\nDisk Read:', inline=True, value=f'{hw.disk_read}')
        embed.add_field(name='\u200b\nDisk Write:', inline=True, value=f'{hw.disk_write}')

        if footer:
            embed.set_footer(text=footer, icon_url=INFO_URL)

        return embed

    @staticmethod
    def gen_footer(minutes, finish_at):
        if minutes < 0:
            return "Updating indefinitely. Type '!temp stop' to stop."
        elif minutes:
            stop_at = str(finish_at - datetime.now())
            stop_at = stop_at.split('.', 1)[0]
            if stop_at[0:2] == '0:':
                stop_at = stop_at[2:]
            return f"Updating for {minutes} minute{'' if minutes == 1 else 's'}. Type '!temp stop' to stop.\n" +\
                   "Stopping in " + stop_at

    async def temp(self, message, minutes=-1):
        finish_at = datetime.max if minutes == -1 else datetime.now() + timedelta(minutes=minutes)
        self.STOP = False
        while datetime.now() < finish_at and not self.STOP:
            hw = HardwareInfo()

            embed = self.temp_embed(hw, TempBot.gen_footer(minutes, finish_at))
            if self.temp_msg:
                try:
                    await self.temp_msg.edit(embed=embed)
                except discord.HTTPException:
                    self.STOP = True
            else:
                self.temp_msg = await message.channel.send(embed=embed)
            await asyncio.sleep(5)
        embed = self.temp_embed(hw, 'Message is no longer updating.')
        await self.temp_msg.edit(embed=embed)
        self.temp_msg = None

    async def get_hw_attr(self, message: discord.Message, attr: str):
        try:
            await message.channel.send(HardwareInfo().__getattribute__(attr))
        except AttributeError:
            await message.channel.send(f'Error: No {attr} attribute exists.')

    async def on_message(self, message: discord.Message):
        msg: str = message.content.lower()

        if msg.startswith('!temp'):
            if len(msg) == 5:  # Must just be !temp
                await self.temp_wait_before_exit()
                await self.temp(message, 5)
                return
            try:
                command = msg.split()[1]
            except IndexError:
                return
            if command == 'for':
                await self.temp_wait_before_exit()
                try:
                    m = abs(int(msg.split()[2]))
                except ValueError:
                    return
                await self.temp(message, m)
            elif command == 'go':
                await self.temp_wait_before_exit()
                await self.temp(message)
            elif command == 'stop':
                self.STOP = True
            elif command == 'get':
                await self.get_hw_attr(message, msg.split()[2])
            elif command == 'help':
                await message.channel.send(embed=TempBot.plain_embed(description=HELP_MSG, name='TempBot Help:'))
            elif command == 'exit':
                await self.exit()

    async def temp_wait_before_exit(self, close=False):
        """
        Waits for TempBot to put 'Message is no longer updating.' in the status of the message before exiting.

        :param close: Whether or not TempBot should close it's connection to discord after waiting.
        """
        self.STOP = True
        while self.temp_msg is not None:  # When temp_msg is None
            await asyncio.sleep(0.5)
        if close:
            await self.close()

    async def notify_startup_crash(self):
        """If a crash happens during startup, wait for TempBot to sign into discord first, so that the connection can be
        gracefully closed later."""
        while self.initial_login:
            await asyncio.sleep(0.5)
        await self.exit()

    async def exit(self):
        await self.temp_wait_before_exit()

        # https://wxpython.org/Phoenix/docs/html/events_overview.html
        SomeNewEvent, EVT_SOME_NEW_EVENT = wx.lib.newevent.NewEvent()

        def handler(event):
            tray.TaskBarIcon.menu_item_chosen = event.menu_item
            tray.TaskBarIcon.app.ExitMainLoop()

        tray.App.Bind(EVT_SOME_NEW_EVENT, handler)
        evt = SomeNewEvent(menu_item='Exit')
        wx.PostEvent(tray.App, evt)


def main():
    global bot, tray

    def discord_thread():
        bot.run(TOKEN)

    bot = TempBot(activity=discord.Activity(name='!temp help', type=discord.ActivityType.listening))
    threading.Thread(target=discord_thread, name='DiscordThread').start()

    tray_menu = ['menu', [
        'Exit'
    ]]

    tray = sg.SystemTray(
        menu=tray_menu,
        data_base64=ICON,
        tooltip=NAME
    )

    try:
        if HardwareInfo().failed_to_load:
            win32gui.MessageBox(None, 'Open Hardware Monitor must be running for !temp to work.', 'Warning', 48)
    except:
        traceback.print_exc()
        bot.loop.create_task(bot.notify_startup_crash())

    while True:  # Handle Tray events
        event = tray.Read()
        if event == 'Exit':
            tray.Hide()
            bot.loop.create_task(bot.temp_wait_before_exit(close=True))
            break


if __name__ == '__main__':
    main()
