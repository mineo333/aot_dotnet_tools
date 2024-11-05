from binaryninja import *

#this is for working with Handles in .NET


class Handle:
    def __init__(self, value):
        self.value = value
    
    @property
    def HandleType(self):
        return HandleType(self.value >> 24)
    
    @property
    def Offset(self):
        return self.value & 0xffffff   
    
    def AsInt(self):
        return self.value
    