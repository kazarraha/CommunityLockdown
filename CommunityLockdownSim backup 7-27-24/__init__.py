import random
import itertools
import PySimpleGUI as sg
from random import choice
import math
import csv
import ScatterPlotHandler
from pickle import TRUE, FALSE
import UsefulStaticMethods
import VarySquare
import cProfile  #supposedly a profiler
from cmath import inf
import numpy as np
from numpy.random.mtrand import randint
import os
import time



#TODO:

#Redo infection measurements to separate hub communities from center so you can tell how much of
#kamiakTest6_Hub  InPerfect and OutPerfect results are actual meaningful changes 
#and how much are simply Simpson's paradox type things, artifacts of the hub community being unusually high or low on infections, and changing weight in the categories

#This should be doable without rerunning sims, each communities infections are already saved separately
#you just need a more sophisticated version of gridFileToLockPermCompare




#smallMode = True
kamiakMode = False
smallMode = False

locSpatial = True #locations have spatial coordinates and work/visit rates are higher for closer locations
adjustedInfRate = True
bev2 = True #changes how behavior works to be a small list of locations

largeWeight = 2

if smallMode:
    dmp = [5,5,5,50]  #default map parameters
else:
    #dmp = [5,50,100,500]
    dmp = [5,100,200,1000]  #WARNING, this makes the simulation incredibly slow, do some optimization

focusCommunity = 0 #if not smallMode, only this community displays



class Map:
    
    #currently around 189 contact events -> R0 = 1.89?
    #infChance = 0.008
    defaultImmuneDuration = 80
    defaultInfChance = 0.005
    #defaultComArrangement = "complete"
    #defaultComArrangement = "hubIn"
    defaultComArrangement = "hubOut"
    
    def __init__(self, nc, nw,nh, ac, seedNone, comArrangement = defaultComArrangement): #number of communities, work locations per community, home locations per community, agents per community
        self.baseImmuneDuration = Map.defaultImmuneDuration
        self.dayNumber = 0 #how many days have passed
        self.numCom = nc
        self.communities = []
        self.comArrangement = comArrangement
        #"complete" has all communities equidistant from each other
        #"clustered" has two groups that interact more internally
        #"hub" has one community in the center of a bunch of others
        
        self.infChance = 0.005
        if smallMode:
            self.infChance = 0.011
    
        for i in range(nc):
            com = Community(nw,nh,ac,i)
            self.communities.append(com)
        
        self.setComVisitRates(comArrangement)
            
        self.makeAllLocationList()
        self.fillAgentsV1(ac)
        if not seedNone:
            seedInitialInfections(self)
        self.tempStep = 0 #what time of day is it
        self.displayNumbers = False
        
        self.allLockdownLocations = []
        #print("new map created")
    
    def makeAllLocationList(self):
        self.allLocations = []
        for com in self.communities:
            for loc in com.locations:
                self.allLocations.append(loc)
    
    def setComVisitRates(self, comArrangement):
        clusterStrength = 4
        perfectCluster=True
        clusterBase = 1
        if perfectCluster:
            clusterBase = 0 #agents will obey the comArrangement perfectly, all visits are along graph lines
        self.comVisitRates = []
        for i in range(len(self.communities)):
            com = self.communities[i]
            vi = []
            for j in range(len(self.communities)):
                com2 = self.communities[j]
                if i == j:
                    vi.append(0)
                elif comArrangement=="clustered": #reverse bipartite.  communities are clustered in two halves which interact more strongly internally
                    if (i < len(self.communities)/2 and j < len(self.communities)/2) or (i >= len(self.communities)/2 and j >= len(self.communities)/2):
                        vi.append(clusterStrength)
                    else:
                        vi.append(clusterBase)
                elif comArrangement=="hubIn" or comArrangement=="hubOut": #one community in the center with spokes to other communities
                    hubIndex = 0 #lockdowns are applied nonrandomly in ascending order, so 0 gets locked down first, in this case, the hub center is the first to lockdown
                    if comArrangement == "hubOut": #in this case, the hub center is the last one to lockdown
                        hubIndex = self.numCom-1
                    if i==hubIndex:
                        vi.append(1) #hub connects everywhere equally
                    elif j == hubIndex: #the i!=0 should be unnecessary since that gets cutoff above, but it's here to be robust in case something changes later
                        vi.append(clusterStrength) #spokes connect strongly to hub
                    else:
                        vi.append(clusterBase) #spokes connect weakly or 0 to each other

                elif comArrangement=="complete":
                    vi.append(1)
                else:
                    print("warning, setComVisitRates passed invalid comArrangement: " + comArrangement)
                    vi.append(1)
            #UsefulStaticMethods.normalize(vi) #I believe normalizing is done automatically when making weighted random choices later
            self.comVisitRates.append(vi)
    
    
    def fillAgentsV1(self, ac):
        #assumes all communities and locations already exist
        self.allAgents = []
        commuterRate = 0.05
        numCommuter = math.floor(ac * commuterRate)
        

        if self.numCom < 2:
            numCommuter = 0
            
        #keep numCommuters the same, have comArrangement set weights on which communities are chosen by each commuter
        #and also weight visits in self.assignBehaviorLocSpatial2
        #should be able to keep the same method and not need a v3 since current behavior is preserved by "complete" graph
            
        self.monitorCount = 0    
        
        for com in self.communities:
            agentsPerHome = ac/len(com.homes)
            for j in range(ac):
                agent = Agent(self)
                agent.name = [com.name,j]
                com.agents.append(agent)
                self.allAgents.append(agent)
                agent.home = com.homes[int(j/agentsPerHome)]
                agent.homeCom = com
                #temp monitoring system  7-8-24
                agent.monitor = False
                if self.monitorCount > 0:
                    agent.monitor = True
                    self.monitorCount = self.monitorCount - 1
                #
                
            #assign behaviors to agents
            for agent in random.sample(com.agents, numCommuter):
                agent.commuter = True
            if not locSpatial:
                self.assignBehaviorV1(com)
            else:
                if bev2:
                    self.assignBehaviorLocSpatial2(com)
                else:
                    self.assignBehaviorLocSpatial(com)

    
    def assignBehaviorLocSpatial2(self,com):
        #v2 assigns a fixed number of locations to agents to visit, which massively saves computing time
        #and gives agents a more well-defined social network
        
        #note, this does not define the agent.behavior parameter, make sure all simulations called after this
        #know bev2 is true and act accordingly
        
        
        #assign weights to locations with weight inversely proportional to distance from agent's home
        #chooses 10 locations to sometimes visit with same weights, but once chosen all are equally likely
        

        
        numVisit = 9
        
        workProb = 0.8 #agent is at work during day shift
        visitProb = 0.25 #agent is in another community during day shift
        homeProb = 0.2 #agent is at home during afternoon shift
        denomBonus = 0.01 #prevents asymptotically huge weights for close locations, increase to decrease influence of distance
        effectiveComSize = len(com.locations)+largeWeight*com.numLarge #be careful, this requires all communities have the same number of large locations (pre-lockdown)
        
        
        defaultVisitWeights = [] #for when people are visiting other communities not their own
        for comI in self.communities:
            v = []
            for loc in comI.works:
                if loc.large:
                    v.append(largeWeight)
                else:
                    v.append(1)
            defaultVisitWeights.append(v)
        
        
        if not locSpatial:
            print("WARNING, Map.assignBehaviorLocSpatial2 was called despite locSpatial set to False")
        if not bev2:
            print("WARNING, Map.assignBehaviorLocSpatial2 was called despite bev2 set to False")
        for agent in com.agents:
            workWeights = []
            for loc in com.works:
                multiplier = 1
                if loc.large:
                    multiplier = largeWeight
                d = UsefulStaticMethods.distance(agent.home.spatial,loc.spatial)
                workWeights.append(multiplier/(d+denomBonus))
            UsefulStaticMethods.normalize(workWeights)
            if not agent.commuter:
                agent.work = random.choices(com.works, workWeights)[0]
                
            #WORKING HERE 7-2-24
            #update this based on community distances from each other
            else:
                #otherCom = choice_excluding(self.communities, com) #old code, equivalent to comArrangement="complete"
                i = self.communities.index(agent.homeCom)
                otherCom = random.choices(self.communities, weights=self.comVisitRates[i])[0] #comArrangement is applied here in comVisitRates
                
                
                #newWorkWeights = []
                #for loc in otherCom.works:
                #    if loc.large:
                #        newWorkWeights.append(largeWeight)
                #    else:
                #        newWorkWeights.append(1)
                #agent.work = random.choices(otherCom.works, newWorkWeights)[0]
                agent.work = random.choices(otherCom.works, defaultVisitWeights[self.communities.index(otherCom)])[0]
            
            #old code from pre-comArrangement  
            #visitWeights = [] #for not working, requires workWeights already normalized
            #for i in range(len(self.allLocations)):
            
            #    loc = self.allLocations[i]
            #    if loc.home:
            #        visitWeights.append(0)
            #    elif loc in com.works: #works in the agent's own community
            #        visitWeights.append(workWeights[com.works.index(loc)])
            #    else: #works in another community
                    #WORKING HERE 7-2-24
                    #I'm not convinced this is weighting locations in own community versus other communities appropriately
                    #double check that
                    #also change to update with respect to new community configurations
                    
            #        multiplier = 1
            #        if loc.large:
            #            multiplier = largeWeight
            #        visitWeights.append(multiplier/(effectiveComSize*(self.numCom-1)))
            #agent.visitLocs = random.choices(self.allLocations, weights = visitWeights, k = numVisit)

            
            agent.visitLocs = []
            numOut1 = 0
            for i in range(numVisit):
                if random.random() < visitProb:
                    numOut1 += 1
                    otherCom = random.choices(self.communities, weights=self.comVisitRates[self.communities.index(com)])[0]
                    loc = random.choices(otherCom.works, defaultVisitWeights[self.communities.index(otherCom)])[0]
                    agent.visitLocs.append(loc)
                else:
                    loc = random.choices(com.works, workWeights)[0]
                    agent.visitLocs.append(loc)
            
            #temp monitoring code
            if agent.monitor:
                numOut2 = 0
                for loc in agent.visitLocs:
                    if loc.community != com:
                        numOut2 += 1
                print("numOut1: " + str(numOut1))
                print("numOut2: " + str(numOut2))
            agent.visitLocs.append(agent.home)
    
    def tempVisitWeightSums(self, agent, visitWeights):
        sumOut = 0
        sumIn = 0
        for i in range(len(visitWeights)):
            loc = self.allLocations[i]
            if loc.community == agent.homeCom:
                sumIn += visitWeights[i]
            else:
                sumOut += visitWeights[i]
        
        print("Sum internal: " + str(sumIn) + "  Sum External: " + str(sumOut))
        
    
    def assignBehaviorLocSpatial(self,com):
        #assigns works to agents and visiting rates inversely proportional to the spatial distance
        #from their house to the work location
        workProb = 0.8 #agent is at work during day shift
        visitProb = 0.05 #agent is in another community during day shift
        homeProb = 0.2 #agent is at home during afternoon shift
        denomBonus = 0.01 #prevents asymptotically huge weights for close locations, increase to decrease influence of distance
        effectiveComSize = len(com.locations)+largeWeight*com.numLarge #be careful, this requires all communities have the same number of large locations (pre-lockdown)
        
        if not locSpatial:
            print("WARNING, Map.assignBehaviorLocSpatial was called despite locSpatial set to False")
        for agent in com.agents:
            workWeights = []
            for loc in com.works:
                multiplier = 1
                if loc.large:
                    multiplier = largeWeight
                d = UsefulStaticMethods.distance(agent.home.spatial,loc.spatial)
                workWeights.append(multiplier/(d+denomBonus))
            UsefulStaticMethods.normalize(workWeights)
            if not agent.commuter:
                agent.work = random.choices(com.works, workWeights)[0]
            else:
                otherCom = choice_excluding(self.communities, com)
                newWorkWeights = []
                for loc in otherCom.works:
                    if loc.large:
                        newWorkWeights.append(largeWeight)
                    else:
                        newWorkWeights.append(1)
                agent.work = random.choices(otherCom.works, newWorkWeights)[0]
            visitWeights = [] #for not working, requires workWeights already normalized
            for i in range(len(self.allLocations)):
                loc = self.allLocations[i]
                if loc.home:
                    visitWeights.append(0)
                elif loc in com.works:
                    visitWeights.append(workWeights[com.works.index(loc)])
                else:
                    multiplier = 1
                    if loc.large:
                        multiplier = largeWeight
                    visitWeights.append(multiplier/(effectiveComSize*(self.numCom-1)))

                
            dayShift = []
            aftShift = []
            Shift = []
            for i in range(len(self.allLocations)):
                loc = self.allLocations[i]
                #print("The variable, workProb is of type:", type(workProb))
                #print("The variable, visitProb is of type:", type(visitProb))
                #print("The variable, visitWeights[i] is of type:", type(visitWeights[i]))
                
                if agent.home == loc:
                    dayShift.append(0)
                    aftShift.append(homeProb)
                    Shift.append(1)
                elif agent.work == loc:
                    dayShift.append(workProb)
                    if loc.community == com:
                        aftShift.append((1-homeProb)*(1-visitProb)*visitWeights[i])
                    else:
                        aftShift.append((1-homeProb)*visitProb*visitWeights[i])
                    Shift.append(0)
                elif loc.home:
                    dayShift.append(0)
                    aftShift.append(0)
                    Shift.append(0)
                elif loc.community == com:
                    dayShift.append((1-workProb)*(1-visitProb)*visitWeights[i])
                    aftShift.append((1-homeProb)*(1-visitProb)*visitWeights[i])
                    Shift.append(0)
                else:
                    dayShift.append((1-workProb)*(visitProb)*visitWeights[i])
                    aftShift.append((1-homeProb)*(visitProb)*visitWeights[i])
                    Shift.append(0)
                    
                    
                #double check these, not sure they're entirely correct
            UsefulStaticMethods.normalize(dayShift)
            UsefulStaticMethods.normalize(aftShift)
            agent.behavior = [dayShift,aftShift,Shift]
            
            
            #bugtesting
            #if com.agents.index(agent)==0:
            #    print("Caution!  Make sure visit rates for locations in com never go below rates for individual locations in other coms")
            #    print("consider removing explicit visits and just having distances to other coms")
            #    hom = agent.home
            #    print("home (" + str(hom.spatial[0])+","+str(hom.spatial[1])+")")
            #    for i in range(len(self.allLocations)):
            #        loc = self.allLocations[i]
            #        if loc.home or loc.large:
            #            continue
            #        if loc.community != com:
            #            if not loc.large:
            #                print("nonlocal aftShift: " + str(aftShift[i]))
            #            continue
            #        dist = UsefulStaticMethods.distance(hom.spatial,loc.spatial)
            #        print("loc (" + str(loc.spatial[0])+","+str(loc.spatial[1])+") dist: "+str(dist)+" visitWeight "+ str(visitWeights[i])+ " aftShift: " + str(aftShift[i]))
            

            
            
            #this should be complete, but test it first to make sure there aren't bugs
        
        
    
    def assignBehaviorV1(self, com):
            workProb = 0.8 #agent is at work during day shift
            dayVisitProb = 0.1 #agent is in another community during day shift
            inComProbSmall = (1-workProb)*(1-dayVisitProb)/(len(com.works)-1+com.numLarge) #agent is at a particular location in com during day shift
            inComProbLarge = (1-workProb)*(1-dayVisitProb)/(len(com.works)-largeWeight+com.numLarge) #if agent's own work location is large, then denominator needs to be smaller since possible visits have less weight
            
            outComProb = 0
            if self.numCom > 1:
                outComProb = (1-workProb)*dayVisitProb/((self.numCom - 1)*(len(com.works)+com.numLarge))
            #WARNING, the above formula only works if all communities have the same number of works
            
            homeProb = 0.2 #agent is at home during afternoon shift
            afterVisitProb = 0.1 #agent is in another community during afternoon shift
            inAfternoonProb = (1-homeProb)*(1-afterVisitProb)/len(com.works) #agent is at a particular location during afternoon shift    
            outAfternoonProb = 0
            if self.numCom > 1:
                outAfternoonProb = (1-homeProb)*afterVisitProb/(self.numCom-1)/len(com.works) 
            
            #morning: own work or random work
            #afternoon: home or random work
            #: home
                
            workWeights = []
            for loc in com.works:
                if loc.large:
                    workWeights.append(largeWeight)
                else:
                    workWeights.append(1)
            
            for agent in com.agents:
                dayShift = []
                aftShift = []
                Shift = []
                if not agent.commuter:
                    agent.work = random.choices(com.works, workWeights)[0]
                    #agent.work = random.choice(com.works)
                else:
                    otherCom = choice_excluding(self.communities, com)
                    agent.work = random.choice(otherCom.works)
                 
                inComProb = inComProbSmall
                if agent.work.large:
                    inComProb = inComProbLarge #pedantic detail to make sure weights are correct for daytime visits
                

                for loc in self.allLocations:
                    if agent.home == loc:
                        dayShift.append(0)
                        aftShift.append(homeProb)
                        Shift.append(1)
                    elif agent.work == loc:
                        dayShift.append(workProb)
                        if loc.community == com:
                            aftShift.append(inAfternoonProb)
                        else:
                            aftShift.append(outAfternoonProb)
                        Shift.append(0)
                    else:
                        Shift.append(0)
                        if loc.home:
                            dayShift.append(0)
                            aftShift.append(0)
                        else:
                            if loc.community == com:
                                dayShift.append(inComProb)
                                aftShift.append(inAfternoonProb)
                            else:
                                dayShift.append(outComProb)
                                aftShift.append(outAfternoonProb)
                        if loc.large:
                            aftShift[len(aftShift)-1] *= 2
                            if agent.work != loc:
                                dayShift[len(dayShift)-1] *= 2
                agent.behavior.append(dayShift)
                agent.behavior.append(aftShift)
                agent.behavior.append(Shift)
                
    def getComInfectionsLoc(self): #old version, gets infections per location
        list = []
        for com in self.communities:
            comInf = 0
            for loc in com.locations:
                comInf += loc.sumInfections
            list.append(comInf)
        return list
    
    def getComInfections(self):
        list = []
        for com in self.communities:
            comInf = 0
            for agent in com.agents:
                comInf += agent.sumInfections
            list.append(comInf)
        return list
    
    def getSumInfections(self):
        comInf = self.getComInfections()
        sum = 0
        for c in comInf:
            sum += c
        return sum
    
    def getSumInfectionsBreakdown(self, numLock):
        comInf = self.getComInfections()
        sumLock = 0
        sumPerm = 0
        sum = 0
        for i in range(len(comInf)):
            c = comInf[i]
            sum += c
            if i < numLock:
                sumLock += c
            else:
                sumPerm += c
        breakdown = [sum, sumLock, sumPerm]
        return breakdown
        
      
    def setParameters(self, inf, immune, numLock):  
        self.infChance = inf
        self.baseImmuneDuration = immune
        for i in range(numLock):
            homeLockdown(self, self.communities[i])
      
        
class Community:
    
    def __init__(self, nw,nh, ac, name):
        self.comLoc = nw+nh
        self.agentCom = ac
        self.locations = []
        self.agents = []
        self.homes = []
        self.agents = [] #agents who live here
        self.comPAgents = [] #agents who are present here (live - visitors leaving + visiting coming) 
        self.works = []
        self.name = name
        self.lockdown = FALSE
        
        
        self.numLarge = 1
        if not smallMode:
            self.numLarge = 5
        
        
        for j in range(self.comLoc):
            loc = Location(self)
            self.locations.append(loc)
            if j < self.numLarge:
                loc.large = True
            if j >= nw:
                loc.home = True
                self.homes.append(loc)
            else:
                self.works.append(loc)
        
    
                

class Agent:
    
    infectedDuration = 14
    #baseImmuneDuration = 50
    if smallMode:
        infectedDuration = 7
        immuneDuration = 8
    
    
    def __init__(self, m):
        #backref
        self.mapp = m
        
        #fixed parameters
        self.home = None
        self.homeCom = None
        self.work = None
        self.behavior = []
        self.name = None
        self.commuter = False
        
        #variable
        self.infected = False
        self.exposed = False
        self.recoveryTime = 0
        self.visiting = False
        
        self.immune = 0
        
        self.sumInfections = 0

            
    
    def infect(self):
        self.infected = True
        self.recoveryTime = Agent.infectedDuration
        self.sumInfections += 1

    def immuneDuration(self, baseImmuneDuration):
        #return random.randint(Agent.baseImmuneDuration, 2*Agent.baseImmuneDuration)
        #output = random.randint(baseImmuneDuration, 2*baseImmuneDuration)
        output = random.randint(math.floor(baseImmuneDuration * 0.9), math.floor(baseImmuneDuration * 1.1))
        #print("immuneDuration: " + str(output))
        return output
    
    def timeTick(self, mapp):
        if self.immune > 0:
            self.immune -= 1
        if self.infected:
            self.recoveryTime -= 1
            if self.recoveryTime <= 0:
                self.infected = False
                self.immune = self.immuneDuration(mapp.baseImmuneDuration)
        elif self.exposed == True:
            self.infect()
        self.exposed = False
            
    def nameToString(self):
        if self.name == None:
            return "none"
        else:
            return str(self.name[0])+"-"+str(self.name[1])
    

class Location:
    def __init__(self, com):
        self.home = False
        self.presentAgents = []
        self.community = com
        self.large = False
        
        #variables
        self.sumInfections = 0 #all infections since time started
        self.rollingInfections = 0 #approximate average infections per day, weighted more towards recency
        self.rollingInfectionRate = 100
        #not certain the rolling average is the way to go long term, but gives ballpark answer for now
        
        if locSpatial: #assign a random location in a [0,1] x [0,1] square
            self.spatial = [random.random(),random.random()]
        
        
    def incInfections(self, num):
        self.sumInfections += num
        self.rollingInfections += num/self.rollingInfectionRate
        
    def timeTick(self):
        self.rollingInfections *= (1 - 1/self.rollingInfectionRate)
        
        
        
    
def makeWindow(mapp):
    
    #can=sg.Canvas(size=(800,600), background_color='grey', key='canvas')
    can=sg.Canvas(size=(1500,800), background_color='grey', key='canvas')
    layout = [[sg.Button("simDay")], [sg.Button("simStep")], [sg.Button("reset")],[sg.Button("action")],[sg.Button("simDayx10")],[can]]
    window = sg.Window("Community Lockdown Sim", layout, finalize=True)

    
    
    #fig = [tkc.create_rectangle(100, 100, 600, 400, outline='white'),
    #   tkc.create_line(50, 50, 650, 450, fill='red', width=5),
    #   tkc.create_oval(150,150,550,350, fill='blue'),
    #   tkc.create_text(350, 250, text="Sierra is a Sneep Snorp",
    #   fill='white', font=('Arial Bold', 16)),
    #]
    hackPaint(can, mapp)
    
    while True:
        event, values = window.read()
        if event == "OK" or event == sg.WIN_CLOSED:
            break
        if event == "simDay":
            simDay(mapp)
            hackPaint(can, mapp)
        if event == "simDayx10":
            for i in range(10):
                simDay(mapp)
            hackPaint(can, mapp)
        if event == "simStep":
            simStep(mapp)
            hackPaint(can, mapp)
        if event == "reset":
            mapp = Map(mapp.numCom, len(mapp.communities[0].works),len(mapp.communities[0].homes), mapp.communities[0].agentCom, False)
            hackPaint(can, mapp)
        if event == "action":
            action(can, mapp)
            hackPaint(can, mapp)
    window.close()

def action(can, mapp):
    #actionpaction
    if True:
        #basicLockdownSimAndSave("lockdownSave3")
        #loadAndDisplay1("lockdownSave3")
        
        #fullHistoryLockdownTest(2, 10000, "fullHistorySaveC-180-0.003")
        #loadAndDisplay2("fullHistorySaveB1-65")
        
        
        #fullHistoryLockdownRepeat([0.003, 365, 3], 10000, "fullHistoryRepeat-3-365-0.003-v4")
        #fullHistoryLockdownRepeat([0.012, 365, 3], 10000, "fullHistoryRepeat-3-365-0.012-v4")
        #loadAndDisplay2v2(["fullHistoryRepeat-3-365-0.003-v4","fullHistoryRepeat-3-365-0.012-v4"])
        #loadAndDisplay2v3(["fullHistoryRepeat-3-365-0.003-v4-percentComplete","fullHistoryRepeat-3-365-0.012-v4-percentComplete"])
        
        
        #timeToExtinctionTest("timeToExtinctionSaveL1")
        #loadAndDisplay3("timeToExtinctionSaveL1")
        #timeToExtinctionTest("timeToExtinctionSaveB3-65")
        #loadAndDisplay3("timeToExtinctionSaveB3-65")
    
        #initialToEndemic("initialToEndemicSave1")
        #initialToEndemicSpecial("initialToEndemicSpecialBev1")
        #loadAndDisplay4("initialToEndemicSpecial3")
        #loadAndDisplay4("initialToEndemicSpecialBev1")
        
        #for i in range(6):
        #    hackR0EstimatorTest(i)
        #hackR0EstimatorTest(0)

        
        #tempProfileTest()
        
        #tempCollateDataTest()
        #timeToExtinctionImmuneTest("timeToExtinctionImmuneTestB3")
        #timeToExtinctionGrid("timeToExtinctionGridBreakdownLinear")
        #timeToExtinctionGrid("CompleteArrangementTest1")
        #timeToExtinctionGrid("HubArrangementTest1")
        
        
        #VarySquare.testSquare()
        #VarySquareLoader("kamiakTest3permInf")
        #VarySquareLoader("timeToExtinctionGridBreakdown3inf")
        #VarySquareLoader("timeToExtinctionGridBreakdownLinearinf")
        #VarySquareLoader("kamiakTest4lockInf", extraNormalizer="lock")
        
        #graphInfLockProjection("kamiakTest5_butterySmoothinf")
        #graphInfLockProjection("kamiakTest6Hubinf")
        #graphInfLockProjection("CompleteArrangementTest1inf",num=1)
        #graphInfLockProjection("kamiakTest4permInf")
        
        #gridFileToLockPermCompare("kamiakTest4lockInf", "kamiakTest4permInf")
        gridFileToLockPermCompare("kamiakTest6_HubInPerfectlockInf", "kamiakTest6_HubInPerfectpermInf")
        gridFileToLockPermCompare("kamiakTest6_HubOutPerfectlockInf", "kamiakTest6_HubOutPerfectpermInf")
        
        

def hackPaint(can, mapp):
    
    if locSpatial:
        hackPaintSpatial(can,mapp)
        return
    
    tkc=can.TKCanvas
    tkc.delete('all')
    size = 60 #squares representing communities
    inc = size+8
    cSize = 8 #circles representing agents
    cInc = cSize+2
    rec = []
    circ = []
    ofn = 5 #overflow number for agents in each row
    ofy = cInc
    
    displayRolling = True
    focusRow = 15
    
    
    for i in range(len(mapp.communities)):
        if(not smallMode and i != focusCommunity):
            continue
        com = mapp.communities[i]
        yBase = inc/2+inc*i*1.5
        row = []
        for j in range(len(com.locations)):
            y = yBase
            rollOver = 0
            if not smallMode:
                rollOver = math.floor(j/focusRow)
                y = inc/2+inc*rollOver*1.5
            loc = com.locations[j]
            x = inc/2+inc*(j-rollOver*focusRow)
            color = 'white'
            if loc.home:
                color = 'black'
            tSize = size
            if loc.large:
                tSize = size+4
                color = 'blue'
            if displayRolling:
                t = str(round(loc.rollingInfections,2))
                tkc.create_text(x+4, y-7, text=t, fill="black", font=('Helvetica 8'))
            row.append(tkc.create_rectangle(x,y, x+tSize, y+tSize, outline = color))
            for k in range(len(loc.presentAgents)):
                agent = loc.presentAgents[k]
                rn = math.floor(k/ofn) #row number
                ya = y+cInc/2+rn*ofy
                xa = x+cInc/4+cInc*(k-rn*ofn)  #update this to handle overflow
                color = 'blue'
                if agent.immune > 0:
                    color = 'cyan'
                if agent.infected:
                    color = 'green'
                oColor = 'black'
                if agent.home.community != com:
                    oColor = 'red'
                circ.append(tkc.create_oval(xa,ya,xa+cSize,ya+cSize, fill = color, outline = oColor))
                if mapp.displayNumbers:
                    t = agent.name[1]
                    tkc.create_text(xa+4, ya-5, text=t, fill="black", font=('Helvetica 8'))
        rec.append(row) 


def hackPaintSpatial(can, mapp):
    
    if not locSpatial:
        print("WARNING, hackPaintSpatial called but locSpatial = False")
    
    left = 50
    top = 50
    width = 600
    height = 600
        
    tkc=can.TKCanvas
    tkc.delete('all')
    size = 60 #squares representing communities
    cSize = 8 #circles representing agents
    cInc = cSize+2
    rec = []
    circ = []
    ofn = 5 #overflow number for agents in each row
    ofy = cInc
    
    focusCommunity = 0
    
    
    
    com = mapp.communities[focusCommunity]
    focusAgentIndex = 0
    if focusAgentIndex >= 0:
        fa = com.agents[focusAgentIndex]
    row = []
    for j in range(len(com.locations)):
        loc = com.locations[j]
        y = int(top + (1-loc.spatial[1])*height-size/2)
        x = int(left+loc.spatial[0]*width-size/2)

        color = 'white'
        if loc.home:
            color = 'black'
        tSize = size
        if loc.large:
            tSize = size+4
            color = 'blue'
        row.append(tkc.create_rectangle(x,y, x+tSize, y+tSize, outline = color))
        for k in range(len(loc.presentAgents)):
            agent = loc.presentAgents[k]
            rn = math.floor(k/ofn) #row number
            ya = y+cInc/2+rn*ofy
            xa = x+cInc/4+cInc*(k-rn*ofn)  #update this to handle overflow
            color = 'blue'
            if agent.immune > 0:
                color = 'cyan'
            if agent.infected:
                color = 'green'
            oColor = 'black'
            if agent.home.community != com:
                oColor = 'red'
            if focusAgentIndex >= 0:
                if agent == fa:
                    color = 'yellow'
            circ.append(tkc.create_oval(xa,ya,xa+cSize,ya+cSize, fill = color, outline = oColor))
            if mapp.displayNumbers:
                t = agent.name[1]
                tkc.create_text(xa+4, ya-5, text=t, fill="black", font=('Helvetica 8'))
        if focusAgentIndex >= 0 and not loc.home and not loc.large and not bev2:
            t = str(fa.behavior[1][mapp.allLocations.index(loc)])
            tkc.create_text(x+4, y-8, text=t, fill="black", font=('Helvetica 8'))

                  
    rec.append(row)   

    
def simDay(mapp):
    #if mapp.dayNumber % 10 == 0:
    #    print("day " + str(mapp.dayNumber)+" inf: " + str(mapp.getSumInfections()))
    if not bev2:
        simTime(mapp, 0) #day shift
        simTime(mapp, 1) #afternoon shift
        simTime(mapp, 2) # shift
    else:
        simTime2(mapp, 0) #day shift
        simTime2(mapp, 1) #afternoon shift
        simTime2(mapp, 2) # shift
    newDay(mapp)
    

    
    
def simStep(mapp):
    if mapp.tempStep < 3:
        if not bev2:
            simTime(mapp, mapp.tempStep)
        else:
            simTime2(mapp, mapp.tempStep)
        mapp.tempStep += 1
    else:
        newDay(mapp)
        mapp.tempStep = 0

def simTime(mapp, shift):
    resetLocations(mapp)
    for agent in mapp.allAgents:
        loc = random.choices(mapp.allLocations, agent.behavior[shift])[0]
        loc.presentAgents.append(agent)
        loc.community.comPAgents.append(agent)        
    for com in mapp.communities:
        simCom(com, shift, mapp)
   
def simTime2(mapp, shift):
    #using bev2, agent visits are restricted to specific locations
    #only calls random.choice when needed for visits, and only on a smaller set
    
    assignLocations2(mapp, shift)        
    for com in mapp.communities:
        simCom(com, shift, mapp)
            
def assignLocations2(mapp, shift):
    resetLocations(mapp)
    for agent in mapp.allAgents:
        loc = 0
        if shift == 0:
            if random.random() < 0.8:
                loc = agent.work
            else:
                loc = random.choice(agent.visitLocs)
        if shift == 1:
            loc = random.choice(agent.visitLocs)
        if shift == 2:
            loc = agent.home
        loc.presentAgents.append(agent)
        loc.community.comPAgents.append(agent)    
    for loc in mapp.allLockdownLocations: #quick hack, there is likely a more efficient way to avoid putting people in these to begin with
        for agent in loc.presentAgents:
            agent.home.presentAgents.append(agent)
            loc.presentAgents.remove(agent)
            if loc.community != agent.home.community:
                loc.community.comPAgents.remove(agent)
                agent.home.community.comPAgents.append(agent)     


def simCom(com, shift, mapp):
    #for agent in com.agents, place agents into locations randomly based on behavior
    #simulate disease spread within each location
    for loc in com.locations:
        for pair in itertools.permutations(loc.presentAgents, 2):
            infect = infectionChance(pair, mapp)
            if infect:
                loc.incInfections(1)



def resetLocations(mapp):
    for com in mapp.communities:
        com.comPAgents = []
        for loc in com.locations:
            loc.presentAgents = []

def decision(probability):
    return random.random() < probability

def infectionChance(pair, mapp):
    if(pair[0].infected):
        if(pair[1].immune <= 0 and not pair[1].infected):
            if decision(mapp.infChance):
                pair[1].exposed = True
                #print("Agent "+str(pair[0].name[1])+" infected " + str(pair[1].name[1]))
                return True
    return False
    
def seedInitialInfections(mapp):
    numInf = int(len(mapp.communities[0].agents)/5)
    if not smallMode:
        numInf = 5
    for com in mapp.communities: 
        infectors = random.sample(com.agents, numInf)
        numImmune = numInf
        if not smallMode:
            numImmune = int(math.floor(len(com.agents)/4))
        hackImmune = random.sample(com.agents, numImmune)
        immuneDuration = 10
        for agent in infectors:
            Agent.infect(agent)
        for agent in hackImmune:
            if not agent.infected:
                if smallMode:
                    agent.immune = agent.immuneDuration(mapp.baseImmuneDuration)
                else:
                    agent.immune = immuneDuration
                    immuneDuration = immuneDuration +5
                
def seedOneInfection(mapp):
    agent = random.choice(mapp.allAgents)
    Agent.infect(agent)
            
def newDay(mapp):
    for com in mapp.communities:
        for agent in com.agents:
            agent.timeTick(mapp)
        for loc in com.locations:
            loc.timeTick()
    mapp.dayNumber += 1
            
def defaultMap():
    return Map(dmp[0],dmp[1],dmp[2],dmp[3], False)

def singleInfMap():
    mapp = Map(dmp[0],dmp[1],dmp[2],dmp[3],True)
    seedOneInfection(mapp)
    return mapp
    
def singleInfMapType(type, numLock):
    #0: lockdown community works at small location, 1: lockdown worked at large
    #2: permissive works at small, 3: permissive works at large
    
    
    #TODO:  change the random agent sampling to iteratively attempt agents in index order
    #(which is allowed without loss of generality)
    #and regenerate map if this fails
    
    comIndex = -1
    if type in [0,1,5,6]:
        if numLock == 0:
            print("WARNING, singleInfMapType passed type " + str(type)+" numLock: " + str(numLock))
        comIndex = 0
    if type in [2,3,6,7]:
        if numLock == 5:
            print("WARNING, singleInfMapType passed type " + str(type)+" numLock: " + str(numLock))
        comIndex = dmp[0]-1 #last community is the last to lock down
    large = False
    if (type % 2) == 1:
        large = True
    oppositeCommute = False
    if type in [4,5,6,7]:
        oppositeCommute = True
    
    maxTries = 50
    tries = 0
    go = True



    while go:
        mapp = Map(dmp[0],dmp[1],dmp[2],dmp[3],True)
        for i in range(numLock):
            homeLockdown(mapp, mapp.communities[i])
        com = mapp.communities[comIndex]
        #testing all agents in index order should be effectively random WLOG, but shuffle just in case
        random.shuffle(com.agents)
        for agent in com.agents: 
        #print("agent " + str(com.agents.index(agent)) + " rolled")
        #print("agent.commuter: " + str(agent.commuter)
            if agent.work.large == large:
                opposite = True
                if com.lockdown == agent.work.community.lockdown:
                    opposite = False
                if oppositeCommute == opposite:
                    Agent.infect(agent)
                    return mapp #this succeeds, anything else that exits loops is a failure
                
        #if you get here, that means no agents in the community were valid.  reroll map
        tries += 1
        if tries > maxTries:
            go = False
            print("Warning, singleInfMapType failed to find agent of appropriate type in 50 map generations")
            print("numLock: " + str(numLock) + " type: " + str(type))
    return []    
    
def homeLockdown(mapp, lockCom):
    #all large locations are closed, all agents who would go to one go home instead
    for loc in [l for l in lockCom.locations if l.large]:
        i = mapp.allLocations.index(loc)
        if not bev2:
            for agent in mapp.allAgents:
                j = mapp.allLocations.index(agent.home)
                for k in range(len(agent.behavior)):
                    agent.behavior[k][j] += agent.behavior[k][i]
                    agent.behavior[k][i] = 0
        mapp.allLockdownLocations.append(loc)
    lockCom.lockdown = True


def checkExtinction(mapp):
    for agent in mapp.allAgents:
        if agent.infected:
            return False
    return True
        

#useful static stuff
#TODO, figure out how to make this a separate .py file, ActionManager
  


def choice_excluding(list, exception):
    possible_choices = [v for v in list if v != exception]
    return random.choice(possible_choices)



def basicLockdownTest(numLock, numDaysPre, numDays):
    mapp = defaultMap()
    extinct = False
    data = []
    for i in range(numLock):
        homeLockdown(mapp, mapp.communities[i])
    for i in range(numDaysPre):
        simDay(mapp)
    preInf = mapp.getComInfections()
    for i in range(numDays):
        simDay(mapp)
        if i%100 == 0:
            if not extinct and checkExtinction(mapp):
                print("Infection went extinct around t = " + str(i))
                extinct = True
        if i%1000==0:
            print("Simtime: " + str(i))
    postInf = mapp.getComInfections()
    for c in range(len(postInf)):
        avg = str((postInf[c]-preInf[c])/numDays)
        if extinct:
            avg += "*"
        print("There were an average of " + avg + " infections per day in community " + str(c))
        data.append(avg)
    
    return data

def fullHistoryLockdownTest(parameterPack, numDays, name):
    mapp = defaultMap()
    print("fullHistoryLockdown Test, parameters set: " + str(parameterPack[0])+","+str(parameterPack[1])+","+str(parameterPack[2]))
    mapp.setParameters(parameterPack[0], parameterPack[1], parameterPack[2]) #infection rate, immune duration, number of lockdown communities
    numLock = parameterPack[2]
    extinct = False
    fullHistoryData = []
    metaData = [numLock, mapp.numCom - numLock]
    fullHistoryData.append(metaData)
    #for i in range(numLock):
    #    homeLockdown(mapp, mapp.communities[i])
    for i in range(numDays):
        simDay(mapp)
        if i%100 == 0:
            if not extinct and checkExtinction(mapp):
                print("Infection went extinct around t = " + str(i))
                extinct = True
                break
        if i%1000==0:
            print("Simtime: " + str(i))
        fullHistoryData.append(mapp.getComInfections())  
    save2D(fullHistoryData, name)  
    #print("fullHistoryLockdownTest completed and saved to " + name)
    return fullHistoryData

def fullHistoryLockdownRepeat(parameterPack, numDays, name):
    #this is bugged somehow, final average infection time yields 0...
    
    #this is mostly for testing purposes to tell if infection rate has a meaningful impact on total infections or just the speed they occur
    
    #most parameters are hardcoded in fullHistoryLockdownTest above
    print("fullHistoryLockdownRepeat start")
    numRep = 10
    avg = [0] * numDays #long zero array
    avgInfectionTimes = []
    avgInfectionTime = 0
    percentComplete = [] #tracks what fraction of total infections that will happen have already happened
    for i in range(numRep):
        data = fullHistoryLockdownTest(parameterPack, numDays, "tempHistory")
        sumInfTime = 0
        previousInf = 0
        for d in range(numDays):
            if len(data) > d:
                index = d
            else:
                index = len(data)-1
            sumInf = 0
            for c in data[index]:
                sumInf += c
            avg[d] += sumInf/numRep
            #infectionTime
            if d > 0:
                newInf = sumInf-previousInf
                sumInfTime += newInf*d
            previousInf = sumInf
        avgInfectionTimes.append(sumInfTime/sumInf) #because data is cummulative, most recent sumInf should be total infections
        avgInfectionTime += sumInfTime/(sumInf*numRep)
        pc = []
        for d in range(numDays):
            if len(data) > d:
                index = d
            else:
                index = len(data)-1
            curInf = 0
            for c in data[index]:
                curInf += c
            pc.append(curInf/sumInf)
        percentComplete.append(pc)
        
            
            
    wrapper = []
    for a in avg:
        wrapper.append([a])
    wrapperTimes = []
    for b in avgInfectionTimes:
        wrapperTimes.append([b])
    save2D(wrapper, name)
    save2D(wrapperTimes, name+"-avgInfectionTimes") #this is only as backup in case I need the variance
    save2D(percentComplete, name+"-percentComplete")
    print("average infection time: " + str(avgInfectionTime))
    print("fullHistoryLockdownRepeat complete and saved: " + name)

        
        


def basicLockdownSimAndSave(name):
    allData = []
    numRep = 100
    for i in range(6):
        for j in range(numRep):
            print("lockdown " + str(i))
            simData = basicLockdownTest(i, 1000, 5000)
            simData.insert(0,i) #first entry is numLockdown
            allData.append(simData)
    save2D(allData, name)
    print("basicLocdownSimAndSave complete, saved to " + name)

def timeToExtinction(numLock, maxDays, parameterPack=-1):
    mapp = defaultMap()
    
    if parameterPack != -1: #optional change from default values
        mapp.setParameters(parameterPack[0], parameterPack[1], parameterPack[2])
    t = -1
    for i in range(numLock):
        homeLockdown(mapp, mapp.communities[i])
    for i in range(maxDays):
        simDay(mapp)
        if checkExtinction(mapp):
            t = i
            break
    infs = mapp.getSumInfectionsBreakdown(numLock)
    return [t, infs[0], infs[1], infs[2]]
    #make map, adjust initial infections
    #sim until extinction or maxDays
    #report time and number infected

def timeToExtinctionTest(name):
    #separate into two completely different functions
    #one initializes infection and sees probability that it persists past 100 steps
    #one seeds endemic infection and sees how long it takes to extinct
    
    timeData = [] #how long did it take to go extinct, -1 if it never did
    infData = [] #how many people got infected over the course of the time period
    allData = []
    #numRep = 10
    numRep = 10
    maxDays = 20000
    
    print("run timeToExtinctionTest.  numRep: " + str(numRep) + " maxDays: " + str(maxDays))
    
    #numRep = 1
    #maxDays = 100
    
    for i in range(6):
        print("timeToExtinctionTest starting lockNum " + str(i))
        allRow = [i]
        infRow = [i]
        timeRow = [i]
        for j in range(numRep):
            d = timeToExtinction(i,maxDays)
            allRow.append(d)
            timeRow.append(d[0])
            infRow.append(d[1])
        allData.append(allRow)
        timeData.append(timeRow)
        infData.append(infRow)
        
    save2D(allData, name+"all")
    save2D(timeData, name+"time")
    save2D(infData, name+"inf")
    print("timeToExtinctionTest complete, saved to " + name)

def timeToExtinctionImmuneTest(name):
    #similar to timeToExtinction test but varies baseImmuneDuration instead of numLockdown

    timeData = []
    infData = []
    
    numRep = 1
    maxDays = 20000
    
    numLock = 2
    
    print("run timeToExtinctionImmuneTest. numRep: " + str(numRep) + " maxDays: " + str(maxDays))
    
    for i in range(100):
        if i != 90:
            continue
        print("timeToExtinctionImmuneTest starting baseImmune " + str(i))
        infRow = [i]
        timeRow = [i]
        for j in range(numRep):
            parameterPack = [Map.defaultInfChance, i, numLock]
            d = timeToExtinction(numLock,maxDays, parameterPack)
            timeRow.append(d[0])
            infRow.append(d[1])
        timeData.append(timeRow)
        infData.append(infRow)
        save2D(timeData, name+"time")  #rewrites the data in progress every time it completes a row, in case it's interrupted midway
        save2D(infData, name+"inf")
        

    print("timeToExtinctionImmuneTest complete, saved to " + name)

def timeToExtinctionGrid(name):
    
    start = time.time()
    print("start time: " + str(start))
    if kamiakMode:
        r = str(randint(10000000,999999999))
    
    #tests timeToExtinction as three parameters vary, infChance, immuneDuration, numLock

    #TODO, fix saving of prelude filling in with too many commas and quotations
    #TODO, add ability to differentiate between infections in lockdown communities and nonlockdown
    
    
    numRep = 20
    maxDays = 20000
    #numRep = 1
    #maxDays = 2000
    
      
    prelude = "prelude,-timeToExtinctionGrid-maxDays-"+str(maxDays)+"-formatted:infChance-ImmuneDuration-numLock-data"
    timeData = [[prelude]] #time it takes until disease goes extinct
    infData = [[prelude]]  #total infections
    lockInfData = [[prelude]] #total infections in lockdown communities
    permInfData = [[prelude]] #total infections in permissive communities
    
    if kamiakMode:
        timeData = []
        infData = []
        lockInfData = []
        permInfData= []
    
    
    
    
    print("run timeToExtinction. numRep: " + str(numRep) + " maxDays: " + str(maxDays))
    
    #note, 0.003 makes R0 slightly more than 3 at no lockdowns and slightly less at all lockdown
    index = 0
    #for infChance in [0.002, 0.005, 0.008]:
    #for infChance in [0.003, 0.0036, 0.006, 0.012]:
    for infChance in [0.003,0.004,0.005,0.006,0.007]:
    #for infChance in [0.003, 0.0035, 0.004, 0.0045,0.005,0.0055,0.006,0.0065,0.007,0.0075]:
    #for infChance in [0.003,0.0032,0.0034,0.0036,0.0038,0.004,0.0042,0.0044,0.0046,0.0048,0.005,0.0052,0.0054,0.0056,0.0058,0.006,0.0062,0.0064,0.0066,0.0068,0.007]:
        for immuneDuration in [180, 365, 1000000]:
        #for immuneDuration in [365]:
            #for numLock in [0,2,5]:
            for numLock in [0,1,2,3,4,5]:
            #for numLock in [3]:
                paramString = str(infChance)+"-"+str(immuneDuration)+"-"+str(numLock)
                timeRow = [paramString]
                infRow = [paramString]
                lockInfRow = [paramString]
                permInfRow = [paramString]
                print("starting "+paramString)
                for j in range(numRep):
                    parameterPack = [infChance, immuneDuration, numLock]
                    d = timeToExtinction(numLock,maxDays, parameterPack)
                    timeRow.append(d[0])
                    infRow.append(d[1])
                    lockInfRow.append(d[2])
                    permInfRow.append(d[3])
                timeData.append(timeRow)
                infData.append(infRow)
                lockInfData.append(lockInfRow)
                permInfData.append(permInfRow)
                
                if kamiakMode:
                    #note, numpy refuses to save an array unless it's a perfect rectangle, save2D can handle it just fine, but I'm not sure how to make it save properly on kamiak
                    np.savetxt(name+"time"+r+".csv",np.array(timeData),delimiter=',',comments=',',fmt="%s")
                    np.savetxt(name+"inf"+r+".csv",np.array(infData),delimiter=',',comments=',',fmt="%s")
                    np.savetxt(name+"lockInf"+r+".csv",np.array(lockInfData),delimiter=',',comments=',',fmt="%s")
                    np.savetxt(name+"permInf"+r+".csv",np.array(permInfData),delimiter=',',comments=',',fmt="%s")
                else:
                    save2D(timeData, name+"time")  #rewrites the data in progress every time it completes a row, in case it's interrupted midway
                    save2D(infData, name+"inf")
                    save2D(lockInfData, name+"lockInf")
                    save2D(permInfData, name+"permInf")
    
    if kamiakMode:
        name += "-"+r
    print("timeToExtinctionGrid complete and saved to: "+str(name))
    
    end = time.time()
    print("end time: " + str(end))
    
    
def timeToExtinctionGridSlice(name, varyParameters, fixedParameters):
    #for passing to kamiak
    numRep = fixedParameters[0]
    maxDays = fixedParameters[1]
    prelude = fixedParameters[2]
    infChance = varyParameters[0]
    immuneDuration = varyParameters[1]
    numLock = varyParameters[2]
    paramString = str(infChance)+"-"+str(immuneDuration)+"-"+str(numLock)
    
    timeData = [[prelude]]
    infData = [[prelude]]
    infLockData = [[prelude]] #time it takes until disease goes extinct
    infPermData = [[prelude]] #total infections
    lockInfData = [[prelude]] #total infections in lockdown communities
    permInfData = [[prelude]] #total infections in permissive communities
    
    
    
    paramString = str(infChance)+"-"+str(immuneDuration)+"-"+str(numLock)
    timeRow = [paramString]
    infRow = [paramString]
    lockInfRow = [paramString]
    permInfRow = [paramString]
    for j in range(numRep):
        parameterPack = [infChance, immuneDuration, numLock]
        d = timeToExtinction(numLock,maxDays, parameterPack)
        timeRow.append(d[0])
        infRow.append(d[1])
        lockInfRow.append(d[2])
        permInfRow.append(d[3])
    timeData.append(timeRow)
    infData.append(infRow)
    lockInfData.append(lockInfRow)
    permInfData.append(permInfRow)
    
    #replace the save methods with some kamiak-compatible code it can use to pass back
    #make sure save string is appropriately coded
    
    #save2D(timeData, name+"time")  #rewrites the data in progress every time it completes a row, in case it's interrupted midway
    #save2D(infData, name+"inf")
    #save2D(lockInfData, name+"lockInf")
    #save2D(permInfData, name+"permInf")
    
    
    
    

def initialToEndemic(name):
    #runs sims with a single infected agent and finds probability that it turns endemic
    
    #update to separately compute lockdown initial vs nonlockdown initial
    #also specifying someone who works in a large location
    
    
    numRep = 10
    timeLimit = 100
    data = []
    for numLock in range(6):
        sum = 0
        for i in range(numRep):
            mapp = singleInfMap()
            for t in range(timeLimit):
                simDay(mapp)
            if not checkExtinction(mapp):
                sum += 1
        data.append(sum)
        print("numLock " + str(numLock)+": "+str(sum)+ " out of "+str(numRep)+" maps went endemic")
    
    wrapper = [data]
    save2D(wrapper, name)
    print("initialToEndemic complete and saved to " + name)


def initialToEndemicSpecial(name):
    #runs initial to endemic but separately tracks outcomes for agents with different circumstances
    #0: lock-small, 1 lock-large
    #2: perm-small, 3 perm-large
    #4-7 same as 0-3 except commutes to a community of opposite lockdown status
    
    
    numRep = 10
    timeLimit = 100
    data = []
    for numLock in range(6):
        print("starting numLock " + str(numLock))
        typeSum = [0,0,0,0,0,0,0,0] #permLarge, permSmall, lockLarge, lockSmall
        for type in range(8):
            if (type <= 1 and numLock == 0) or (type >= 2 and numLock == 5):
                typeSum[type] = -1
                continue
            if (type >= 4 and numLock == 0):
                typeSum[type] = -1
                continue
            sum = 0
            for i in range(numRep):
                mapp = singleInfMapType(type, numLock) #infects a single agent of the right type
                for t in range(timeLimit):
                    simDay(mapp)
                if not checkExtinction(mapp):
                    sum += 1
            typeSum[type] = sum
        data.append(typeSum)
    save2D(data, name)
    print("initialToEndemicSpecial complete and saved to " + name)


#file manager stuff


def collateData(list, newName):
    #list contains a set of file names containing identically formatted data from a series of runs
    #load them, combine the data and resave into one file containing all of it fused together
    fullData = []
    prelude = ["prelude","this is collated data with no prelude from source material"]
    fullData.append(prelude)
    preludeEmpty = True
    
    #prelude should contain meta data about what parameters the run had, assume each list has the same prelude
    
    key = []
    for name in list:
        data = load2D(name)
        for row in data:
            if row[0] == "prelude" or row[0] == "\"prelude":
                if preludeEmpty:
                    fullData[0] = row
                    preludeEmpty = True
                continue
            if not row[0] in key:
                key.append(row[0])
                fullData.append([row[0]])
            i = key.index(row[0])
            del row[0]
            fullData[i+1].extend(row)
    save2D(fullData, newName)
    
    
    


filePath = "C:/Users/Matthew/Desktop/Python stuff/CommunityLockdownSaves/"
def save2D(data, name):
    path = filePath+name+".csv"
    with open(path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(data)




def load2D(name):
    path = filePath+name+".csv"
    data = []
    with open(path, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for row in reader:
            rowString = ', '.join(row)
            splitRow = rowString.split(',') 
            data.append(splitRow)
    return data

def loadAndDisplay1(name):
    data = load2D(name)
    clean = cleanData1(data)
    scatter = ScatterPlotHandler.sph(clean[0], clean[1], "Test Data", True)
    print("loadAndDisplay1 complete")
    
def loadAndDisplay2(name):
    data = load2D(name)
    clean = cleanData2(data)
    scatter = ScatterPlotHandler.sph(clean[0], clean[1], "FullHistory Data", True)
    print("loadAndDisplay2 complete")
    
def loadAndDisplay2v2(nameList):
    dataList = []
    print("loadAndDisplay2v2")
    for name in nameList:
        print(name)
        dataList.append(load2D(name))
    clean = simpleScatterMulti(dataList)
    scatter = ScatterPlotHandler.sph(clean[0], clean[1], "FullHistory Data", True)
    print("loadAndDisplay2v2 complete")
    
def loadAndDisplay2v3(nameList):
    dataList = []
    print("loadAndDisplay2v3")
    for name in nameList:
        print(name)
        dataList.append(load2D(name))
    clean = cleanData2v3(dataList)
    scatter = ScatterPlotHandler.sph(clean[0], clean[1], "FullHistory Data", True)
    print("loadAndDisplay2v2 complete")
    
    
def loadAndDisplay3(name):
    tte = load2D(name + "time")
    #clean = cleanDataSimple(tte)
    clean = cleanData3(tte)
    scatter = ScatterPlotHandler.sph(clean[0],clean[1], "Time to Extinction", True)
    print("loadAndDisplay3 complete")
    
        
def loadAndDisplay4(name):
    data = load2D(name)
    clean = cleanData4(data)
    scatter = ScatterPlotHandler.sph(clean[0],clean[1], "Endemic Probability", True)
    print("loadAndDisplay4 complete")
    
def cleanData1(data):
    #take raw data from lockdown sim and format it into a way that ScatterPlotHandler can display    
    #TODO: adjust this for statistical variance
    clean = []  #append xP then yP, each should have two graphs for LockDown and Permissive
    xLock = []
    xPerm = []
    yLock = []
    yPerm = []
    for i in range(len(data)):
        for j in range(len(data[i])):
            data[i][j] = float(data[i][j].replace('*', '')) #remove stars from data, which represent extinction
    

    for i in range(len(data)):
        lockSum = 0
        permSum = 0
        numLock = data[i][0]
        numPerm = len(data[i])-1-numLock
        for j in range(len(data[i])):
            if j > 0 and j <= numLock:
                lockSum += data[i][j]
            elif j > numLock:
                permSum += data[i][j]
        if numLock > 0:
            lockAvg = lockSum/numLock
            xLock.append(numLock)
            yData = [0,0,lockAvg,0,0]    #adjust this later with error bars
            yLock.append(yData)
            print("xLock append " + str(numLock))
        if numPerm > 0:
            permAvg = permSum/numPerm
            xPerm.append(numLock)
            yData = [0,0,permAvg,0,0]
            yPerm.append(yData)
    xP = [xLock, xPerm]
    yP = [yLock, yPerm]
    clean = [xP, yP]
    return clean        

def simpleScatterMulti(dataList):
    #takes list of list of y value and adds linear x points for ScatterPlotHandler
    xP = []
    yP = []
    pop = False
    for data in dataList:
        x = range(len(data))
        xP.append(x)
        data1D = []
        for d in data: #unwraps a  Nx1  2D array into a 1D array
            data1D.append([0,0,float(d[0]),0,0]) #still has error bar hack, center is actual value, sides are for error bars later
            if not pop:
                print(str(d))
                pop = True
        yP.append(data1D)
    clean = [xP, yP]
    return clean
    
    
def cleanData2(data):
    #TODO: add ability to average over certain time ranges
    
    
    #take raw data from fullHistoryLockdownSim and format it into a way that ScatterPlotHandler can display
    #makes a graph showing sumInfections over time for a single sim
    clean = []  #append xP then yP, each should have two graphs for LockDown and Permissive
    xLock = []
    xPerm = []
    yLock = []
    yPerm = []
    
    numLock = int(data[0][0])
    numPerm = int(data[0][1])
    del data[0]
    for i in range(len(data)):
        for j in range(len(data[i])):
            data[i][j] = int(data[i][j])
    
    for t in range(len(data)):
        lockSum = 0
        permSum = 0
        ##
        #if t == 0:
        #    continue
        for j in range(len(data[t])):
            if j < numLock:
                ##subtraction is an optional mode to show infection rate over time rather than sum
                lockSum += data[t][j]# - data[t-1][j]
            elif j >= numLock:
                permSum += data[t][j]# - data[t-1][j]
        if numLock > 0:
            lockAvg = lockSum/numLock
            xLock.append(t)
            yData = [0,0,lockAvg,0,0]    #adjust this later with error bars
            yLock.append(yData)
        if numPerm > 0:
            permAvg = permSum/numPerm
            xPerm.append(t)
            yData = [0,0,permAvg,0,0]
            yPerm.append(yData)
    xP = [xLock, xPerm]
    yP = [yLock, yPerm]
    clean = [xP, yP]
    return clean     

def cleanData2v3(fullData):
    #takes data from fullHistoryRepeat, averages each row, and displays two graphs on the same grid
    #note that this data has each sim in its own row, so average over columns
    
    xp = []
    yp = []
    for data in fullData:
        xd = []
        yd = []
        for x in range(len(data[0])):
            sum = 0
            for y in range(len(data)):
                sum += float(data[y][x])
            yd.append([0,0,sum/len(data),0,0])
            xd.append(x)
            x += 1
        xp.append(xd)
        yp.append(yd)
    clean = [xp, yp]
    return clean
            

    
def cleanDataSimple(data):
    #takes first input as x coordinate (probably numLock), takes rest of row as data points

    xPoints = []
    yPoints = []

    for row in data:
        x = int(row[0])
        for col in range(len(row)):
            if col > 0:
                xPoints.append(x)
                y = [0,0,int(row[col]),0,0]
                yPoints.append(y)
        
        
    xShell = [xPoints] #becaue ScatterPlotHandler expects a list of graphs, even though we only have one
    yShell = [yPoints]
    clean = [xShell, yShell]
    return clean      

def cleanData3(data):
    #for timeToExtinction
    #basically the same as cleanDataSimple except log plot
    simple = cleanDataSimple(data)
    xShell = simple[0]
    yPoints = simple[1][0]
    for y in yPoints:
        if y[2] == -1:
            y[2] = 100000
        y[2] = math.log10(y[2])
    yShell = [yPoints]
    clean = [xShell,yShell]
    return clean

def cleanData4(data):
    #for initialToEndemicSpecial
    
    xPoints = [[],[],[],[],[],[],[],[]]
    yPoints = [[],[],[],[],[],[],[],[]]
    for row in range(len(data)):
        for col in range(len(data[row])):
            if int(data[row][col]) == -1:
                continue
            xPoints[col].append(row)
            y = [0,0,int(data[row][col]),0,0]
            yPoints[col].append(y)
    clean = [xPoints, yPoints]
    return clean  



def hackR0EstimatorTest(numLock=0):
    print("hackR0EstimatorTest, numLock: " + str(numLock))
    numRep = 100
    sum = 0
    
    infectedDuration = 14
    if smallMode:
        infectedDuration = 7
    
    for i in range(numRep):
        mapp = singleInfMap()
        for i in range(numLock):
            homeLockdown(mapp, mapp.communities[i])
        if not bev2:
            sum += R0simDay(mapp)
        else:
            sum += R0simDayBev(mapp)
    perDay = sum/numRep
    perInf = perDay * Agent.infectedDuration
    print("hackR0EstimatorTest found R0 connectivity perDay " +str(perDay) + "-> total: " +str(perInf))
    print("multiply by infectivity to get R0.")
    #print("at default infectivity this yields R0: " + str(perInf*Map.defaultInfChance))
    
    #under standard parameters with numLock 3
    #somewhere around 21.23 contacts per day per person yielding around 297 contacts per infection
    #making R0 approximately 1 at infChance 0.0033
    #or, R0 ~= 300*infChance
    




def R0simDay(mapp):
    #runs a simDay with no actual infections but estimates the potential for  of each person
    #This version is based on the non-localized location behavior
    if bev2:
        print("WARNING: R0simDay() called when bev2 is True")
    sum = 0
    for shift in range(3):
    #for shift in [2]:
        resetLocations(mapp)
        for agent in mapp.allAgents:
            loc = random.choices(mapp.allLocations, agent.behavior[shift])[0]
            loc.presentAgents.append(agent)
            loc.community.comPAgents.append(agent)
        for com in mapp.communities:
            for loc in com.locations:
                for pair in itertools.permutations(loc.presentAgents, 2):
                    sum += 1
    average = sum/len(mapp.allAgents) #estimated R0 for an average infected agent
    return average

def R0simDayBev(mapp):
    if not bev2:
        print("WARNING: R0simDayBev() called when bev2 is False")
    sum = 0
    for shift in range(3):
        assignLocations2(mapp, shift)
        for com in mapp.communities:
            for loc in com.locations:
                for pair in itertools.permutations(loc.presentAgents, 2):
                    sum += 1
    average = sum/len(mapp.allAgents) #estimated R0 for an average infected agent
    return average


def tempProfileTest():
    cProfile.run("timeToExtinctionTestProfileMode()")
    loadAndDisplay4("timeToExtinctionB_immune65")

def timeToExtinctionTestProfileMode():
    timeToExtinctionTest("timeToExtinctionB_immune65")
    #initialToEndemicSpecial("initialToEndemicSpecialBev1")
    
    
def tempCollateDataTest():  
    list = ["timeToExtinctionGridTest8inf", "timeToExtinctionGridTest9inf", "timeToExtinctionGridTest9binf"]
    collateData(list, "collateTest")
    print("tempCollateDataTest complete")
    
def kamiakCollate(base):
    #takes a pile of individual files generated by kamiak running timeToExtinctionGrid a bunch of times
    #and combines them into summary files
    d = "kamiakDumps6_HubOutPerfect/"  #save2D already directs to my desktop pythonSaves folder, this just adds the subfolder
    rootList = [base+"inf",base+"time",base+"lockInf",base+"permInf"]
    suffList = kamiakCollateGetNames("C:/Users/Matthew/Desktop/Python stuff/CommunityLockdownSaves/kamiakDumps6_HubOutPerfect",base)
    numCol = 0
    for root in rootList:
        list = suffList.copy()
        for i in range(len(list)):
            list[i] = d+root+suffList[i]
            numCol += 1
        collateData(list, root)
    print("kamiakCollate completed: " + str(numCol) + " files combined")        
        
def kamiakCollateGetNames(path, base):
    #pulls off all the prefixes and suffixes to find the random numbers that were assigned to individual jobs
    #only uses the inf files because the others should have identical copies
    suffList = []
    for x in os.listdir(path):
        if x.startswith(base+"inf"):
            a = x.removeprefix(base+"inf")
            b = a.removesuffix(".csv")
            suffList.append(b)
    return suffList
    
        

def gridFileTo3DAvg(name):
    #takes a 2D CSV file in which each row starts with a cell describing three parameters, and the rest contain data points
    #and creates a 3D array based on combinations of those parameters
    #with value equal to the average of the data points
    
    
    rawData = load2D(name)
    labels = [[],[],[]]
    for row in rawData:
        if row[0] == "prelude" or row[0] == "\"prelude":
            continue
        #use first entry in row of saveFile to figure out how large to make the array
        words = row[0].split('-')
        UsefulStaticMethods.flipEntries(words,0,1)
        c = [-1,-1,-1]
        for i in range(3):
            if not words[i] in labels[i]:
                labels[i].append(words[i])
            c[i] = labels[i].index(words[i])
    
    grid = [] #makes 3D array of appropriate size.  There has to be a better way to do this in Python
    for a in range(len(labels[0])):
        gridb = []
        for b in range(len(labels[1])):
            gridc = []
            for c in range(len(labels[2])):
                gridc.append(0)
            gridb.append(gridc)
        grid.append(gridb)

    
    #quite redundant, but now that grid exists I can put stuff in it
    for row in rawData:
        if row[0] == "prelude" or row[0] == "\"prelude":
            continue
        #use first entry in row of saveFile to figure out where to put data
        words = row[0].split('-')
        UsefulStaticMethods.flipEntries(words,0,1)
        c = [-1,-1,-1]
        for i in range(3):
            if not words[i] in labels[i]:
                print("WARNING, gridFileTo3DAvg found different label stuff in the second section")
            c[i] = labels[i].index(words[i])      
        sum = 0
        for i in range(len(row)):
            if i == 0:
                continue
            sum += int(row[i])
        avg = sum/(len(row)-1)
        grid[c[0]][c[1]][c[2]] = avg #make sure this is actually correct
    #print("grid:")
    #print(grid)
    print("labels:")
    print(labels)
    return grid


def gridFileToLockPermCompare(nameLock, namePerm):
    #takes data from files representing infections of lockdown communities and infections of permissive communities, presumably from the same data set
    #averages data for infectivity together, leaving numLock varied as the x axis
    #graphs the results on a scatterplot for comparison (separate graph for each immune duration)
    #I thought I had something that did a regression for slope, but I'm not sure where.  maybe I did that manually on the internet
    #if so, implement it here
    
    
    permData = gridFileTo3DAvg(namePerm)#arrays are indexed by [immunity][infectivity][numLock]
    
    
    lockData = gridFileTo3DAvg(nameLock) 
    fullData = [permData,lockData]
    
    denom = len(lockData[0])
    
    avg = []
    
    for d in range(2): #perm or lock
        avg.append([])
        for i in range(len(permData)): #immunity
            avg[d].append([])
            for j in range(len(permData[d])): #infectivity (gets collapsed in the new array)
                for k in range(len(permData[d][j])): #numLock
                    numCom = k
                    if d == 0:
                        numCom = 5-k #number of permissive
                    if numCom < 1:
                        numCom = 1 #hack to avoid dividing by zero
                    normalizer = 1/numCom
                    if j == 0:
                        avg[d][i].append(0)
                    avg[d][i][k] += fullData[d][i][j][k]*normalizer/denom

    
    for imm in range(len(fullData[0])):
        xP = []
        yP = []
        for d in range(2):
            xp = []
            yp = []
            for numLock in range(len(avg[d][imm])):
                xp.append(numLock)
                yp.append([0,0,avg[d][imm][numLock],0,0])
            xP.append(xp)
            yP.append(yp)
    
        label = "permInf and lockInf as a function of numLock, immuneDuration: " + str(imm)
        bounds = [0,5,0,500]
        scatter = ScatterPlotHandler.sph(xP,yP, label, True, setBounds=bounds)
        
        #now set good bounds for scatter
        
        
    
    print("gridFileToLockPermCompare complete")
            

tempLinearMode = False

def VarySquareLoader(name, extraNormalizer="none"):
    data = gridFileTo3DAvg(name)
    xAx = [0,1,2,3,4,5]
    #yAx = [0.003,0.0036,0.006,0.012]
    yAx = [0.003,0.004,0.005,0.006,0.007]
    immuneList = ["180","365","infinite"]
    if tempLinearMode:
        xAx = [3]
        yAx = [0.003, 0.0035, 0.004, 0.0045,0.005,0.0055,0.006,0.0065,0.007,0.0075]
        immuneList = ["365"]
    
    for i in range(len(immuneList)):
        lab = "TimeToExtinction as a function of infectivity (y) and numLockdown (x) for immuneDuration: " + immuneList[i]
        dat = data[i]
        maxx = 3000
        #maxx = 10000
        normVal = [1,1,1,1,1,1]
        nlt = "none"
        if extraNormalizer == "lock":
            normVal = [1,1,2,3,4,5]
        if extraNormalizer == "perm":
            normVal = [5,4,3,2,1,1]
        if extraNormalizer != "none":
            nlt = "sqrt"
            maxx /= 5
            lab += ", extraNormalizer = " + extraNormalizer
            for row in dat:
                for j in range(6):
                    row[j] /= normVal[j]
        
        square = VarySquare.vs(xAx, yAx, lab, dat, maxx, nonlinearTransform=nlt)
    
    
    

def graphInfLockProjection(name, num=6):
    fullData = gridFileTo3DAvg(name)
    conversionScale = [317.146872,310.398648,303.647568,297.045896,290.166576,283.366216] #data from hackR0_allLock_100rep.txt
    if num == 1:
        conversionScale = [297.045896] #numLock 3 only
    #infAxis = [0.003,0.004,0.005,0.006,0.007]
    infAxis = [0.003,0.0032,0.0034,0.0036,0.0038,0.004,0.0042,0.0044,0.0046,0.0048,0.005,0.0052,0.0054,0.0056,0.0058,0.006,0.0062,0.0064,0.0066,0.0068,0.007]
    scatterBounds = [0,2.5, 0,5000]
    #for i in range(3):
    for i in range(1):
        data = infLockProjection(fullData[i],conversionScale, infAxis)
        scatter = ScatterPlotHandler.sph(data[0],data[1], "infLockProjection " + str(i), False, setBounds=scatterBounds,scatterName=name)
        #TODO, change infLockProjection to save as multiple scatter graphs to see if projection is nicely behaved


def infLockProjection(data, conversionScale, infAxis):
    #converts a 2D array with infectivity on y axis and numLock on x axis
    #into a 1D array of R0, under the assumption that
    # R0 = infectivity * conversion(n), where conversion is pre-measured via hackR0Estimator
    #data may end up unsorted, but ScatterPlotHandler should be able to handle it
    xPoints = []
    yPoints = []
    for y in range(len(data)):
        for x in range(len(data[y])):
            r0 = infAxis[y]*conversionScale[x]
            xPoints.append(r0)
            yPoints.append([0,0,data[y][x],0,0])
    newData = [xPoints,yPoints]
    return newData
    



    
def kamiakTest():
    print("kamiakTest() called")
    
    #fileName = "testFile.txt"
    #file1 = open(fileName , "w")
    #toFile = "Kamiak test file text"
    #file1.write(toFile)
    #file1.close()
    
    #suffix = "testFile2"
    #base_sweep = [1,2,3,4,5]
    #base_sweep = ["kamiakTest1","kamiakTest2",3,4,5]
    #fileName = "ktestFile2.csv"
    
    #np.savetxt(''.join(['kamiak_',suffix,'.csv']),base_sweep,delimiter=',',comments=',',fmt="%s")
    #np.savetxt(fileName,base_sweep,delimiter=',',comments=',',fmt="%s")
    #timeData = [[1,2],[5,43],[9,10]]
    #convertedData = np.array(timeData)
    
    #np.savetxt("ktestFile3.csv",convertedData,delimiter=',',comments=',',fmt="%s")
    

    #VarySquareLoader("kamiakTest4inf")
    #timeToExtinctionGrid("kamiakTest5_butterySmooth")
    #timeToExtinctionGrid("kamiakTest6Temp")
    #kamiakCollate("kamiakTest6_HubOutPerfect")   #path directory is hardcoded in this method, since it's run so rarely

    #path = "C:/Users/Matthew/Desktop/Python stuff/CommunityLockdownSaves/kamiakDumps6_HubOutPerfect/"
    #s1 = "6Hub"
    #s2 = "6_Hub"
    #UsefulStaticMethods.fileRenamer(path,s1,s2)


#main stuff

if kamiakMode:
    kamiakTest()
else:
    test = defaultMap()
    makeWindow(test)    





