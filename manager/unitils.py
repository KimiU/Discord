import math

###############################
# unitils.py - perus työkalut #
###############################

# Tarkistaa sisältääkö viestissä koodia.
def isCode(msg):
    msg = msg.lower()
    if "```" in msg:
        return True

    keys = ["string ", "int ", "double ", "float ", "System.out"]
    for i in keys:
        if i in msg:
            return True

    for m in msg.split(' '):
        if "https" in m or "http" in m:
            if "stack" in m or \
                    "overflow" in m or \
                    "w3schools" in m or \
                    "jetbrains" in m or \
                    "code" in m or \
                    "java" in m or \
                    "c#" in m or \
                    "c++" in m or \
                    "python" in m or \
                    "javascript" in m or \
                    "programming" in m:
                return True
    return False


# Tarkistaa sisältääkö viestissä Nettix OY linkkejä.
def isNettiauto(msg):
    msg = msg.lower()
    for m in msg.split(' '):
        if "https" in m or "http" in m:
            if "nettiauto" in m or \
                    "nettimarkkina" in m or \
                    "nettimoto" in m or \
                    "nettivene" in m or \
                    "nettikone" in m or \
                    "nettivaraosa" in m or \
                    "nettivuokraus" in m or \
                    "nettimokki" in m or \
                    "nettikaravaani" in m:
                return True
    return False


# Turns seconds to hours and minutes
def convertSeconds_old(seconds):
    # hours = math.trunc(seconds / 60 / 60)
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    if hour > 0:
        return f"{hour}h {minutes}m"
    else:
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds} seconds"

def convertSeconds(timeInMilliSeconds):
    seconds = timeInMilliSeconds / 1000
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24
    if days >= 1:
        # return str(int(days)) + "days " + str(int(hours % 24)) + " hours " + str(int(minutes % 60)) + " minutes " + str(int(seconds % 60)) + " seconds"
        return str(int(hours)) + "h " + str(int(minutes % 60)) + "m"
    else:
        if hours >= 1:
            return str(int(hours)) + "h " + str(int(minutes % 60)) + "m"
        else:
            if minutes >= 1:
                return str(int(minutes)) + "m " + str(int(seconds % 60)) + "s"
            else:
                return str(int(seconds)) + "s"

# Debug tarkoitukseen
def dump(obj):
    for attr in dir(obj):
        if hasattr(obj, attr):
            print("obj.%s = %s" % (attr, getattr(obj, attr)))