# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['bot.py'],
             pathex=['X:\\Workspaces\\PyCharm\\DiscordTempBot'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='TempBot',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=['vcruntime140.dll', 'wxmsw30u_core_vc140.dll', 'wxmsw30u_stc_vc140.dll', 'wxbase30u_vc140.dll', 'wxmsw30u_adv_vc140.dll', 'msvcp140.dll', 'wxbase30u_net_vc140.dll'],
          runtime_tmpdir=None,
          console=False , icon='thermometer.ico')
