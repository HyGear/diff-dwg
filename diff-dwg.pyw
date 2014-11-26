"""
diff-dwg-new.py: Compare two engineering drawings in PDF format and output a diff image.

This script makes use of a anaglyph algorithm to compare two PDF drawing files. The files
are first converted to JPG format, then the JPG files are processed. The output file is
a composite of the two input files with deleted pixels highlighted in red and new pixels
highlighted in blue.

This script is composed from snippets from online sources:
Anaglyph Algorithm: https://mail.python.org/pipermail/python-list/2006-May/392738.html
Progresse Bar: http://stackoverflow.com/questions/25202147/tkinter-progressbar-with-indeterminate-duration
"""

from Tkinter import *
import tkFileDialog as tk
from PythonMagick import Image as PMImage
import Image,timeit,os,numpy,ttk,threading,time
import tkMessageBox
import subprocess

global tempdir,size_check
#Change this if needed
tempdir = 'c:\\temp\\diff-dwg\\'
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
        self.master.title("diff-dwg")
        global v
        v = StringVar()
        v.set("1")
        Radiobutton(self, text = "Display on Screen", variable=v, value="1").grid(row = 0, column = 0, sticky = W)
        Radiobutton(self, text = "Save JPG to Desktop", variable=v, value="2").grid(row = 1, column = 0, sticky = W)
        Button(self, text = "OK", command = self.fileselect).grid(row = 2, column = 0, sticky = S)

    def fileselect(self):
        #Create a set of variables to pass back to main program.
        global filePath1
        global filePath2 
        filePath1 = ""
        filePath2 = ""
        #self.master.destroy()
        #root = Tkinter.Tk()
        self.master.withdraw()
        status_1 = 0
        status_2 = 0
        while filePath1 == "":
            if status_1 == 1:
                error_msg("Error","Please select a valid file.")
            filePath1 = tk.askopenfilename(title="Open First PDF (Old Drawing)")
            filePath1 = filePath1.replace("/","\\\\")
            status_1 = 1
        
        while filePath2 == "":
            if status_2 == 1:
                error_msg("Error","Please select a valid file.")
            filePath2 = tk.askopenfilename(title="Open Second PDF (New Drawing)")
            filePath2 = filePath2.replace("/","\\\\")
            status_2 = 1
        
        print ("Old Drawing: "+filePath1+"\n")  #Display first filepath
        print ("New Drawing: "+filePath2+"\n")  #Display second filepath
        self.master.destroy()
        
#A class to display the image created


#Helper functions
def pdf2jpg(pdf,temp):
    #Generate the path for the jpg file. Need to use a temp directory in case
    #pdf location is read only.
    pdf = str(pdf)
    base = os.path.basename(pdf)
    basefile = os.path.splitext(base)
    jpg = temp + basefile[0] + ".jpg"
    jpg = str(jpg.replace("\\","\\\\"))
    jpg = str(jpg)
    pdf = str(pdf)
    img = PMImage()
    img.density('200')
    img.depth(24)
    img.read(pdf)
    img.write(jpg)    
    img = Image.open(jpg)
    rgbimg = Image.new("RGBA", img.size)
    rgbimg.paste(img)
    rgbimg.save(jpg)
    return jpg

def maketmp(temp):
    if (not os.path.isdir(temp)):
        print ("We need to make a temp directory")
        os.system("mkdir %s" % temp)
        
def anaglyph(image1, image2, method=true_anaglyph):
    m1, m2 = [numpy.array(m).transpose() for m in method]
    im1, im2 = image_to_array(image1), image_to_array(image2)
    composite = numpy.dot(im1, m1) + numpy.dot(im2, m2)
    result = array_to_image(image1.mode, image1.size, composite)
    return result

def image_to_array(im):
    s = im.tostring()
    dim = len(im.getbands())
    return numpy.fromstring(s, numpy.uint8).reshape(len(s)/dim, dim)

def array_to_image(mode, size, a):
    return Image.fromstring(mode, size, a.reshape(len(a)*len(mode), 1).astype(numpy.uint8).tostring())

def process_images(win):
    #FIXME: Compare images to make sure they are the same size.
    global filePath1, filePath2, v, size_check
    start = timeit.default_timer()
    img1_file = pdf2jpg(filePath1, tempdir)
    img2_file = pdf2jpg(filePath2, tempdir)
    im1, im2 = Image.open(img2_file), Image.open(img1_file)
    file_string = os.path.splitext(os.path.basename(filePath1))[0] + "-diff.jpg"
    if im1.size[0] == im2.size[0] and im1.size[1] == im2.size[1]:
        print "Drawing sizes match"
        
        if v.get() == "1":
            dispimg = tempdir + file_string
            anaglyph(im1, im2, half_color_anaglyph).save(dispimg, quality=90)
            win.quit()
            #Launch Windows Photo Viewer to view image
            #os.system("rundll32 \"C:\Program Files\Windows Photo Viewer\PhotoViewer.dll\", ImageView_Fullscreen %s" % dispimg)
            substring="rundll32 \"C:\Program Files\Windows Photo Viewer\PhotoViewer.dll\", ImageView_Fullscreen %s" % dispimg
            subprocess.call(substring,shell=True)
            #Clean up after ourselves.
            os.remove(dispimg)
        else:
            userhome = os.path.expanduser('~')
            desktop = userhome + '\\Desktop\\'
            dispimg = desktop + file_string
            anaglyph(im1, im2, half_color_anaglyph).save(dispimg, quality=90)
            win.quit()
    else:
        print "Drawing size mismatch."
        size_check = 1        
        win.quit()
    del im1,im2
    os.remove(img1_file)
    os.remove(img2_file)
    stop = timeit.default_timer()
    print "Run time was", stop - start
    print "Done"
        
    
def complete_msg(s1,s2):
    msg = Tk()
    msg.withdraw()
    tkMessageBox.showinfo(s1,s2)
    msg.destroy()
    return True

def error_msg(s1,s2):
    emsg = Tk()
    emsg.withdraw()
    tkMessageBox.showerror(s1,s2)
    emsg.destroy()
    return True

    
def progress(win):
    ft = ttk.Frame()
    ft.pack(expand=True, fill=BOTH, side=TOP)
    pb_hD = ttk.Progressbar(ft, length=200, orient='horizontal', mode='indeterminate')
    pb_hD.pack(expand=True, fill=BOTH, side=TOP)
    pb_hD.start(50)
    win.mainloop()
    
def Main():
    global v
    root = Tk()
    root.wm_title("Choose images")
    app = DiffApp(master=root)
    app.mainloop()
    maketmp(tempdir)
    win = Tk()
    win.wm_title("Processing images")
    t1=threading.Thread(target=process_images, args=(win,))
    t1.start()
    progress(win)  # This will block while the mainloop runs
    t1.join()
    #Clean up windows/files and show messages to user
    win.destroy()
    if v.get() == "2" and size_check != 1:
        complete_msg("Image Complete", "Image complete. Please check your desktop")    
    if size_check == 1:
        error_msg("Size mismatch","Drawing sizes do not match. Please try again")
    

    
if __name__=='__main__':
    Main()
