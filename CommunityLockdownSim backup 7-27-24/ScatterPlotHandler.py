import PySimpleGUI as sg
 
 
 
#WARNING.  Default bounds and circle size are set to fullHistorymode
 
class sph:
    
    #[left, right, bottom, top]
    defaultBounds = [0,6,0,2]
    defaultBounds2 = [0,2500,0,2000] #for fullHistory
    defaultBounds2v3 = [0,500,0,1] #for fullHistory percent  
    defaultBounds3 = [0, 5,0,5] #for timeToExtinction
    defaultBounds4 = [0,5,0,100]
 
    def __init__(self, xP, yP, lab, many, setBounds=defaultBounds2, scatterName="CommunityLockdownSim ScatterPlot"):
        #xp is two dimensional: [graph set][point within set]
        #yp is three dimensional: [graph set][point within set][actual value and std dev bounds]
        
        self.label = lab
        
        self.multiple = many
        if many:
            self.xp = xP
            self.yp = yP
        else:
            self.xp = []
            self.xp.append(xP)
            self.yp = []
            self.yp.append(yP)
        self.label = lab
        can=sg.Canvas(size=(800,600), background_color='grey', key='canvas')
        layout = [[can]]
        self.window = sg.Window(scatterName, layout, finalize=True)
        self.bounds = sph.defaultBounds2
        
        if lab == "FullHistory Data":
            self.bounds = sph.defaultBounds2
            sph.paintScatter(self, can, True)
        else:
            self.bounds=setBounds
            sph.paintScatter(self, can, False)
 
    defaultColors = ['black', 'red', 'blue', 'cyan', 'green', 'magenta', 'gray', 'yellow']

    
    def paintScatter(self, can, tiny):
        tkc=can.TKCanvas
        width = 500
        height = 500
        xOffset = 20
        yOffset = 20
        cw = 7
        ch = 7
        
        if tiny:
            cw = 2   #for fullHistory
            ch = 2
        xScale = width/(self.bounds[1]-self.bounds[0])
        yScale = height/(self.bounds[3]-self.bounds[2])
        for i in range(len(self.xp)):
            if i < len(sph.defaultColors):
                color = sph.defaultColors[i]
            else:
                color = 'black'
            for j in range(len(self.xp[i])):
                #print("self.yp[i][j] " + str(self.yp[i][j]))
                x = (self.xp[i][j]-self.bounds[0])*xScale+xOffset
                y = yOffset+height-(self.yp[i][j][2]-self.bounds[2])*yScale #2 is actual data point, 0,1,3,4 are for error bars
                tkc.create_oval(x-cw,y-cw,x+cw,y+cw, fill = color)
        
        tkc.create_line(xOffset, yOffset, xOffset+width, yOffset) #top
        tkc.create_line(xOffset, yOffset+height, xOffset+width, yOffset+height) #bottom
        tkc.create_line(xOffset, yOffset, xOffset, yOffset+height) #left
        tkc.create_line(xOffset+width, yOffset, xOffset+width, yOffset+height) #right 
        tkc.create_text(xOffset,yOffset-10,fill="black",font="Times 10",
                        text=self.label)
        
        #add axes and labels
                