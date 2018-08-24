"""
diff-dwg-new.py: Compare two engineering drawings in PDF format and output a diff image.
This script makes use of a anaglyph algorithm to compare two PDF drawing files. The files
are first converted to PNG format, then the PNG files are processed. The output file is
a composite of the two input files with deleted pixels highlighted in red and new pixels
highlighted in blue.
This script is composed from snippets from online sources:
Anaglyph Algorithm: https://mail.python.org/pipermail/python-list/2006-May/392738.html
Progresse Bar: http://stackoverflow.com/questions/25202147/tkinter-progressbar-with-indeterminate-duration
"""

from tkinter import *
from tkinter import messagebox
#from tkinter import ttk
import tkinter.filedialog as tk
import timeit,os,numpy #threading
#Setting some environment variables so ImageMagick and GS portable will load correctly.
#These are only needed if compiling with PyInstaller.
#os.environ['PATH'] = os.environ['PATH'] + ';C:\\diff-dwg3\\gs\\gs9.21\\bin\\;C:\\diff-dwg3\\ImageMagick-6.9.10-Q16\\bin\\'
#os.environ['MAGICK_HOME'] = os.path.abspath('C:\\diff-dwg3\\ImageMagick-6.9.10-Q16\\')
#os.environ['MAGICK_CODER_MODULE_PATH'] = 'C:\\diff-dwg3\\ImageMagick-6.9.10-Q16\\modules\\coders\\;C:\\diff-dwg3\\gs\\gs9.21\\bin\\'
#os.environ['MAGICK_CONFIGURE_PATH'] = 'C:\\diff-dwg3\\ImageMagick-6.9.10-Q16\\'
#os.environ['MAGICK_CODER_FILTER_PATH'] = 'C:\\diff-dwg3\\ImageMagick-6.9.10-Q16\\modules\\filters\\'
#os.environ['LD_LIBRARY_PATH'] = "C:\\\diff-dwg3\\ImageMagick-6.9.10-Q16"
#os.environ['GS'] = 'C:\\diff-dwg3\\gs\\gs9.21\\bin\\gswin64.exe'
#os.environ['GSC'] = 'C:\\diff-dwg3\\gs\\gs9.21\\bin\\gswin64c.exe'
#os.environ['GS_DLL'] = 'C:\\diff-dwg3\\gs\\gs9.21\\bin\\gsdll64.dll'
#os.environ['GS_LIB'] = 'C:\\diff-dwg3\\gs\\gs9.21\\lib\\'
from wand.image import Image as WImage
from wand.color import Color as Color
from PIL import Image
from sys import platform

import subprocess

global tempdir,size_check
#Setting a temporary directory. Change this if needed
#FIXME: Need to clean-up directory when done.
if platform == "win32":
    tempdir = 'c:\\temp\\diff-dwg\\'
else:
    tempdir = '/tmp/diff-dwg/'						  
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

# Create a GUI class that does the following:
# 1. Generate a simple selection window.
# 2. Launch a file selection dialog.
class DiffApp(Frame):
    def __init__(self, master):
        Frame.__init__(self,master)
        self.grid()
        self.master.title("diff-dwg - Drawing Comparison")
        global v,v_status,v_status_f
        v = StringVar()
        v.set("1")
        v_status = StringVar()
        v_status_f = StringVar()
        v_status.set("Ready...")
        v_status_f.set("Please select files.")
        self.grid_columnconfigure(0,minsize=350)
        self.pack(padx=10,pady=10)
        Radiobutton(self, text = "Display on Screen", variable=v, value="1").grid(row = 0, column = 0, sticky = S)
        Radiobutton(self, text = "Save PNG to Desktop", variable=v, value="2").grid(row = 1, column = 0, sticky = S)
        Button(self, text = "OK", command = self.fileselect).grid(row = 2, column = 0, sticky = S, padx=5,pady=5)
        status_lower=Message(self, textvariable=v_status_f,bd=1, relief=SUNKEN, anchor=W, width=330, font=('arial',8)).grid(row=3, column=0, sticky='WE')
        status=Label(self, textvariable=v_status, bd=1, relief=SUNKEN, anchor=W).grid(row=4, column=0, sticky='WE')																									 

    def fileselect(self):
        #Create a set of variables to pass back to main program.
        global filePath1
        global filePath2 
        filePath1 = ""
        filePath2 = ""
        #self.master.withdraw()
        status_1 = 0
        status_2 = 0
        while filePath1 == "":
            if status_1 == 1:
                error_msg("Error","Please select a valid file.")
            filePath1 = tk.askopenfilename(title="Open First PDF (Old Drawing)")
            if platform == "win32":					   
                filePath1 = filePath1.replace("/","\\\\")
            status_1 = 1
        
        while filePath2 == "":
            if status_2 == 1:
                error_msg("Error","Please select a valid file.")
            filePath2 = tk.askopenfilename(title="Open Second PDF (New Drawing)")
            if platform == "win32":					   
                filePath2 = filePath2.replace("/","\\\\")
            status_2 = 1
        print ("Old Drawing: "+filePath1+"\n")  #Display first filepath
        print ("New Drawing: "+filePath2+"\n")  #Display second filepath
        #self.master.deiconify()
        v_status.set("Processing images...")
        v_status_f.set("Old Drawing:\n"+filePath1+"\n"+"New Drawing:\n"+filePath2)
        self.update_idletasks()
        maketmp(tempdir)
        process_images()
        self.master.destroy()
        

#Helper functions
def pdf2png(pdf,temp):
    #Generate the path for the png file. Need to use a temp directory in case
    #pdf location is read only.
    pdf = str(pdf)
    base = os.path.basename(pdf)
    basefile = os.path.splitext(base)
    png = temp + basefile[0] + ".png"
    png = str(png)
    pdf = str(pdf)
    with WImage(filename=pdf, resolution=200) as img:
        img.background_color=Color('white')
        img.alpha_channel='remove'
        img.depth=24
        img.save(filename=png)  
    img = Image.open(png)
    rgbimg = Image.new("RGB", img.size)
    rgbimg.paste(img)
    rgbimg.save(png)
    return png

def maketmp(temp):
    if (not os.path.isdir(temp)):
        print("We need to make a temp directory")
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

def process_images():
    #FIXME: Compare images to make sure they are the same size.
    global filePath1, filePath2, v, size_check
    start = timeit.default_timer()
    img1_file = pdf2png(filePath1, tempdir)
    img2_file = pdf2png(filePath2, tempdir)
    im1, im2 = Image.open(img2_file), Image.open(img1_file)
    file_string = os.path.splitext(os.path.basename(filePath1))[0] + "-diff.png"
    if im1.size[0] == im2.size[0] and im1.size[1] == im2.size[1]:
        print("Drawing sizes match")
        
        if v.get() == "1":
            dispimg = tempdir + file_string
            anaglyph(im1, im2, color2_anaglyph).save(dispimg, quality=90)
            if platform == "win32":
                substring="rundll32 \"C:\Program Files\Windows Photo Viewer\PhotoViewer.dll\", ImageView_Fullscreen %s" % dispimg
            else:
                substring="eog %s" % dispimg
            subprocess.call(substring,shell=True)
            #Clean up after ourselves.
            os.remove(dispimg)
        else:
            userhome = os.path.expanduser('~')
            if platform == "win32":
                desktop = userhome + '\\Desktop\\'
            else:
                desktop = userhome + '/Desktop/'
            dispimg = desktop + file_string
            anaglyph(im1, im2, color2_anaglyph).save(dispimg, quality=90)
    else:
        print("Drawing size mismatch.")
        #FIXME: Add a message window that drawings do not match and recall the main command window.
        size_check = 1        
    del im1,im2
    os.remove(img1_file)
    os.remove(img2_file)
    stop = timeit.default_timer()
    print("Run time was", stop - start)
    print("Done")
   # self.master.destroy()
        
    
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

    
#def progress(win):
#    ft = ttk.Frame()
#    ft.pack(expand=True, fill=BOTH, side=TOP)
#    pb_hD = ttk.Progressbar(ft, length=200, orient='horizontal', mode='indeterminate')
#    pb_hD.pack(expand=True, fill=BOTH, side=TOP)
#    pb_hD.start(50)
#    win.mainloop()
    
def Main():
    global v
    root = Tk()
    root.wm_title("Choose images")
    app = DiffApp(master=root)
    app.mainloop()
    if v.get() == "2" and size_check != 1:
        complete_msg("Image Complete", "Image complete. Please check your desktop")    
    if size_check == 1:
        error_msg("Size mismatch","Drawing sizes do not match. Please try again")
    

    
if __name__=='__main__':
    Main()
