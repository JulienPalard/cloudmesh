# import os
from __future__ import print_function
import sys
from cloudmesh_common.logger import LOGGER
from cloudmesh.config.cm_config import cm_config
from cloudmesh.user.cm_user import cm_user
from cloudmesh.cm_mongo import cm_mongo
from cloudmesh_common.tables import row_table

from cmd3.shell import command

log = LOGGER(__file__)

class cm_shell_quota:

    """opt_example class"""
    _id = "usage"  # id for usage in cm_mongo

    def activate_cm_shell_quota(self):
        self.register_command_topic('cloud', 'quota')

    def get_cloud_name(self, cm_user_id):
        """Returns a default cloud name if exists
        """
        try:
            return self.cm_user.get_defaults(cm_user_id)['cloud']
        except KeyError:
            log.error('set a default cloud with openstack. "stack" works on'
                      ' openstack platform only')
            return None

    @command
    def do_quota(self, args, arguments):
        """
        Usage:
            quota [CLOUD]
            quota help | -h

        quota limit on a current project (tenant)

        Arguments:
          
          CLOUD          Cloud name to see the usage
          help           Prints this message

        Options:

           -v       verbose mode

        """
        self.cm_mongo = cm_mongo()
        self.cm_config = cm_config()
        self.cm_user = cm_user()

        if arguments["help"] or arguments["-h"]:
            print (self.do_quota.__doc__)
        else:
            userid = self.cm_config.username()
            def_cloud = self.get_cloud_name(userid)
            self.cm_mongo.activate(userid)
            quota = self.cm_mongo.quota(def_cloud, userid)
            print(row_table(quota, order=None, labels=["Variable", "Value"]))
            return quota
