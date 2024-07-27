import PySimpleGUI as sg
from cProfile import label
import math
#from imaplib import dat                #I suspect I typoed something important here, "dat" is used as a variable later
#from matplotlib import colors
 
 
 
#in progress, adapted from Java, VarySquare in Coevolution project
#some potentially useful methods have been left out as they were not needed here, but might be useful later
 
 
 
#ISSUES:   Dimensions of test square are messed up, my guess is the height/width has some sort of error in it
 
 
 
 
class vs:


    def __init__(self, xAx, yAx, lab, dat, maxx, nonlinearTransform="none"):
        #xp is two dimensional: [graph set][point within set]
        #yp is three dimensional: [graph set][point within set][actual value and std dev bounds]
        

        self.xAxis = xAx
        self.yAxis = yAx
        self.label = lab
        self.data = dat
        self.max = maxx
        self.nonlinearTransform = nonlinearTransform
        
        self.showValues = True
        
        can=sg.Canvas(size=(1200,1000), background_color='grey', key='canvas')
        layout = [[can]]
        self.window = sg.Window(label, layout, finalize=True)
        #self.bounds = sph.defaultBounds3
        vs.paintSquare(self,can)
        
        

 
    #defaultColors = ['white', 'red']
    defaultColors = [[255,255,255], [255,0,0]] #RGB because I couldn't get the color.rgb module to import in python


    
    
    def paintSquare(self, can):
        
        tkc=can.TKCanvas
        row = []
        row.append(tkc.create_rectangle(0,0, 1800, 1000, fill = "white"))
   
        xStart = 50;
        yStart = 80;
        width = 800;
        height = 800;
        numX = len(self.data[0])
        numY = len(self.data)
        xW = width/numX
        yW = height/numY
        
        print("xW: " + str(xW))
        print("yW: " + str(yW))
        
        baseColors = self.defaultColors
        
        tkc.create_text(xStart+200, yStart-50, text=self.label, fill="black", font=('Helvetica 8'))

         
        gradCap = self.max  #value that will show up as pure red from the gradient
         
        row.append(tkc.create_rectangle(xStart-1, yStart-1, width+2, height+2, outline = "black"))
        
        for y in range(numY):
            yPoint = yStart+height-(y+1)*yW
            for x in range(numX):
                xPoint = xStart+x*xW
                proportion = self.data[y][x]/gradCap
                if self.nonlinearTransform == "sqrt":
                    proportion = math.sqrt(proportion)
                #color = checkGradient(proportion, baseColors)
                color = multiColorGradient(proportion, colorPalette1())
                row.append(tkc.create_rectangle(xPoint, yPoint, xPoint+xW, yPoint+yW, fill = color))
                
                if self.showValues:
                    t = str(round(self.data[y][x],3))
                    tkc.create_text(xPoint+50, yPoint+50, text=t, fill="black", font=('Helvetica 8'))
                    if x == 0:
                        tx = str(self.yAxis[y])
                        tkc.create_text(xStart-20, yPoint+80, text=tx, fill="black", font=('Helvetica 8'))
                    if y == 0:
                        tx = str(self.xAxis[x])
                        tkc.create_text(xPoint+50, yStart+height+20, text=tx, fill="black", font=('Helvetica 8'))
    
    
def checkGradient(proportion, baseColors):

         
    if proportion < 0:
        proportion = 0;
    if proportion > 1:
        proportion = 1;
    
    c1 = baseColors[0]
    c2 = baseColors[1]
    c3 = [0,0,0]
    
    for i in range(3):
        c3[i] = math.floor((1-proportion)*c1[i]+(proportion)*c2[i])
        
    color = "#%02x%02x%02x" % (c3[0], c3[1], c3[2]) 
    return color
        

def multiColorGradient(proportion, colors):
    print("multiColorGradient called")
    #allows colors to shift in phases
    
    if proportion < 0:
        proportion = 0
    if proportion >= 1:
        proportion = 1
    
    print("proportion passed")
    numRegions = len(colors)-1
    region = (int)(proportion*numRegions)
    if region >= numRegions:
        region = numRegions-1 #makes sure if proportion = 1 we drop down
    newProp = proportion*numRegions-region
    rColors = [colors[region],colors[region+1]]
    return checkGradient(newProp, rColors)       


def colorPalette1():
    color1 = [255,255,0] #yellow
    color2 = [205,50,255] #magenta
    color3 = [0,0,255] #blue
    colors = [color1, color2, color3]
    return colors       
        
def testSquare():
        
    v = []
    for y in range(10):
        v.append([])
        for x in range(10):
            v[y].append(2000*x+8000*y)
    xAx = [0,10]
    yAx = [0,10]
    test = vs(xAx, yAx, "testSquare", v, 150000)
        

