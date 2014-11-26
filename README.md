diff-dwg
========
Compare two engineering drawings in PDF format and output a diff image.

This script makes use of a anaglyph algorithm to compare two PDF drawing files. The files
are first converted to JPG format, then the JPG files are processed. The output file is
a composite of the two input files with deleted pixels highlighted in red and new pixels
highlighted in blue.

This script is composed from snippets from online sources:
Anaglyph Algorithm: https://mail.python.org/pipermail/python-list/2006-May/392738.html
Progresse Bar: http://stackoverflow.com/questions/25202147/tkinter-progressbar-with-indeterminate-duration

At the moment, the script is only compatible with Windows but Linux compatiblity will be added later. 

Requirements
============
1. ImagMagick: http://www.imagemagick.org/ (tested against 6.9.0 Q16)
2. GhostScript: http://ghostscript.com/download/gsdnld.html (tested against 9.15)
3. PythonMagick: http://www.lfd.uci.edu/~gohlke/pythonlibs/ (tested against 0.9.10

Directions
==========
1. Launch the script with "python diff-dwg.pyw"
2. Select if you would like to display the results on the screen or save them to your desktop.
3. Pick the "old" revision PDF file.
4. Pick the "new" revision PDF file.
5. Your results will be shown on the screen or a JPEG will be written to the desktop. The program will highlight items that were added in cyan and the items that were removed in red.
