import math
import PySimpleGUI as sg
import os



def distance(c1, c2):
    ss = 0
    for i in range(len(c1)):
        ss += (c1[i]-c2[i])*(c1[i]-c2[i])
    return math.sqrt(ss)


def normalize(list):
    sum = 0
    for item in list:
        sum += item
    if sum == 0:
        return list
    for i in range(len(list)):
        list[i] /= sum
    return list



def flipEntries(list,a,b):
    temp = list[a]
    list[a] = list[b]
    list[b] = temp
    return list #shouldn't need actual return


def fileRenamer(path, s1, s2):
    #this takes a bunch of files in the path folder, and replaces a substring in their filename with another
    #because I accidentally named a bunch of related files wrong
    #path = "C:/Users/Matthew/Desktop/Python stuff/CommunityLockdownSaves/kamiakDumps4/"
    count = 0
    for filename in os.listdir(path):
        old_name = os.path.join(path, filename)
        if s1 in old_name:
            new_name = old_name.replace(s1, s2)
            os.rename(old_name, new_name)
            count += 1
    print("fileRenamer complete, " + str(count) + " files renamed")
    
    
    
    
