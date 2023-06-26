import os.path
import subprocess
import json
import os
import sys
import ntpath
import re
from multiprocessing.pool import ThreadPool
from Skill import *
from sys import argv


def getSkillData(APIFileName, skills):
    with open(APIFileName, "r") as file:
        data = json.load(file)
        for entry in data["results"]:
            if entry["skillID"] not in skills:
                skill = Skill.createSkillFromAPI(entry)
                skills[skill.id] = skill
            else:
                newCastDuration = updateCastDur(entry)
                if newCastDuration != -1: 
                    skills[entry["skillID"]].castDuration = newCastDuration
                #sometimes there are duplicate skills that are missing cast times, so we need to update the cast time everytime a duplicate is found
                #otherwise it might default to 0 if there is a missing cast time



def generateRawTickData(pathToLogTool, pathToLogFile, pathToTickOutput):
    #run zethox's arcdps log tool to gather tick data
    process = subprocess.run([pathToLogTool,
        pathToLogFile,
        pathToTickOutput,
        "cast"])

    return process


def parseSkillTickData(tickDataJsonFileName, skillTickData):

#skillTickData =
#            {
#                id:
#                    {
#                        length: {
#                                    freq: "",
#                                    running sum: [],
#                                },
#                       length:...
#                    },
#                id:....
#            }

    with open(tickDataJsonFileName, "r") as file:
        data = json.load(file)
        for entry in data["casts"]:

            #sometimes we can get bad tick data(ie someone running symbols with writ of persistence)
            #so we match arrays of ticks with other arrays that have the same length
            #each individual tick is avg'd to deal with outliers
            skill = entry["skill"]["id"]
            if skill not in skillTickData:
                skillTickData[skill] = {}

            if len(entry["hits"]) not in skillTickData[entry["skill"]["id"]]:
                skillTickData[skill][len(entry["hits"])] = {}
                skillTickData[skill][len(entry["hits"])]["freq"] = 0
                skillTickData[skill][len(entry["hits"])]["runningSum"] = [0] * len(entry["hits"])

            skillTickData[skill][len(entry["hits"])]["freq"] += 1
            for i in range(0, len(entry["hits"])):
                skillTickData[skill][len(entry["hits"])]["runningSum"][i] += entry["hits"][i]["tick"]

        #for entry in data["hits_without_cast"]:
        #    if "skill" in entry:
        #    skill = entry["skill"]["id"]
        #    if skill not in skills[skill]:
        #        newSkill = Skill(skill)
        #        skills[skill] = newSkill



def attachTickData(skills, skillTickData):
    for skillID in skillTickData:
        newStrikeOnTickList = []

        #for all our tick lists, we want to attach the one with the most common length
        #in order to avoid bad/buggy data
        mostFreq = 0
        mostFreqLength = 0
        for length in skillTickData[skillID]:
            if skillTickData[skillID][length]["freq"] > mostFreq:
                mostFreq = skillTickData[skillID][length]["freq"]
                mostFreqLength = length


        if str(skillID) in skills:
            for tick in skillTickData[skillID][mostFreqLength]["runningSum"]:
                #we store the tick count, to get the actual time we multiply tick * 40
                newStrikeOnTickList.append(round(tick / mostFreq) * 40)

        if str(skillID) in skills:
            skills[str(skillID)].strikeOnTickList = newStrikeOnTickList.copy()



def skillToJsonFormat(skill, professions):
        jsonEntry = {}
        jsonEntry["skill_id"] = skill.id
        jsonEntry["skill_key"] = skill.name
        jsonEntry["weapon_type"] = skill.weaponType
        jsonEntry["cast_duration"] = [int(round((skill.castDuration * 1.5) / 40) * 40), skill.castDuration]

        if len(skill.pulseOnTickList) > 0:
            jsonEntry["pulse_on_tick_list"] = [skill.pulseOnTickList, skill.pulseOnTickList]
        if len(skill.strikeOnTickList) > 0:
            jsonEntry["strike_on_tick_list"] = [skill.strikeOnTickList, skill.strikeOnTickList]
        if len(skill.coefficients) > 0:
            jsonEntry["damage_coefficient"] = skill.coefficients[0]
        if skill.cooldown is not None:
            jsonEntry["cooldown"] = [int(skill.cooldown * 1000), int(skill.cooldown * .8 * 1000)]
        if not skill.canCrit:
            jsonEntry["can_critical_strike"] = "false"
        if skill.rechargeDuration is not None:
            jsonEntry["recharge_duration"] = skill.rechargeDuration
        if skill.ammo > 0:
            jsonEntry["ammo"] = skill.ammo

        if len(skill.onStrikeEffects) > 0:
            jsonEntry["on_strike_effect_applications"] = skill.onStrikeEffects
        if len(skill.onPulseEffects) > 0:
            jsonEntry["on_pulse_effect_applications"] = skill.onPulseEffects

        for profession in skill.professions:
            if profession not in professions:
                professions[profession] = {"skills" : []}

            professions[profession]["skills"].append(jsonEntry)


def writeToOutput(jsonObjects, outPath):
    for profession in jsonObjects:
        if not os.path.exists(outPath + profession + "\\"):
            os.makedirs(outPath + profession)

        formattedJsonObj = json.dumps(jsonObjects[profession], indent=4)

        with open(outPath + profession + "\\" + profession + ".json", "w") as file:
            file.write(formattedJsonObj)


def getFileList(rootDirPath):
    outFiles = []
    for (root, dir, files) in os.walk(rootDirPath):
        for file in files:
            outFiles.append(root + file)
    return outFiles

def main():
    if len(sys.argv) < 2:
        raise Exception("Unexpected number of arguments. Exiting")
        exit()

    curDir = os.path.dirname(os.path.realpath(__file__))

    pathToLogTool = sys.argv[1]
    pathToARCDPSLogs = curDir + "\\arc_log_files\\"
    if len(sys.argv) >= 3:
        pathToARCDPSLogs = sys.argv[2]


    skillDataFiles = getFileList(curDir + "\\profession_data\\")
    numFiles = str(len(skillDataFiles) - 1)
    filesProcessed = 0

    skills = {}
    for file in skillDataFiles:
        print(str(filesProcessed) + "/" + numFiles + "\t\tProcessing profession data file: " + file + "...", end="")
        getSkillData(file, skills)
        filesProcessed += 1
        print(" DONE")


    if not os.path.exists(curDir + "\\tick_data\\"):
        os.mkdir(curDir + "\\tick_data\\")
    arcLogFiles = getFileList(pathToARCDPSLogs)

    pool = ThreadPool()
    for filename in arcLogFiles:
        pool.apply_async(generateRawTickData, (pathToLogTool, filename, curDir + "\\tick_data\\" + ntpath.basename(filename),))

    pool.close()
    pool.join()


    skillTickData = {}
    tickDataFiles = getFileList(curDir + "\\tick_data\\")
    numFiles = str(len(tickDataFiles) - 1)
    filesProcessed = 0
    for fileName in tickDataFiles:
        print(str(filesProcessed) + "/" + numFiles + "\t\tParsing tick data from file: " + fileName + "...", end="")
        parseSkillTickData(fileName, skillTickData)
        print(" DONE")
        filesProcessed += 1

    print("Attaching tick data to skills...", end="")
    attachTickData(skills, skillTickData)
    print(" DONE")


    professions = {}
    professionsManualReview = {}
    print("Saving data to output...", end="")
    for id in skills:
        if skills[id].needsManualReview:
            skillToJsonFormat(skills[id], professionsManualReview)
        else:
            skillToJsonFormat(skills[id], professions)

    writeToOutput(professions, curDir + "\\output\\skills\\")
    writeToOutput(professionsManualReview, curDir + "\\output\\skills(needs-manual-review)\\")

    print(" DONE")


main()
