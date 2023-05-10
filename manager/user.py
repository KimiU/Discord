import json
import os
import time
import discord

from manager import unitils

directory = "./data/users/"


class User:
    default_xp = 250
    level = 1
    xp = 0
    time = 0
    current = 0

    stopped_time = 0

    @classmethod
    async def get_all_users(cls, client):
        users = []

        if not os.path.exists(directory):
            return users

        for file_name in os.listdir(directory):
            if file_name.endswith(".json"):
                with open(os.path.join(directory, file_name), "r") as file:
                    data = json.load(file)
                    discord_user = client.get_user(data["id"])
                    if discord_user is None:
                        try:
                            discord_user = await client.fetch_user(data["id"])
                        except discord.NotFound:
                            print(f"User not found with ID {data['id']}")
                            continue

                    user = cls(discord_user)
                    users.append(user)
                    print(f"Loaded user {user.username}#{user.tag} | Time: {user.getTimeFormatted()}")

        return users

    # Runs on User call.
    def __init__(self, user):
        self.user_id    = user.id
        self.username   = user.name
        self.tag        = user.discriminator

        if self.isUser():
            self.loadUser()
            self.max_xp = self.getMaxXP()
        else:
            self.createUser()
            self.max_xp = self.default_xp

    # get user data from json file.
    def loadUser(self):
        with open(directory + str(self.user_id) + '.json', 'r') as file:
            f = json.loads(file.read())
            self.level = f['progression']['level']
            self.xp = f['progression']['xp']
            self.time = f['time']['seconds']
            self.current = f['time']['current']

    # Saves user data to a existing json file.
    def saveUser(self):
        data = {
            'id': self.user_id,
            "username": self.username,
            "tag": self.tag,
            "progression": {
                "level": self.level,
                "xp": self.xp
            },
            "time": {
                "seconds": self.time,
                "current": self.current
            }
        }
        with open(directory + str(self.user_id) + '.json', 'w') as file:
            json.dump(data, file)

    # Create json file of the user if does not exist.
    def createUser(self):
        self.level = 1
        self.xp = 0
        self.time = 0
        self.saveUser()

    # Check if user exist
    def isUser(self):
        if not os.path.exists(directory):
            os.makedirs(directory)
        return os.path.exists(directory + str(self.user_id) + ".json")

    # Time handling
    def getTime(self):
        return self.time

    def getTimeFormatted(self):
        return unitils.convertSeconds(self.time)

    def addTime(self, t):
        self.time = self.getTime() + t

    # Level handing
    def getLevel(self):
        return self.level

    # XP Handling
    def getXP(self):
        return self.xp

    def addXP(self, xp):
        self.xp = self.getXP() + xp

    def setXP(self, xp):
        self.xp = xp

    def getMaxXP(self):
        return self.getMaxXPByLevel()

    def getMaxXPByLevel(self):
        return self.default_xp + 50 * self.level

    # Leveling handler
    def levelUp(self):
        max_xp = self.getMaxXP()
        if self.getXP() >= max_xp:
            self.setXP(self.xp - max_xp)
            self.level = self.level + 1

    def checkLevel(self):
        max_xp = self.getMaxXP()
        if self.getXP() >= max_xp:
            self.levelUp()
            self.checkLevel()
        else:
            self.saveUser()

    def startTime(self):
        self.current = int(round(time.time() * 1000))
        self.saveUser()

    def stopTime(self):
        self.stopped_time = int((int(round(time.time() * 1000)) - self.current))
        self.addTime(self.stopped_time)

        mins = int(self.stopped_time / 1000 / 60)
        if mins > 0:
            self.addXP(mins)

        self.checkLevel()

        self.current = 0
        self.saveUser()

    def getStoppedTime(self):
        return self.stopped_time
    
    def getCurrentMillis(self):
        return self.current
    
    def getCurrentCallTime(self):
        return int((int(round(time.time() * 1000)) - self.current))
    
    def getCurrentCallTimeFormatted(self):
        return unitils.convertSeconds(int((int(round(time.time() * 1000)) - self.current)))
