# -*- coding: utf-8 -*-
"""
diff-dwg-new.py: Compare two engineering drawings in PDF format and output a diff image.
This script makes use of a anaglyph algorithm to compare two PDF drawing files. The files
are first converted to PNG format, then the PNG files are processed. The output file is
a composite of the two input files with deleted pixels highlighted in red and new pixels
highlighted in blue.
This script is composed from snippets from online sources:
Anaglyph Algorithm: https://mail.python.org/pipermail/python-list/2006-May/392738.html
"""
from tkinter import *
from tkinter import messagebox
import tkinter.filedialog as tk
import tempfile
import fitz
import timeit,os,numpy
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from sys import platform
from os.path import isfile, join
from os import listdir
import re

global tempdir,olddir,newdir,diffdir,watermark
os_temp_dir = tempfile.gettempdir()

tempdir = join(os_temp_dir, 'diff-dwg')
olddir = join(os_temp_dir, 'old')
newdir = join(os_temp_dir, 'new')
diffdir = join(os_temp_dir, 'diff')

size_check = 0

#Anaglyph matrices
_magic = [0.299, 0.587, 0.114]
_zero = [0, 0, 0]
_ident = [[1, 0, 0],
          [0, 1, 0],
          [0, 0, 1]]

true_anaglyph = ([_magic, _zero, _zero], [_zero, _zero, _magic])
gray_anaglyph = ([_magic, _zero, _zero], [_zero, _magic, _magic])
color_anaglyph = ([_ident[0], _zero, _zero], [_zero, _ident[1], _ident[2]])
color2_anaglyph = ([[1, 0, 0],[0,0,0],[0,0,0.603922]],[[0,0,0],[0,1,0],[0,0,0.396078]])
half_color_anaglyph = ([_magic, _zero, _zero], [_zero, _ident[1], _ident[2]])
optimized_anaglyph = ([[0, 0.7, 0.3], _zero, _zero], [_zero, _ident[1], _ident[2]])
methods = [true_anaglyph, gray_anaglyph, color_anaglyph, half_color_anaglyph, optimized_anaglyph]

class DiffApp(Frame):
    def __init__(self, master):
        Frame.__init__(self,master)
        self.grid()
        self.master.title("diff-dwg - Batch Drawing Comparison")
        global v,v_status,v_status_f
        v = StringVar()
        v.set("1")
        v_status = StringVar()
        v_status_f = StringVar()
        v_status.set("Ready...")
        v_status_f.set("Please select directories to compare.")
        self.grid_columnconfigure(0,minsize=350)
        self.pack(padx=10,pady=10)
        Radiobutton(self, text = "Single Drawing Comparison", variable=v, value="1").grid(row = 0, column = 0, sticky = S)
        Radiobutton(self, text = "Batch Drawing Comparison", variable=v, value="2").grid(row = 1, column = 0, sticky = S)
        Button(self, text = "START", command = self.fileselect).grid(row = 2, column = 0, sticky = S, padx=5,pady=5)
        status_lower=Message(self, textvariable=v_status_f,bd=1, relief=SUNKEN, anchor=W, width=330, font=('arial',8)).grid(row=3, column=0, sticky='WE')
        status=Label(self, textvariable=v_status, bd=1, relief=SUNKEN, anchor=W).grid(row=4, column=0, sticky='WE')

    def fileselect(self):
        #Create a set of variables to pass back to main program.
        global filePath1
        global filePath2
        global filePath3
        global tempdir,olddir,newdir,diffdir,watermark
        filePath1 = ""
        filePath2 = ""
        filePath3 = ""
        #self.master.withdraw()
        status_1 = 0
        status_2 = 0
        status_3 = 0
        while filePath1 == "":
            if status_1 == 1 and v.get() == "1":
                error_msg("Error", "Please select a valid file.")
                return
            elif status_1 == 1 and v.get() == "2":
                error_msg("Error", "Please select a valid directory.")
            elif status_1 == 0 and v.get() == "1":
                filePath1 = tk.askopenfilename(title="Select old drawing")
            elif status_1 == 0 and v.get() == "2":
                filePath1 = tk.askdirectory(title="Select location of old drawings")
            else:
                error_msg("Error", "Uh oh. Something broke.")
                status_1=1
            if platform == "win32":
                filePath1 = filePath1.replace("/","\\\\")
                olddir=filePath1
            status_1 = 1

        while filePath2 == "":
            if status_2 == 1 and v.get() == "1":
                error_msg("Error", "Please select a valid file.")
                return
            elif status_2 == 1 and v.get() == "2":
                error_msg("Error", "Please select a valid directory.")
            elif status_2 == 0 and v.get() == "1":
                filePath2 = tk.askopenfilename(title="Select new drawing")
            elif status_2 == 0 and v.get() == "2":
                filePath2 = tk.askdirectory(title="Select location of new drawings")
            else:
                error_msg("Error", "Uh oh. Something broke.")
                status_2=1
            if platform == "win32":
                filePath2 = filePath2.replace("/","\\\\")
                newdir=filePath2
            status_2 = 1

        while filePath3 == "":
            if status_3 == 1:
                error_msg("Error", "Please select a valid directory.")
            filePath3 = tk.askdirectory(title="Select location to output DIFF drawings.")
            if platform == "win32":
                filePath3 = filePath3.replace("/","\\\\")
                diffdir=filePath3
            else:
                diffdir = filePath3
            status_3 = 1

        print ("Old Drawing Path: "+filePath1+"\n")  #Display first filepath
        print ("New Drawing Path: "+filePath2+"\n")  #Display second filepath
        print ("DIFF Drawing Path: "+filePath3+"\n")
        #self.master.deiconify()
        v_status.set("Processing images...")
        v_status_f.set("Old Drawing:\n"+filePath1+"\n"+"New Drawing:\n"+filePath2)
        self.update_idletasks()
        if v.get() == "1":
            maketmp(tempdir)
            process_images()
        elif v.get()== "2":
            maketmp(tempdir)
            process_batch()
        self.master.destroy()

def pdf2png(pdf,temp):
    #Generate the path for the png file. Need to use a temp directory in case
    #pdf location is read only.
    pdf = str(pdf)
    base = os.path.basename(pdf)
    basefile = os.path.splitext(base)
    png = join(temp, basefile[0] + ".png")
    print(pdf)
    print(png)
    doc = fitz.open(pdf)
    xres=2
    yres=2
    mat= fitz.Matrix(xres,yres)
    for page in doc:
        pix = page.getPixmap(matrix=mat, colorspace="rgb", alpha = False)
        pix.writePNG(png)
    return png

def maketmp(temp):
    if (not os.path.isdir(temp)):
        print("We need to make %s directory" % temp)
        os.system("mkdir %s" % temp)

def anaglyph(image1, image2, method=true_anaglyph):
    m1, m2 = [numpy.array(m).transpose() for m in method]
    im1, im2 = image_to_array(image1), image_to_array(image2)
    composite = numpy.dot(im1, m1) + numpy.dot(im2, m2)
    result = array_to_image(image1.mode, image1.size, composite)
    return result

def image_to_array(im):
    s = im.tobytes()
    dim = len(im.getbands())
    return numpy.frombuffer(s, numpy.uint8).reshape(len(s)//dim, dim)

def array_to_image(mode, size, a):
    return Image.frombytes(mode, size, a.reshape(len(a)*len(mode), 1).astype(numpy.uint8).tostring())

def watermark_text(input_image_path,
                   output_image_path,
                   text, pos):
    photo = Image.open(input_image_path)
    drawing = ImageDraw.Draw(photo)
    red = (255, 0, 0)
    if platform == 'win32':
        font = ImageFont.truetype("C:\\Windows\\Fonts\\Calibri.ttf", 30)
    elif platform == 'linux':
        font = ImageFont.load_default()
    drawing.text(pos, text, fill=red, font=font)
    photo.save(output_image_path)

def find_char(find_s,find_c):
    i=0
    j=0
    k=len(find_s)
    for c in find_s:
        if c == find_c:
            j=i
        i=i+1
    trim=k-j
    if trim == k:
        trim = -1
    else:
        trim = trim+1
    return trim

def process_batch():
    global size_check
    start = timeit.default_timer()
    oldfiles = [f for f in listdir(olddir) if isfile(join(olddir,f))]
    newfiles = [n for n in listdir(newdir) if isfile(join(newdir,n))]
    pattern=re.compile('^([a-zA-Z])+')
    # The loop below attempts to match part numbers in the old folder and new folder. This is done
    # by dropping the first and last character and anything after an underscore. This tends to
    # find a match for most part numbering schemes.
    for old_f in oldfiles:
        if old_f[-3:] == "pdf":
            trim_old=find_char(old_f,"_")
            if trim_old == -1:
                trim_old = 5
            if pattern.match(old_f):
                first_file = old_f[3:trim_old]
            else:
                first_file = old_f[1:-trim_old]
            for new_f in newfiles:
                if new_f[-3:] == "pdf":
                    trim_new=find_char(new_f,"_")
                    if trim_new == -1:
                        trim_new = 5
                    if pattern.match(new_f):
                        second_file = new_f[3:trim_old]
                    else:
                        second_file = new_f[1:-trim_new]
                    if second_file == first_file:
                        print("Name match found")
                        print("New file: ",new_f)
                        print("Old file: ",old_f)
                        filePath1 = join(olddir, old_f)
                        filePath2 = join(newdir, new_f)
                        print(filePath1)
                        img1_file = pdf2png(filePath1, tempdir)
                        img2_file = pdf2png(filePath2, tempdir)
                        im1, im2 = Image.open(img2_file), Image.open(img1_file)
                        file_string = os.path.splitext(os.path.basename(new_f))[0] + "-diff.png"
                        if im1.size[0] == im2.size[0] and im1.size[1] == im2.size[1]:
                            print("Drawing sizes match")
                            dispimg = join(tempdir, file_string)
                            anaglyph(im1, im2, color2_anaglyph).save(dispimg, quality=90)
                            waterimg = join(diffdir, file_string)
                            watermark_text(dispimg,waterimg,"UNCONTROLLED COPY",pos=(0, 0))
                        else:
                            print("Drawing size mismatch.")
                            size_check = 1
                        del im1,im2
                        try:
                            os.remove(img1_file)
                            os.remove(img2_file)
                            os.remove(dispimg)
                        except:
                            print("Error while deleting temp files. Please check ", tempdir)

    stop = timeit.default_timer()
    print("Run time was", stop - start)
    print("Done")

def process_images():
    global filePath1, filePath2, v, size_check
    start = timeit.default_timer()
    img1_file = pdf2png(filePath1, tempdir)
    img2_file = pdf2png(filePath2, tempdir)
    im1, im2 = Image.open(img2_file), Image.open(img1_file)
    file_string = os.path.splitext(os.path.basename(filePath1))[0] + "-diff.png"
    if im1.size[0] == im2.size[0] and im1.size[1] == im2.size[1]:
        print("Drawing sizes match")
        dispimg = join(diffdir, file_string)
        print(newdir)
        print(olddir)
        print(diffdir)
        print(dispimg)
        anaglyph(im1, im2, color2_anaglyph).save(dispimg, quality=90)
        watermark_text(dispimg, dispimg, "UNCONTROLLED COPY", pos=(0, 0))
    else:
        print("Drawing size mismatch.")
        size_check = 1
    del im1,im2
    os.remove(img1_file)
    os.remove(img2_file)
    stop = timeit.default_timer()
    print("Run time was", stop - start)
    print("Done")

def complete_msg(s1,s2):
    msg = Tk()
    msg.withdraw()
    messagebox.showinfo(s1,s2)
    msg.destroy()
    return True

def error_msg(s1,s2):
    emsg = Tk()
    emsg.withdraw()
    messagebox.showerror(s1,s2)
    emsg.destroy()
    return True

def Main():
    global v
    root = Tk()
    root.wm_title("Choose images")
    app = DiffApp(master=root)
    app.mainloop()
    if v.get() == "2" and size_check != 1:
        complete_msg("Image Complete", "Image complete. Please check %s" % diffdir)
    if size_check == 1:
        error_msg("Drawing Error","A temp drawing failed to delete or there was a size mismatch. Please check output results.")


if __name__=='__main__':
    Main()
