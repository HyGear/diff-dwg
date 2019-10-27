diff-dwg
========
Compare two engineering drawings in PDF format and output a diff image.

This script makes use of a anaglyph algorithm to compare two PDF drawing files or two folders
of PDF drawing files. The files are first converted to PNG format, then the PNG files are 
processed.  The output file is a composite of the two input files with deleted pixels highlighted 
in magenta and new pixels highlighted in green. A watermark is also added to the diff drawing
to designate it as an uncontrolled copy.

The main anaglyph algorithm is taken from the following source:
Anaglyph Algorithm: https://mail.python.org/pipermail/python-list/2006-May/392738.html

At the moment, the script is only compatible with Windows. 

Requirements
============
1. PyMuPDF
2. Python Image Library (PIL)
3. Numpy

Use `pip install -r requirements.txt` to install the packages.

Directions
==========
1. Launch the script with "python diff-dwg.pyw"
2. Choose if you would like to do a single file comparison or batch file comparison.
3. If doing a single file comparison, choose the old file, new file, and output location.
4. If doing a batch file comparison, choose the location of the old files, location of the new files, and output location.
5. Check the output location for the "DIFF" images.
