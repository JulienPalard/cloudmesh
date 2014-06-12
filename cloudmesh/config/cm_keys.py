from cloudmesh.config.cm_config import cm_config
from string import Template
from cloudmesh.util.keys import get_fingerprint
from cloudmesh.util.keys import key_fingerprint, key_validate
from cloudmesh.cm_mongo import cm_mongo
import os

class cm_keys_base:
    def type(self, name):
        try:
            if name.startswith("ssh"):
                return "string"
            else:
                return "file"
        except:
            return "keys"

    def _get_key_from_file(self, filename):
        return open(self._path_expand(os.path.expanduser(filename)),
                    "r").read()
    def _path_expand(self, text):
        """ returns a string with expanded variavble """
        template = Template(text)
        result = template.substitute(os.environ)
        result = os.path.expanduser(result)
        return result


    def fingerprint(self, name):
        value = self.__getitem__(name)
        # maxsplit set to 2, which means extra blanks (in the comment
        # field) are ignored
        t, keystring, comment = value.split(' ', 2)
        return key_fingerprint(keystring)


class cm_keys_yaml(cm_keys_base):

    filename = None

    def __init__(self, filename=None):
        """
        initializes based on cm_config and returns pointer
        to the keys dict.
        """

        # Check if the file exists
        self.config = cm_config(filename)


    def _getvalue(self, name):
        '''
        gets key corrosponding to the name
        '''

        if name == 'keys':
            return self.config.get("cloudmesh.keys")
        elif name == 'default':
            key = self.config.get("cloudmesh.keys.default")
        else:
            key = name
        value = self.config.get("cloudmesh.keys.keylist")[key]
        return value

    def get_default_key(self):
        '''
        returns the default key
        '''        
        return self.config.get("cloudmesh.keys.default")

    def __getitem__(self, name):
        '''
        gets key corrosponding to the name
        '''
        return self._getvalue(name)

    def __setitem__(self, name, value, key_type = "file"):
        '''
        adds new key name and value. If name is already present the value is changed.
        The parameter key_type should  be set to file if you want to read the key from a file.
        '''

        if key_type == "file":
            try:
                key_value = self._get_key_from_file(value)
            except:
                print "ERROR: Could not read from file. Make sure everything about the file is alright"
                return        
        else:
            print "Detected key"
            key_value = value
        self.config["cloudmesh"]["keys"]["keylist"][name] = key_value
        print "SUCCESS: key was added. name:{0}".format(name)

    def set(self, name, value, expand=False, key_type = "file"):
        '''
        adds new key name and value. If name is already present the value is changed.
        The parameter key_type should  be set to file if you want to read the key from a file.
        '''

        self.__setitem__(name, value, keytype = keytype)
        
    def __delitem__(self, name):
        '''
        deletes the key with the given name. WIll not succeed if the key is the default key
        '''    
        self.delete(name)

    def delete(self, name):
        '''
        deletes the key with the given name. WIll not succeed if the key is the default key
        '''    

        default = self.config.get("cloudmesh.keys.default")
        if name == default:
            print "ERROR: You are trying to delete the default key. Change the default key first"
            return
        else:
            if name in self.config.get("cloudmesh.keys.keylist"):
                print "Proceeding to delete key", name
                del self.config.get("cloudmesh.keys.keylist")[name]
                return "SUCCESS: Key successfully deleted"
            else:
                print "ERROR: Key not found"
                return

    def setdefault(self, name):
        """
        sets the default key
        """
        self.config["cloudmesh"]["keys"]["default"] = name

    def names(self):
        """
        returns all key names in an list.
        """
        return self.config.get("cloudmesh.keys.keylist").keys()

    def __str__(self):
        """returns the dict in a string representing the project"""
        return str(self.config)

    def fingerprint(self, name):
        value = self.__getitem__(name)
        # maxsplit set to 2, which means extra blanks (in the comment
        # field) are ignored
        t, keystring, comment = value.split(' ', 2)
        return key_fingerprint(keystring)

    def __len__(self):
        return len(self.names())

    def no_of_keys(self):
        return len(self.names())


class cm_keys_mongo(cm_keys_base):

    def __init__(self, user):
        """
        initializes based on cm_config and returns pointer
        to the keys dict.
        """
        self.mongo = cm_mongo()
        self.user_info = self.mongo.db_user.find_one(
                    {'cm_user_id': user}
        )
        self.defaults_info = self.mongo.db_defaults.find_one(
                    {'cm_user_id': user}
        )

    def _getvalue(self, name):
        """
        returns value corresponding to the name of the key.
        """
        if name == 'keys':
            return {"default": self.get_default_key(), "keylist":self.user_info["keys"]}
        if name == 'default':
            key = self.defaults_info["key"]
        else:
            key = name
        value = self.user_info["keys"][name]
        return value

    def get_default_key(self):
        """
        returns default key.
        """
        return self.defaults_info["key"]

    def __getitem__(self, name):
        """
        returns the value corresponding to the name of the key
        """        
        return self._getvalue(name)

    def __setitem__(self, name, value, persist = True, key_type="file"):
        '''
        adds new key name and value. If name is already present the value is changed.
        The parameter key_type should  be set to file if you want to read the key from a file.
        The parameter persist being set to true will cause all of the changes made locally to be written to mongo.          
        '''

        if key_type == "file":
            try:
                print "Detected file. Will try to read from file"
                value = self._get_key_from_file(value)
            except:
                print "ERROR: Could not read from file. Make sure everything about the file is alright"
                return      
        else:          
            self.user_info["keys"][name] = value
        if persist:
            self.mongo.db_user.update({'_id': self.user_info['_id']},
            {'$set': {'keys': self.user_info["keys"]}},
            upsert=False,
            multi=False
            )
        print "SUCCESS: key '{0}' was added".format(name)

    def set(self, name, value, expand=False, persist = True):
        '''
        adds new key name and value. If name is already present the value is changed.
        The parameter key_type should  be set to file if you want to read the key from a file.
        The parameter persist being set to true will cause all of the changes made locally to be written to mongo.          
        '''        
        self.__setitem__(name, value, persist= persist)

    def __delitem__(self, name, persist = True):
        '''
        deletes key with given name. Will fail if the key is the default key.
        The parameter persist being set to true will cause all of the changes made locally to be written to mongo.          
        '''
        self.delete(name, persist)

    def delete(self, name, persist = True):
        '''
        adds new key name and value. If name is already present the value is changed.
        The parameter persist being set to true will cause all of the changes made locally to be written to mongo.          
        '''
        default = self.get_default_key()
        if name == default:
            print "ERROR: You are trying to delete the default key. Change the default key first"
            return
        else:
            if name in self.user_info["keys"]:
                print "Proceeding to delete key", name
                del self.user_info["keys"][name]
            else:
                print "ERROR: Key not found"
                return
            if persist:
                self.mongo.db_user.update({'_id': self.user_info['_id']},
                {'$set': {'keys': self.user_info["keys"]}},
                upsert=False,
                multi=False
                )                
        print "SUCCESS: Key successfully deleted"

    def setdefault(self, name, persist=True):
        """
        sets the default key.
        The parameter persist being set to true will cause all of the changes made locally to be written to mongo.          
        
        """
        if name in self.user_info["keys"]:
            self.defaults_info["key"] = name
        else:
            print "ERROR: Key is not there in the key list"
            return
        if persist:
            self.mongo.db_user.update({'_id': self.user_info['_id']},
                {'$set': {'keys': self.user_info["keys"]}},
                upsert=False,
                multi=False
            )
            self.mongo.db_defaults.update({'_id': self.user_info['_id']},
                {'$set': {'key': self.defaults_info["key"]}},
                upsert=False,
                multi=False
            )
        print "SUCCESS: Defualt key modified."

    def default(self):
        """gets the default key"""
        return self.get_default_key()

    def names(self):
        """returns all key names in an list."""
        return self.user_info["keys"].keys()


    def write(self):
        """writes the updated dict to the config"""
        self.config.write()

    def __len__(self):
        return len(self.names())

    def no_of_keys(self):
        return len(self.names())




##THIS PART OF THE CODE WAS ALREADY THERE WHEN I STARTED MODIYING IT. THIS IS THE ORIGINAL VERSION



class cm_keys:

    filename = None

    def __init__(self, filename=None):
        """
initializes based on cm_config and returns pointer
to the keys dict.
"""

        # Check if the file exists
        self.config = cm_config(filename)

    def type(self, name):
        try:
            value = self._getvalue(name)
            if value.startswith("ssh"):
                return "string"
            else:
                return "file"
        except:
            return "keys"

    def _getvalue(self, name):
        if name == 'keys':
            return self.config.get("cloudmesh.keys")
        elif name == 'default':
            key = self.config.get("cloudmesh.keys.default")
        else:
            key = name
        value = self.config.get("cloudmesh.keys.keylist")[key]
        return value

    def get_default_key(self):
        return self.config.get("cloudmesh.keys.default")

    def __getitem__(self, name):
        value = self._getvalue(name)
        key_type = self.type(name)

        if key_type == "file":
            value = self._get_key_from_file(value)

        return value

    def __setitem__(self, name, value):
        if name == 'default':
            self.config["cloudmesh"]["keys"]["default"] = value
            return
        else:
            self.config["cloudmesh"]["keys"]["keylist"][name] = value

    def set(self, name, value, expand=False):
        self.__setitem__(name, value)
        if expand:
            expanded_value = self.__getitem__(name)
            self.__setitem__(name, expanded_value)
        print "EXPANDED", expanded_value

    def __delitem__(self, name):
        self.delete(name)

    def delete(self, name):
        """ not tested"""
        newdefault = False
        if name == 'default':
            key = self.config.get("cloudmesh.keys.default")
            newdefault = True
        else:
            key = name

        del self.config.get("cloudmesh.keys.keylist")[key]

        # ERROR Defalut is not self?
        if newdefault:
            if len(self.config.get("cloudmesh.keys.keylist")) > 0:
                default = self.config.get("cloudmesh.keys.keylist")[0]
        else:
            default = None

    def _path_expand(self, text):
        """ returns a string with expanded variavble """
        template = Template(text)
        result = template.substitute(os.environ)
        result = os.path.expanduser(result)
        return result

    def _get_key_from_file(self, filename):
        return open(self._path_expand(os.path.expanduser(filename)),
                    "r").read()

    def setdefault(self, name):
        """sets the default key"""
        self.config["cloudmesh"]["keys"]["default"] = name

    def default(self):
        """sets the default key"""
        return self.config.userkeys('default')

    def names(self):
        """returns all key names in an array"""
        return self.config.get("cloudmesh.keys.keylist").keys()

    def validate(self, line):
        """
validates if a default key os ok and follows
'keyencryptiontype keystring keyname'
"""

    def __str__(self):
        """returns the dict in a string representing the project"""
        return str(self.config)

    def write(self):
        """writes the updated dict to the config"""
        self.config.write()

    def fingerprint(self, name):
        value = self.__getitem__(name)
        # maxsplit set to 2, which means extra blanks (in the comment
        # field) are ignored
        t, keystring, comment = value.split(' ', 2)
        return key_fingerprint(keystring)

    def defined(self, name):
        return name in self.names()

    def __len__(self):
        return len(self.names())

    def no_of_keys(self):
        return len(self.names())
