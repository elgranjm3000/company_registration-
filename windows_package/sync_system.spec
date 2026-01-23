# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['sync_system.py'],
             pathex=[],
             binaries=[],
             datas=[('smart_sync_complete.py', '.')],
             hiddenimports=['psycopg2', 'psycopg2.extensions', 'mysql.connector', 'tkinter', 'tkinter.ttk', 'tkinter.scrolledtext'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=['matplotlib', 'numpy', 'pandas'],
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
          name='sync_system',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
