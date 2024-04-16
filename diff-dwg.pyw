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
import fitz
import timeit,os,numpy
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from sys import platform
from os.path import isfile, join
from os import listdir
import re
import math
import cv2

global tempdir,olddir,newdir,diffdir,watermark

if platform == "win32":
    tempdir = 'c:\\temp\\diff-dwg'
else:
    tempdir = '/tmp/diff-dwg'
olddir = ''
newdir = ''
diffdir = ''

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
        global v,check,v_status,v_status_f
        v = StringVar()
        check = IntVar()
        v.set("1")
        v_status = StringVar()
        v_status_f = StringVar()
        v_status.set("Ready...")
        v_status_f.set("Please select directories to compare.")
        self.grid_columnconfigure(0,minsize=350)
        self.pack(padx=10,pady=10)
        Radiobutton(self, text = "Single Drawing Comparison", variable=v, value="1", fg='black').grid(row = 0, column = 0, sticky='S')
        Radiobutton(self, text = "Batch Drawing Comparison", variable=v, value="2", fg='black').grid(row = 1, column = 0, sticky='S')
        Checkbutton(self, text = "Attempt image alignment", variable=check, fg='black').grid(row = 2, column = 0, sticky='S')
        Button(self, text = "START", command = self.fileselect).grid(row = 3, column = 0, sticky = S, padx=5,pady=5)
        status_lower=Message(self, textvariable=v_status_f,bd=1, relief=SUNKEN, anchor=W, width=330, font=('arial',8)).grid(row=4, column=0, sticky='WE')
        status=Label(self, textvariable=v_status, bd=1, relief=SUNKEN, anchor=W).grid(row=5, column=0, sticky='WE')

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
                return
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
                return
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
                diffdir=filePath3
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
    png = temp + basefile[0] + ".png"
    png = str(png)
    pdf = str(pdf)
    #print(pdf)
    #print(png)
    doc = fitz.open(pdf)
    xres=2
    yres=2
    mat= fitz.Matrix(xres,yres)
    for page in doc:
        pix = page.get_pixmap(matrix=mat, colorspace="rgb", alpha = False)
        pix.save(png)
    return png

def alignimage(align1,align2):
    img1 = cv2.imread(align1)
    img2 = cv2.imread(align2)

    #Find the corner points of img1
    h1,w1,c=img1.shape
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray1 = numpy.float32(gray1)
    dst1 = cv2.cornerHarris(gray1,5,3,0.04)
    ret1, dst1 = cv2.threshold(dst1,0.1*dst1.max(),255,0)
    dst1 = numpy.uint8(dst1)
    ret1, labels1, stats1, centroids1 = cv2.connectedComponentsWithStats(dst1)
    criteria1 = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
    corners1 = cv2.cornerSubPix(gray1,numpy.float32(centroids1),(5,5),(-1,-1),criteria1)

    #Find the corner points of img2
    h2,w2,c=img2.shape
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    gray2 = numpy.float32(gray2)
    dst2 = cv2.cornerHarris(gray2,5,3,0.04)
    ret2, dst2 = cv2.threshold(dst2,0.1*dst2.max(),255,0)
    dst2 = numpy.uint8(dst2)
    ret2, labels2, stats2, centroids2 = cv2.connectedComponentsWithStats(dst2)
    criteria2 = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
    corners2 = cv2.cornerSubPix(gray2,numpy.float32(centroids2),(5,5),(-1,-1),criteria2)


    #Find the top left, top right, and bottom left outer corners of the drawing frame for img1
    a1=[0,0]
    b1=[w1,0]
    c1=[0,h1]
    a1_dist=[]
    b1_dist=[]
    c1_dist=[]
    for i in corners1:
        temp_a1=math.sqrt((i[0]-a1[0])**2+(i[1]-a1[1])**2)
        temp_b1=math.sqrt((i[0]-b1[0])**2+(i[1]-b1[1])**2)
        temp_c1=math.sqrt((i[0]-c1[0])**2+(i[1]-c1[1])**2)
        a1_dist.append(temp_a1)
        b1_dist.append(temp_b1)
        c1_dist.append(temp_c1)

    #print("Image #1 (reference):")
    #print("Top Left:")
    #print(corners1[a1_dist.index(min(a1_dist))])
    #print("Top Right:")
    #print(corners1[b1_dist.index(min(b1_dist))])
    #print("Bottom Left:")
    #print(corners1[c1_dist.index(min(c1_dist))])

    #Find the top left, top right, and bottom left outer corners of the drawing frame for img2
    a2=[0,0]
    b2=[w2,0]
    c2=[0,h2]
    a2_dist=[]
    b2_dist=[]
    c2_dist=[]
    for i in corners2:
        temp_a2=math.sqrt((i[0]-a2[0])**2+(i[1]-a2[1])**2)
        temp_b2=math.sqrt((i[0]-b2[0])**2+(i[1]-b2[1])**2)
        temp_c2=math.sqrt((i[0]-c2[0])**2+(i[1]-c2[1])**2)
        a2_dist.append(temp_a2)
        b2_dist.append(temp_b2)
        c2_dist.append(temp_c2)

    #print("Image #2 (image to align):")
    #print("Top Left:")
    #print(corners2[a2_dist.index(min(a2_dist))])
    #print("Top Right:")
    #print(corners2[b2_dist.index(min(b2_dist))])
    #print("Bottom Left:")
    #print(corners2[c2_dist.index(min(c2_dist))])

    #Create the points for img1
    point1 = numpy.zeros((3,2), dtype=numpy.float32)
    point1[0][0]=corners1[a1_dist.index(min(a1_dist))][0]
    point1[0][1]=corners1[a1_dist.index(min(a1_dist))][1]
    point1[1][0]=corners1[b1_dist.index(min(b1_dist))][0]
    point1[1][1]=corners1[b1_dist.index(min(b1_dist))][1]
    point1[2][0]=corners1[c1_dist.index(min(c1_dist))][0]
    point1[2][1]=corners1[c1_dist.index(min(c1_dist))][1]

    #Create the points for img2
    point2 = numpy.zeros((3,2), dtype=numpy.float32)
    point2[0][0]=corners2[a2_dist.index(min(a2_dist))][0]
    point2[0][1]=corners2[a2_dist.index(min(a2_dist))][1]
    point2[1][0]=corners2[b2_dist.index(min(b2_dist))][0]
    point2[1][1]=corners2[b2_dist.index(min(b2_dist))][1]
    point2[2][0]=corners2[c2_dist.index(min(c2_dist))][0]
    point2[2][1]=corners2[c2_dist.index(min(c2_dist))][1]

    #Make sure points look ok:
    #print(point1)
    #print(point2)

    #Transform the image
    m = cv2.getAffineTransform(point2,point1)
    image2Reg = cv2.warpAffine(img2, m, (w1, h1), borderValue=(255,255,255))

    #Highlight found points in red:
    #img1[dst1>0.1*dst1.max()]=[0,0,255]
    #img2[dst2>0.1*dst2.max()]=[0,0,255]

    #Output the images:
    cv2.imwrite(align1, img1)
    #cv2.imwrite("output-img2-harris.jpg", img2)
    cv2.imwrite(align2,image2Reg)
    print("Images aligned successfully")
    return align1, align2
    
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
    return Image.frombytes(mode, size, a.reshape(len(a)*len(mode), 1).astype(numpy.uint8).tobytes())

def watermark_text(input_image_path,
                   output_image_path,
                   text, pos):
    photo = Image.open(input_image_path)
    drawing = ImageDraw.Draw(photo)
    red = (255, 0, 0)
    if platform == "win32":
        font = ImageFont.truetype("C:\\Windows\\Fonts\\Calibri.ttf", 30)
    else:
        font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", 30)
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
    global size_check, check
    start = timeit.default_timer()
    oldfiles = [f for f in listdir(olddir) if isfile(join(olddir,f))]
    newfiles = [n for n in listdir(newdir) if isfile(join(newdir,n))]
    pattern=re.compile('^([a-zA-Z])+')
    # The loop below attempts to match part numbers in the old folder and new folder. This is done
    # by dropping the first and last character and anything after an underscore. This is meant to 
    # match a XXXXXX-XXXXX.pdf numbering convention where the first and last digits are changed
    # to prototype status and revision level. This logic will need to be made more general to match
    # other part numbering schemes.
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
                        if platform == "win32":
                            filePath1 = olddir + "\\\\" + old_f
                            filePath2 = newdir + "\\\\" + new_f
                        else:
                            filePath1 = olddir + "/" + old_f
                            filePath2 = newdir + "/" + new_f
                        #print(filePath1)
                        img1_file = pdf2png(filePath1, tempdir)
                        img2_file = pdf2png(filePath2, tempdir)
                        if check.get() == 1:
                            align1, align2 = alignimage(img1_file, img2_file)
                            im1, im2 = Image.open(align2), Image.open(align1)
                        else:
                            im1, im2 = Image.open(img2_file), Image.open(img1_file)                
                        file_string = os.path.splitext(os.path.basename(new_f))[0] + "-diff.png"
                        if im1.size[0] == im2.size[0] and im1.size[1] == im2.size[1]:
                            print("Drawing sizes match")
                            if platform == "win32":
                                dispimg = tempdir + "\\\\" + file_string
                                waterimg = diffdir + "\\\\" + file_string
                            else:
                                dispimg = tempdir + "/" + file_string
                                waterimg = diffdir + "/" + file_string
                            anaglyph(im1, im2, color2_anaglyph).save(dispimg, quality=90)
                            watermark_text(dispimg,waterimg,"UNCONTROLLED COPY",pos=(0, 0))
                        else:
                            print("Drawing size mismatch.")
                            size_check = 1
                        del im1,im2
                        try:
                            if img1_file==img2_file:
                                os.remove(img1_file)
                            else:
                                os.remove(img1_file)
                                os.remove(img2_file)
                            os.remove(dispimg)
                        except:
                            print("Error while deleting temp files. Please check ", tempdir)

    stop = timeit.default_timer()
    print("Run time was", stop - start)
    print("Done")

def process_images():
    global filePath1, filePath2, v, check, size_check
    start = timeit.default_timer()
    img1_file = pdf2png(filePath1, tempdir)
    img2_file = pdf2png(filePath2, tempdir)
    if check.get() == 1:
        align1, align2 = alignimage(img1_file, img2_file)
        im1, im2 = Image.open(align2), Image.open(align1)
    else:
        im1, im2 = Image.open(img2_file), Image.open(img1_file)
    file_string = os.path.splitext(os.path.basename(filePath1))[0] + "-diff.png"
    if im1.size[0] == im2.size[0] and im1.size[1] == im2.size[1]:
        print("Drawing sizes match")
        if platform == "win32":
            dispimg = diffdir + "\\\\" + file_string
            waterimg = diffdir + "\\\\" + file_string
        else:
            dispimg = diffdir + "/" + file_string
            waterimg = diffdir + "/" + file_string
        anaglyph(im1, im2, color2_anaglyph).save(dispimg, quality=90)
        watermark_text(dispimg,waterimg,"UNCONTROLLED COPY",pos=(0, 0))
    else:
        print("Drawing size mismatch.")
        size_check = 1
    del im1,im2
    if img1_file == img2_file:
        os.remove(img1_file)
    else:
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
    root.option_add('*foreground', 'black')
    root.option_add('*activeForeground', 'white')
    root.wm_title("Choose images")
    app = DiffApp(master=root)
    app.mainloop()
    if v.get() == "2" and size_check != 1:
        complete_msg("Image Complete", "Image complete. Please check %s" % diffdir)
    if size_check == 1:
        error_msg("Drawing Error","A temp drawing failed to delete or there was a size mismatch. Please check output results.")


if __name__=='__main__':
    Main()
