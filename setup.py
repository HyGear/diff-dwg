from distutils.core import setup
import py2exe, numpy, PythonMagick

setup(windows=['diff-dwg.pyw'],
          options = {
           "py2exe":{"dll_excludes":["MSVCP90.dll","VCOMP90.DLL"]}})
