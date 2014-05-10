import types
import textwrap
import inspect
import sys
import importlib
import simplejson as json
import time
import cmd
from bson.json_util import dumps
from cmd3.shell import command
from cloudmesh.user.cm_user import cm_user
from cloudmesh.cm_mongo import cm_mongo
from cloudmesh.config.cm_config import cm_config
from pprint import pprint
from prettytable import PrettyTable
from cloudmesh.util.logger import LOGGER
import docopt

log = LOGGER(__file__)

# BUGS:

# TODO: the try methods at the beginning should be called on teh first
# call of this method to load the data. otherwise they should not be
# called, e.g. dynamic loading

# TODO: the defaults should be read at the beginning and when any
# command is used that needs them. a logic needs to be defined so that
# defaults are included in other methods after their first loading. a
# boolean should help prevent constant reloading.

try:
    config = cm_config()
except:
    log.error("There si a problem with the configuration yaml files")
    
try:
    mongoClass = cm_mongo()
except:
    log.error("There si a problem with the mongo server")


class cm_shell_defaults:

    defDict = {}

    def _default_update(attribute, value):
        mongoClass.db_defaults.update(
            {'_id': dbDict['_id']},
            {'$set': {attribute: value}},
            upsert=False, multi=False)
    
    def createDefaultDict(self):
        # image
        # flavor
        # keyname
        # nodename
        # number of nodes


        dbDict = mongoClass.db_defaults.find_one(
            {'cm_user_id': config.username()})

        defCloud = config.default_cloud
        cmType = config.cloud(defCloud)['cm_type']

        cloudName = config.default_cloud
        self.defDict['cloud'] = cloudName
        cloudDict = config.cloud(cloudName)

        # check the flavor
        if 'flavors' in dbDict:
            if cloudName in dbDict['flavors'] and dbDict['flavors'][cloudName]:
                self.defDict['flavors'] = dbDict['flavors'][cloudName]
            else:
                print 'saving default flavor to Mongo.'
                self.defDict['flavor'] = cloudDict['default']['flavor']
                flavors = dbDict['flavors']
                flavors[cloudName] = cloudDict['default']['flavor']
                self._default_update('flavors', flavors)
        else:
            print 'Reading and saving default flavor to Mongo.'
            flavors = {}
            flavors[cloudName] = cloudDict['default']['flavor']
            self._default_update('flavors', flavors)

        # check the image
        if 'images' in dbDict:
            if cloudName in dbDict['images'] and dbDict['images'][cloudName]:
                self.defDict['image'] = dbDict['images'][cloudName]
            else:
                print 'saving default image to Mongo.'
                self.defDict['image'] = cloudDict['default']['image']
                images = dbDict['images']
                images[cloudName] = cloudDict['default']['image']
                self._default_update('images', images)
        else:
            print 'Reading and saving default image to Mongo.'
            images = {}
            images[cloudName] = cloudDict['default']['image']
            self._default_update('images', images)

        if dbDict['key']:
            self.defDict['keyname'] = dbDict['key']
        else:
            self.defDict['keyname'] = config.userkeys()['default']
            self._default_update('key', self.defDict['keyname'])

        if dbDict['prefix']:
            self.defDict['prefix'] = dbDict['prefix']
        else:
            self.defDict['prefix'] = config.username()
            self._default_update('prefix', self.defDict['prefix'])

        if dbDict['index']:
            self.defDict['index'] = dbDict['index']
        else:
            self.defDict['index'] = 1
            self._default_update('index', 1)            

        return self.defDict

    @command
    def do_defaults(self, args, arguments):
        """
        Usage:
               defaults clean
               defaults load
               defaults list [--json]
               defaults set variable value NOTIMPLEMENTED
               defaults variable  NOTIMPLEMENTED
               defaults format (json|table)  NOTIMPLEMENTED

        This manages the defaults associated with the user.
        You can load, list and clean defaults associated with
        a user and a cloud. The default parameters include
        index, prefix, flavor and image.

        Arguments:

          CLOUD          The name of Cloud - this has to be implemented

        Options:

           -j --json      json output

        Description:

          defaults set a hallo

             sets the variable a to the value hallo
             NOT YET IMPLEMENTED

          defaults a

             returns the value of the variable
             NOT YET IMPLEMENTED

          default format json
          default format table

             sets the default format how returns are printed.
             if set to json json is returned,
             if set to table a pretty table is printed
             NOT YET IMPLEMENTED
        """

        if arguments["clean"]:
            self.defDict = {}
            return

        if arguments["load"]:
            self.createDefaultDict()
            return

        if arguments["list"]:
            if arguments["--json"]:
                print json.dumps(self.defDict)
                return
            pprint(self.defDict)
            return


def main():
    print "test correct"
    defaults = cm_shell_defaults()
    defaults.createDefaultDict()
    pprint(defaults.defDict)
if __name__ == "__main__":
    main()
