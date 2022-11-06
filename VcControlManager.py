from VcControl import VcControl
import random

class VcControlManager():
    def __init__(self):
        self.vcControls = {} # guild.id: vcControl object

    def add(self, id: str, vcControl: VcControl):
        self.vcControls[str(id)] = vcControl
        
    def getControl(self, id):
        return self.vcControls[str(id)]
        
    def getAllControls(self):
        return self.vcControls
    
    def getRandomID(self):
        return random.randint(0, 100)