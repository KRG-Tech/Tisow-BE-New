from sqlalchemy.dialects.mysql.mariadb import *
from PyInstaller.utils.hooks import collect_submodules

# Collect all submodules for the mariadb connector
hiddenimports = collect_submodules('sqlalchemy.dialects.mariadb')
