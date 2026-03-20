# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller hook para win10toast
Incluye los metadatos necesarios para que pkg_resources funcione correctamente
"""

from PyInstaller.utils.hooks import get_package_paths

# Obtener las rutas del paquete win10toast
pkg_paths = get_package_paths('win10toast')

# Incluir los metadatos (.egg-info o .dist-info) para pkg_resources
datas = [
    (pkg_paths['path'], 'win10toast'),
]

# Buscar e incluir los metadatos del paquete
import os
import glob

# Buscar directorios .egg-info o .dist-info
site_packages = os.path.dirname(pkg_paths['path'])
for metadata_dir in glob.glob(os.path.join(site_packages, 'win10toast-*.dist-info')):
    if os.path.isdir(metadata_dir):
        datas.append((metadata_dir, '.'))

for metadata_dir in glob.glob(os.path.join(site_packages, 'win10toast-*.egg-info')):
    if os.path.isdir(metadata_dir):
        datas.append((metadata_dir, '.'))
