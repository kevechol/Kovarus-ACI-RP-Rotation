class CiscoSecret (object):
    '''
        Cisco Password container
        keytype: 
         0     cleartext
         5     encrypted (stronger, not all CLIs support it)
         7     encrypted
    '''
    def __init__ (self, key, type=0):
        ''' default assumes key in cleartest '''
        self.set (key, type)

    def get_key (self):
        return self.key

    def get_key_type (self):
        return self.type

    def set (self, key, type=0):
        self.key = key
        self.type = type




