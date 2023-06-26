

conditions = {"BLEEDING", "BURNING", "CONFUSION",
              "POISONED", "TORMENT", "BLINDED",
              "CHILLED", "CRIPPLED", "FEAR",
              "IMMOBILE", "SLOW", "TAUNT",
              "WEAKNESS", "VULNERABILITY"}

boons = {"MIGHT", "ALACRITY", "VIGOR",
         "SWIFTNESS", "STABILITY", "RESOLUTION",
         "RESISTANCE", "REGENERATION", "QUICKNESS",
         "PROTECTION", "FURY", "AEGIS"}


def updateCastDur(jsonData):
    castDuration = -1
    modeSum = 0
    numSamples = 0
    for profession in jsonData["professionStats"]:
        if "mode" in jsonData["professionStats"][profession]["durations"]:
            modeSum += jsonData["professionStats"][profession]["durations"]["mode"]
            numSamples += 1

    if numSamples != 0:
        castDuration = modeSum / numSamples
        castDuration = int(40 * round(float(castDuration) / 40))  # round to nearest 40

    return castDuration


class Skill:

    def __init__(self, id=None, name=None, weaponType=None, professionList=None, coefficientsList=None, 
                rechargeDuration=None, cooldown=None, canCrit=None, ammo=None, pulseOnTickList=None,
                needsManualReview=None, onStrikeEffectsList=None, onPulseEffectsList=None,
                castDuration=None, strikeOnTickList=None, onStrikeNumStacks=None
                ):

        self.castDuration = 0 if castDuration is None else castDuration
        self.cooldown = 0 if cooldown is None else cooldown
        self.rechargeDuration = rechargeDuration
        self.canCrit = True if canCrit is None else canCrit
        self.needsManualReview = False if needsManualReview is None else needsManualReview
        self.ammo = 0 if ammo is None else ammo 
        self.onPulseEffects = [] if onPulseEffectsList is None else onPulseEffectsList
        self.onStrikeEffects = [] if onStrikeEffectsList is None else onStrikeEffectsList
        self.coefficients = [] if coefficientsList is None else coefficientsList
        self.strikeOnTickList = [] if strikeOnTickList is None else strikeOnTickList 
        self.pulseOnTickList = [] if pulseOnTickList is None else pulseOnTickList
        self.professions = [] if professionList is None else professionList 
        self.id = str(id)
        self.onStrikeNumStacks = 0 if onStrikeNumStacks is None else onStrikeNumStacks
        self.name = "UNAMED_SKILL" if name is None else name
        self.weaponType = "empty_handed" if weaponType is None else weaponType


    @classmethod
    def createSkill(cls, jsonData):
        name = jsonData["skill"]["name"] if "name" in jsonData["skill"] else None
        id = jsonData["skill"]["id"] if "id" in jsonData["skill"] else None
        return cls(name=name, id=id, needsManualReview=True)


    @classmethod
    def createSkillFromAPI(cls, jsonData):
        castDuration = 0
        cooldown = 0
        rechargeDuration = None
        canCrit = True
        needsManualReview = False
        ammo = 0
        onPulseEffects = []
        onStrikeEffects = []
        coefficients = []
        strikeOnTickList = []
        pulseOnTickList = []
        professions = []
        id = str(jsonData["skillID"])
        onStrikeNumStacks = 0
        hitCount = -1
        pulseCount = -1
        effects = []

        #assign values if found in json data
        if "name" in jsonData:
            name = jsonData["name"][0].replace("\\", "")
        else:
            name = None

        if "weapon_type" in jsonData and jsonData["weapon_type"] != "None":
            weaponType = jsonData["weapon_type"]
        else:
            weaponType = "empty_handed"

        #each prof has its own cast time in json; find avg...
        newCastDuration = updateCastDur(jsonData)
        castDuration = castDuration if newCastDuration == -1 else newCastDuration

        professions = jsonData["professions"].copy()

        #facts contains a variety of unstructured, often times inaccurate and conflicting data
        #we attempt to make sense of the data; if we know something is wrong mark for manual review
        if "facts" in jsonData:

            for fact in jsonData["facts"]:

                #sometimes multiple dmg coefficients are provided...
                if "dmg_multiplier" in fact:
                    coefficients.append(fact["dmg_multiplier"])

                if "hit_count" in fact:
                    hitCount = fact["hit_count"]

                if "text" in fact:


                    #the api mixes up count recharge with recharge on skills that have ammo
                    #skills with counts have their actual cooldown listed as count recharge
                    #if we find both values, we know that skill is an ammo type, and we swap them
                    if fact["text"] == "Count Recharge":
                        rechargeDuration = cooldown
                        cooldown = fact["duration"]

                    if fact["text"] == "Recharge":
                        if rechargeDuration is None:
                            cooldown = fact["value"]
                        else:
                            rechargeDuration = fact["value"]

                    if fact["text"] == "Cannot Critical Hit":
                        canCrit = False

                    if fact["text"] == "Casts":
                        ammo = fact["value"]

                    if fact["text"] == "Pulses":
                        pulseCount = fact["value"]
                        for x in range(0, pulseCount):
                            pulseOnTickList.append(x * 1000)


                    #we only handle condition/boon application for now
                    #not feasible to consistently and accurate determine
                    #the mechanics of condition application based off the
                    #api data, so all skills that apply condition must be
                    #manually reviewed...
                    if fact["text"] == "Apply Buff/Condition":

                        if fact["status"].upper() in conditions or fact["status"].upper() in boons:
                            effect = {
                                "effect": fact["status"],
                            }
                            if "duration" in fact:
                                effect["base_duration_ms"] = fact["duration"] * 1000
                            if "apply_count" in fact:
                                effect["num_stacks"] = fact["apply_count"]
                            else:
                                effect["num_stacks"] = 1

                            if fact["status"].upper() in conditions:
                                effect["direction"] = "OUTGOING"
                            else:
                                effect["direction"] = "INCOMING"

                            effects.append(effect)
                            needsManualReview = True


        #if both these values are zero the skill is probably a single pulse buff(ie, feel my wrath)
        #pulse mentions with the api are very inconsistent, so we're just going to assume 1 pulse in this case
        if hitCount == -1 and pulseCount == -1:
            pulseOnTickList = [castDuration]
            pulseCount = 1


        #sometimes there are multiple buffs listed, if any of them match the number of hits we make
        #an assumption that each hit applies said buff
        #this is not a perfect assumption and needs to be manually checked
        #if it matches both the numHits and numPulses, we just attribute it to strikes rather than pulses
        for effect in effects:
            if "num_stacks" in effect:
                if effect["num_stacks"] == hitCount:
                    effect["on_strike_num_stacks"] = 1
                    onStrikeEffects.append(effect)
                elif effect["num_stacks"] == pulseCount:
                    effect["on_pulse_num_stacks"] = 1
                    onPulseEffects.append(effect)
                elif hitCount > 0:
                    onStrikeEffects.append(effect)
                elif pulseCount > 0:
                    onPulseEffects.append(effect)



        #if multiple damage coeffs are listed we need to manually review
        if len(coefficients) > 1:
            needsManualReview = True

        
        return cls(id=id, name=name, weaponType=weaponType, professionList=professions, coefficientsList=coefficients,
                    rechargeDuration=rechargeDuration, cooldown=cooldown, canCrit=canCrit, ammo=ammo,
                    pulseOnTickList=pulseOnTickList, needsManualReview=needsManualReview, 
                    onStrikeEffectsList=onStrikeEffects, onPulseEffectsList=onPulseEffects, castDuration=castDuration,
                    strikeOnTickList=strikeOnTickList, onStrikeNumStacks=onStrikeNumStacks)





