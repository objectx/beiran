# -*- mode: python -*-
#
# This spec auto generated by command below.
#
#
#    /pyinstaller/pyinstaller.sh --onefile --name beiran \
#                                 --clean --log-level DEBUG --noconfirm \
#                                 --hidden-import  beiran.cli_node \
#                                 --hidden-import  beiran_package_container.cli_docker \
#                                 --hidden-import  beiran_discovery_dns \
#                                 --hidden-import  beiran_discovery_dns.dns \
#                                 --hidden-import  beiran_discovery_zeroconf \
#                                 --hidden-import  beiran_discovery_zeroconf.zeroconf \
#                                 --paths /opt/beiran/pyinstaller \
#                                 --paths ../beiran \
#                                 --paths ../plugins/beiran_package_container \
#                                 --exclude-module pycrypto \
#                                 --exclude-module PyInstaller \
#                                 --additional-hooks-dir ./hooks/ \
#                                 --runtime-hook ./hooks/hook-beiran.plugin.py \
#                                 ../beiran/__main__.py
#

block_cipher = None


a = Analysis(['../beiran/__main__.py'],
             pathex=['/opt/beiran/pyinstaller', '../beiran', '../plugins/beiran_package_container', '/opt/beiran/pyinstaller'],
             binaries=[],
             datas=[],
             hiddenimports=['beiran.cli_node', 'beiran_package_container.cli_docker', 'beiran_discovery_dns', 'beiran_discovery_dns.dns', 'beiran_discovery_zeroconf', 'beiran_discovery_zeroconf.zeroconf'],
             hookspath=['./hooks/'],
             runtime_hooks=['./hooks/hook-beiran.plugin.py'],
             excludes=['pycrypto', 'PyInstaller', 'pycrypto', 'PyInstaller'],
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
          name='beiran',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
