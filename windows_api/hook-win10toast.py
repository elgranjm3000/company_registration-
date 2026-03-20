# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller hook para win10toast
Incluye los metadatos necesarios para que pkg_resources funcione correctamente
"""

from PyInstaller.utils.hooks import get_package_paths
import os
import glob

# Obtener las rutas del paquete win10toast
# get_package_paths devuelve una tupla: (base_path, list_of_files)
pkg_base, pkg_files = get_package_paths('win10toast')

# Incluir los metadatos (.egg-info o .dist-info) para pkg_resources
datas = []

# Buscar directorios .egg-info o .dist-info en el directorio padre
site_packages = os.path.dirname(pkg_base)
for metadata_dir in glob.glob(os.path.join(site_packages, 'win10toast-*.dist-info')):
    if os.path.isdir(metadata_dir):
        datas.append((metadata_dir, '.'))

for metadata_dir in glob.glob(os.path.join(site_packages, 'win10toast-*.egg-info')):
    if os.path.isdir(metadata_dir):
        datas.append((metadata_dir, '.'))
