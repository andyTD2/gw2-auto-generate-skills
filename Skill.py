

conditions = {"BLEEDING", "BURNING", "CONFUSION",
              "POISONED", "TORMENT", "BLINDED",
              "CHILLED", "CRIPPLED", "FEAR",
              "IMMOBILE", "SLOW", "TAUNT",
              "WEAKNESS", "VULNERABILITY"}

boons = {"MIGHT", "ALACRITY", "VIGOR",
         "SWIFTNESS", "STABILITY", "RESOLUTION",
         "RESISTANCE", "REGENERATION", "QUICKNESS",
         "PROTECTION", "FURY", "AEGIS"}
class Skill:

    def __init__(self, jsonData,):


        #default values
        self.castDuration = 0
        self.cooldown = 0
        self.rechargeDuration = None
        self.canCrit = True
        self.rechargeDuration = None
        self.needsManualReview = False
        self.ammo = 0
        self.onPulseEffects = []
        self.onStrikeEffects = []
        self.coefficients = []
        self.strikeOnTickList = []
        self.pulseOnTickList = []
        self.professions = []
        self.id = jsonData["skillID"]
        self.onStrikeNumStacks = 0
        hitCount = -1
        pulseCount = -1
        effects = []


        #assign values if found in json data
        if "name" in jsonData:
            self.name = jsonData["name"][0].replace("\\", "")
        else:
            self.name = "NAME_MISSING"

        if "weapon_type" in jsonData and jsonData["weapon_type"] != "None":
            self.weaponType = jsonData["weapon_type"]
        else:
            self.weaponType = "empty_handed"

        #each prof has its own cast time in json; find avg...
        self.updateCastDur(jsonData)

        self.professions = jsonData["professions"].copy()

        #facts contains a variety of unstructured, often times inaccurate and conflicting data
        #we attempt to make sense of the data; if we know something is wrong mark for manual review
        if "facts" in jsonData:

            for fact in jsonData["facts"]:

                #sometimes multiple dmg coefficients are provided...
                if "dmg_multiplier" in fact:
                    self.coefficients.append(fact["dmg_multiplier"])

                if "hit_count" in fact:
                    hitCount = fact["hit_count"]

                if "text" in fact:


                    #the api mixes up count recharge with recharge on skills that have ammo
                    #skills with counts have their actual cooldown listed as count recharge
                    #if we find both values, we know that skill is an ammo type, and we swap them
                    if fact["text"] == "Count Recharge":
                        self.rechargeDuration = self.cooldown
                        self.cooldown = fact["duration"]

                    if fact["text"] == "Recharge":
                        if self.rechargeDuration is None:
                            self.cooldown = fact["value"]
                        else:
                            self.rechargeDuration = fact["value"]

                    if fact["text"] == "Cannot Critical Hit":
                        self.canCrit = False

                    if fact["text"] == "Casts":
                        self.ammo = fact["value"]

                    if fact["text"] == "Pulses":
                        pulseCount = fact["value"]
                        for x in range(0, pulseCount):
                            self.pulseOnTickList.append(x * 1000)


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
                            self.needsManualReview = True


        #if both these values are zero the skill is probably a single pulse buff(ie, feel my wrath)
        #pulse mentions with the api are very inconsistent, so we're just going to assume 1 pulse in this case
        if hitCount == -1 and pulseCount == -1:
            self.pulseOnTickList = [self.castDuration]
            pulseCount = 1


        #sometimes there are multiple buffs listed, if any of them match the number of hits we make
        #an assumption that each hit applies said buff
        #this is not a perfect assumption and needs to be manually checked
        #if it matches both the numHits and numPulses, we just attribute it to strikes rather than pulses
        for effect in effects:
            if "num_stacks" in effect:
                if effect["num_stacks"] == hitCount:
                    effect["on_strike_num_stacks"] = 1
                    self.onStrikeEffects.append(effect)
                elif effect["num_stacks"] == pulseCount:
                    effect["on_pulse_num_stacks"] = 1
                    self.onPulseEffects.append(effect)
                elif hitCount > 0:
                    self.onStrikeEffects.append(effect)
                elif pulseCount > 0:
                    self.onPulseEffects.append(effect)



        #if multiple damage coeffs are listed we need to manually review
        if len(self.coefficients) > 1:
            self.needsManualReview = True

    def updateCastDur(self, jsonData):
        modeSum = 0
        numSamples = 0
        for profession in jsonData["professionStats"]:
            if "mode" in jsonData["professionStats"][profession]["durations"]:
                modeSum += jsonData["professionStats"][profession]["durations"]["mode"]
                numSamples += 1

        if numSamples != 0:
            self.castDuration = modeSum / numSamples
            self.castDuration = int(40 * round(float(self.castDuration) / 40))  # round to nearest 40



