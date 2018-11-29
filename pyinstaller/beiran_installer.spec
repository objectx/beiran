# -*- mode: python -*-

block_cipher = None


a = Analysis(['../beiran/__main__.py'],
             pathex=[
                '../beiran',
                '../plugins/beiran_package_docker',
                ],
             binaries=[],
             datas=[],
             hiddenimports=[
                'beiran.cli_node',
                'beiran_package_docker.cli_docker',
                'beiran_discovery_dns',
                'beiran_discovery_dns.dns',
                'beiran_discovery_zeroconf',
                'beiran_discovery_zeroconf.zeroconf',
             ],
             hookspath=['./hooks/'],
             runtime_hooks=['./hooks/hook-beiran.plugin.py'],
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
          exclude_binaries=True,
          name='beiran',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )

# onedir config
#coll = COLLECT(exe,
#               a.binaries,
#               a.zipfiles,
#               a.datas,
#               strip=False,
#               upx=True,
#               name='beiran')
