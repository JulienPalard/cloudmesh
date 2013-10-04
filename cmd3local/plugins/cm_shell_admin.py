import types
import textwrap
import inspect
import os
import stat
import sys
import importlib
import string
from random import choice

from jinja2 import Template
from docopt import docopt
from cmd3.shell import command
from cloudmesh.util.util import path_expand, yn_choice
from cloudmesh.user.cm_user import cm_user
from cloudmesh.iaas.openstack.cm_idm import keystone


from cloudmesh.util.logger import LOGGER

log = LOGGER(__file__)

# Helpers
def generate_password():
    """Credit: http://stackoverflow.com/questions/3854692/generate-password-in-python"""
    chars = string.letters + string.digits
    length = 12
    return ''.join([choice(chars) for _ in range(length)])

class cm_shell_admin:
    """Administrative class"""

    def __init__(self):
        self._keystones = { }
        self._cmu = None

    def activate_cm_shell_admin(self):
        pass

    def get_keystone(self, cloudname):
        if cloudname not in self._keystones:
            self._keystones[cloudname] = keystone(cloudname)
        return self._keystones[cloudname]

    def get_cm_user(self):
        if self._cmu is None:
            self._cmu = cm_user()
        return self._cmu

    def user_exists_in_cloud(self, username, cloudname):
        k = self.get_keystone(cloudname)
        k_id = k.get_user_by_name(username)
        return False
        return not k_id is None

    def get_user_profile(self, username):
        cmu = self.get_cm_user()
        profile = cmu.info(username)
        return profile

    def save_user_password(self, username, password, cloudname):
        cmu = self.get_cm_user()
        cmu.set_password(username, password, cloudname)

    def create_user_in_keystone(self, username, password, cloudname):
        k = self.get_keystone(cloudname)
        # k.create_new_user(username, password)
        print "Create user {0} in {1}".format(username, cloudname)

    def create_user_project_tenants(self, username, cloudname, projects):
        k = self.get_keystone(cloudname)
        uid = k.get_user_by_name(username)
        member_rid = k.get_role_by_name('_member_')
        for p in projects:
            tenant = k.get_tenant_by_name(p)
            if tenant is None:
                k.create_new_tenant(p)
                tenant = k.get_tenant_by_name(p)
            add_role_to_user_tenant(tenant, uid, member_rid)

    def create_user_in_cloud(self, username, password, cloudname, projects):
        self.create_user_in_keystone(username, password, cloudname)
        self.create_user_project_tenants(username, cloudname, projects)
        
    def generate_me_yaml(self, username, values, configdir):
        cmu = self.get_cm_user()
        cm_passwords = cmu.get_passwords(username)
        me_template_file = path_expand("~/.futuregrid/etc/me.yaml")
        me_template = open(me_template_file, 'r').read()
        t = Template(me_template)
        render_result = t.render(passwords=cm_passwords, **values)
        if configdir:
            # print to file
            location = path_expand('{0}/me.yaml'.format(configdir))
            f = os.open(location, os.O_CREAT | os.O_TRUNC |
                        os.O_WRONLY, stat.S_IRUSR | stat.S_IWUSR)
            os.write(f, render_result)
            os.close(f)
        else:
            print render_result


    @command
    def do_admin(self, args, arguments):
        """
        Usage:
               admin [force] newuser USERNAME CLOUDNAME [CONFIGDIR]
               
        Initializes new user in the CLOUDNAME cloud. A me.yaml
        file will be generated and placed in CONFIGDIR, or printed
        to stdout if CONDIGDIR is None.

        Arguments:

          newuser    create a new user

          USERNAME   the username of the new user

          CLOUDNAME  the name of the cloud
          
          CONFIGDIR  where to place the me.yaml file

          force      force mode does not ask. This may be dangerous.

        Options:
           
           -v       verbose mode

        """
        log.info(arguments)
        print "<", args, ">"

        if arguments["newuser"]:

            new_username = arguments["USERNAME"]
            cloudname = arguments["CLOUDNAME"]
            configdir = arguments["CONFIGDIR"]

            if self.user_exists_in_cloud(new_username, cloudname):
                print "User {0} is already created in cloud {1}".format(new_username, cloudname)
            else:
                me_values = self.get_user_profile(new_username)
                new_password = generate_password()
                self.create_user_in_cloud(new_username, new_password, cloudname, me_values['projects'])
                self.save_user_password(new_username, new_password, cloudname)
                self.generate_me_yaml(new_username, me_values, configdir)
