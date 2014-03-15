#!/usr/bin/python

from cobbler import api as capi
from multiprocessing import Process, Queue
from functools import wraps
import os
import sys
import time
import subprocess


def authorization(func):
    """
      decorator. authorizate the user's action according to his token and current accessing API. 
    """
    @wraps(func)
    def wrap_authorization(self, *args, **kwargs):
        """
        user_token = kwargs.get("user_token", "")
        if self.validate_token(func.__name__, user_token):
            return func(self, *args, **kwargs)
        else:
            return self._simple_result_dict(False, "Authorization failed with token {0}".format(user_token))
        """
        # ONLY for debug
        # currently, NO authorization
        #print "[TEST ONLY] Authorizate function {0} ...".format(func.__name__)
        return func(self, *args, **kwargs)
    return wrap_authorization

def cobbler_object_exist(object_type, ensure_exist=True):
    """
      decorator. check whether one object exist or not in cobble.
      param ensure_exist is True means the object MUST exist, otherwise must NOT exist.
    """
    def _cobbler_object_exist(func):
        @wraps(func)
        def wrap_cobbler_object_exist(self, name, *args, **kwargs):
            flag_exist = False
            if name in self._list_item_names(object_type):
                flag_exist = True
            if ensure_exist:  # MUST exist
                if flag_exist:
                    return func(self, name, *args, **kwargs)
                else:
                    return self._simple_result_dict(False, "The name {0} in {1} does NOT exist.".format(name, object_type))
            else:  # must NOT exist
                if not flag_exist:
                    return func(self, name, *args, **kwargs)
                else:
                    return self._simple_result_dict(False, "The name {0} in {1} already exists.".format(name, object_type))
        return wrap_cobbler_object_exist
    return _cobbler_object_exist

class CobblerProvision:
    """ Stand on top of cobbler, provide simple and easy API for deploying new OS.
    
     NOTE: As described in "https://fedorahosted.org/cobbler/wiki/CobblerApi",
     Cobbler API (BootAPI) directly modifies the config store (data file) that may not be safe.
     Furthermore the modifications made will NOT be visible to cobblerd. Because cobbler
     command line depends on cobblerd. Therefore, the modification by BootAPI is NOT visible
     through command line.
     
     The strategy used here is as follows:
         (1) BootAPI can be used in reading only, MUST use multiprocessing;
         (2) Add/Modify/Remove operations are operated by shell command.
    """
    
    def __init__(self):
        pass
    
    def get_token(self, username, password):
        """ validate user, generate a token representing his rights.
        return None if user not exist or password is not correct.
         """
        return "a random valid token"
    
    def validate_token(self, access_api, user_token):
        """ validate user's token, if it is not expired, then check whether the
        user has the right to access the specific api, that is access_api, 
        if yes, return True, otherwise return False
        """
        print "user_token = {0}, access_api = {1}".format(user_token, access_api)
        return True
    
    @authorization
    def list_distro_names(self, **kwargs):
        """ 
        ONLY list distribution names, 
        """
        return self._simple_result_dict(True, data=self._list_item_names("distro"))
    
    @authorization
    def list_profile_names(self, **kwargs):
        """ 
        ONLY list profile names, 
        """
        return self._simple_result_dict(True, data=self._list_item_names("profile"))
    
    @authorization
    def list_system_names(self, **kwargs):
        """ 
        ONLY list system names, 
        """
        return self._simple_result_dict(True, data=self._list_item_names("system"))
    
    def _wrap_process_list_item_names(self, q, objects):
        cobbler_handler = capi.BootAPI()
        func = getattr(cobbler_handler, objects)
        q.put([x.name for x in func()])
    
    def _call_cobbler_process(self, func_name, *args):
        q = Queue()
        p = Process(target=getattr(self, func_name), args=(q,) + args)
        p.start()
        result = q.get()
        p.join()
        return result
    
    def _list_item_names(self, object_type):
        """ 
        ONLY list item names, called by distro, profile, system, and etc.
        return a list of object_type
        """
        return self._call_cobbler_process("_wrap_process_list_item_names", "{0}s".format(object_type))
    
    def _wrap_report_result(self, object_type, name):
        data = self._get_item_report(object_type, name)
        result = True if len(data) else False
        msg = "Success" if result else "Object {0} does NOT exist in {1}s.".format(name, object_type)
        return self._simple_result_dict(result, msg, data)
    
    @authorization
    def get_distro_report(self, name, **kwargs):
        """ 
          report the detail of the distribution with name, 
        """
        return self._wrap_report_result("distro", name)
    
    @authorization
    def get_profile_report(self, name, **kwargs):
        """ 
          report the detail of the profile with name, 
        """
        return self._wrap_report_result("profile", name)
    
    @authorization
    def get_system_report(self, name, **kwargs):
        """ 
          report the detail of the system with name, 
        """
        return self._wrap_report_result("system", name)
    
    def _wrap_process_get_item_report(self, q, object_type, name):
        cobbler_handler = capi.BootAPI()
        func = getattr(cobbler_handler, "find_{0}".format(object_type))
        result_list = []
        for item in func(name=name, return_list=True):
            data = item.to_datastruct()
            result_list.append({"type": object_type, 
                                "name": data["name"], 
                                "data": data,
                                })
        q.put(result_list)
    
    def _get_item_report(self, object_type, name):
        """
          report the specific item, called by distro, profile, system, etc.
          return correct item dict.
        """
        return self._call_cobbler_process("_wrap_process_get_item_report", object_type, name)
    
    @authorization
    def import_distro(self, name, url, **kwargs):
        """
          add a distribution to cobbler with import command.
          The first step is to fetch image file given by parameter url with wget, the url MUST be http, ftp, https.
          Then, moust the image, finally import image with cobbler import command
        """
        dir_base = "/tmp"
        dir_iso = "{0}/iso".format(dir_base)
        dir_mount = "{0}/mnt/".format(dir_iso)
        flag_result = self.mkdir(dir_mount)
        if not flag_result:
            return self._simple_result_dict(False, "User does NOT have write permission in /tmp directory.")
        # fetch image iso
        (flag_result, msg) = self.wget(url, dir_iso)
        if not flag_result:
            return self._simple_result_dict(False, msg)
        old_distro_names = self._list_item_names("distro")
        # mount image
        if self.mount_image(msg, dir_mount):
            cmd_args = ["cobbler", "import", "--path={0}".format(dir_mount), "--name={0}".format(name), ]
            flag_result = self.shell_command(cmd_args)
            self.umount_image(dir_mount)
            if not flag_result:
                return self._simple_result_dict(False, "Failed to import distro [{0}] from [{1}]".format(name, url))
            curr_distro_names = self._list_item_names("distro")
            # double check the result of import distro
            possible_names = [x for x in curr_distro_name if x not in old_distro_names and x.startswith(name)]
            distro_name = possible_names[0] if len(possible_names) else None
            return self._simple_result_dict(True if distro_name else False, "Add distro {0} {1}successfully.".format(name, "" if distro_name else "un"))
        return self._simple_result_dict(False, "Failed to mount unsupported image [{0}] in add distro {1}.".format(url, name))
    
    @cobbler_object_exist("profile", False)
    @authorization
    def add_profile(self, profile_name, *args, **kwargs):
        """
          add a new profile
        """
        if len(args) >= 2 and args[0] in self._list_item_names("distro") and self.file_exist(args[1]):
            distro_name = args[0]
            kickstart_file = args[1]
        else:
            msg = "Must provide a distribution name and a kickstart file to add profile {0}.".format(profile_name)\
                  if len(args) < 2 else "Distro {0} or kickstart file {1} to add profile {1} MUST exist.".format(args[0], args[1], profile_name)
            return self._simple_result_dict(False, msg)
        cmd_args = ["cobbler", "profile", "add", 
                    "--name={0}".format(profile_name),
                    "--distro={0}".format(distro_name), 
                    "--kickstart={0}".format(kickstart_file),
                    ]
        flag_result = self.shell_command(cmd_args)
        return self._simple_result_dict(flag_result, "Add profile {0} {1}successfully.".format(profile_name, "" if flag_result else "un"))
        
    @cobbler_object_exist("profile")
    @authorization
    def update_profile(self, profile_name, *args, **kwargs):
        """
          update the kickstart file in the profile
        """
        if len(args) > 0 and self.file_exist(args[0]):
            kickstart_file = args[0]
        else:
            msg = "Must provide a kickstart file to update profile {0}".format(profile_name) if len(args) == 0\
                  else "kickstart file {0} to update profile {1} does NOT exist.".format(args[0], profile_name)
            return self._simple_result_dict(False, msg)
        cmd_args = ["cobbler", "profile", "edit", 
                    "--name={0}".format(profile_name), 
                    "--kickstart={0}".format(kickstart_file),
                    ]
        flag_result = self.shell_command(cmd_args)
        return self._simple_result_dict(flag_result, 
                                        "update profile [{0}] with kickstart file [{1}] {2}successfully."\
                                        .format(profile_name, kickstart_file, "" if flag_result else "un")
                                        )
        
    @cobbler_object_exist("system", False)
    @authorization
    def add_system(self, system_name, contents, **kwargs):
        """
          add system to cobbler with 2 steps.
          The first step is to add a new system ONLY with system name and profile name.
          The second step is to add other contents of system.
          param interfaces is a list, each of which is a dict that has the following format.
          contents has the following formation:
          {
            name: system name,
            profile: profile name,
            gateway: default gateway,
            hostname: host name of system,
            kopts: kernel command-line arguments,
            ksmeta: kickstart meta data,
            name-servers: name servers,
            owners: users and groups,
            power: power_info,
            interfaces: [interface],
          }
          power_info has the following formation:
          {
            power-address: power IP address,
            power-type: ipmilan or etc...,
            power-user: power user,
            power-pass: power password,
            power-id: power id,
          }
          interface has the following formation:
          { name: eth0,
            ip-address: ipv4 address,
            mac-address: mac address,
            static: True | False,
            netmask: netmask of this interface,
            management: True | False,
          }
        """
        # profile must be provided to add a system
        flag_result = False
        profile_name = None
        if "profile" in contents:
            profile_name = contents["profile"]
            if profile_name in self._list_item_names("profile"):
                flag_result = True
        if not flag_result:
            return self._simple_result_dict(False, "Profile [{0}] does NOT exist.".format(profile_name) if profile_name else "Must provide a profile to add system.")
        cmd_args = ["cobbler", "system", "add", 
                    "--name={0}".format(system_name), 
                    "--profile={0}".format(profile_name), 
                    ]
        flag_result = self.shell_command(cmd_args)
        if flag_result:
            flag_result = self._edit_system(system_name, contents)
            # add others of system failed, MUST remove the added new system completely
            if not flag_result:
                self._remove_item("system", system_name)
        return self._simple_result_dict(flag_result, "Add system {0} {1}successfully.".format(system_name, "" if flag_result else "un"))
    
    @cobbler_object_exist("system")
    @authorization
    def update_system(self, system_name, contents, **kwargs):
        """
          update system with 2 steps. The first step is updating profile if needed.
          The second step is to update other objects in system.
        """
        # update profile firstly
        if "profile" in contents:
            if contents["profile"] not in self._list_item_names("profile"):
                return self._simple_result_dict(False, "Failed to update system, because profile [{0}] does NOT exist.".format(contents["profile"]))
            cmd_args = ["cobbler", "system", "edit", "--name={0}".format(system_name)]
            cmd_args += ["--profile={0}".format(contents["profile"])]
            if not self.shell_command(args):
                return self._simple_result_dict(False, "Failed to update system [{0}] with unknown error.".format(system_name))
        # update other objects in system
        flag_result = self._edit_system(system_name, contents)
        return self._simple_result_dict(flag_result, "Update system {0} {1}successfully.".format(system_name, "" if flag_result else "un"))
    
    def _edit_system(self, system_name, contents):
        """
          edit system of system_name with contents
        """
        system_args = "gateway hostname kopts ksmeta name-servers owners".split()
        power_args = "power-type power-address power-user power-pass power-id".split()
        interface_args = "ip-address mac-address netmask static management".split()
        cmd_args_edit = ["cobbler", "system", "edit", "--name={0}".format(system_name), ]
        # common system parameters
        cmd_args = cmd_args_edit + self._merge_arg_list(system_args, contents)
        # power parameters
        if "power" in contents.keys():
            cmd_args += self._merge_arg_list(power_args, contents["power"])
        all_interface_args = []
        if "interfaces" in contents:
            for interface in contents["interfaces"]:
                temp_if_args = ["--interface={0}".format(interface["name"])]
                temp_if_args += self._merge_arg_list(interface_args, interface)
                all_interface_args += [temp_if_args]
        flag_result = True
        if len(all_interface_args) > 0:
            flag_result = self.shell_command(cmd_args + all_interface_args[0])
        elif len(cmd_args) > len(cmd_args_edit):
            flag_result = self.shell_command(args)
        if flag_result:
            for interface in all_interface_args[1:]:
                flag_result = self.shell_command(cmd_args_edit + interface)
                if not flag_result:
                    break
        return flag_result
    
    @authorization
    def remove_distro(self, distro_name, **kwargs):
        """
          remove a distro
        """
        return self._remove_item("distro", distro_name)
    
    @authorization
    def remove_profile(self, profile_name, **kwargs):
        """
          remove a profile
        """
        return self._remove_item("profile", profile_name)
    
    @authorization
    def remove_system(self, system_name, **kwargs):
        """
          remove a system
        """
        return self._remove_item("system", system_name)
    
    def _remove_item(self, object_type, name):
        cmd_args = ["cobbler", object_type, "remove", "--name={0}".format(name)]
        if name in self._list_item_names(object_type):
            flag_result = self.shell_command(cmd_args)
            return self._simple_result_dict(flag_result, "The object {0} in {1} removed {2}successfully.".format(name, object_type, "" if flag_result else "un"))
        return self._simple_result_dict(True, "The name {0} in {1} does NOT exist. Not need to remove.".format(name, object_type))
    
    @cobbler_object_exist("system")
    @authorization
    def remove_system_interface(self, system_name, *args, **kwargs):
        """
         remove one or more interfaces from a system named system_name. 
         If param args contains at lease one interface name, then each of which will be removed from system.
         If param args is empty, all possible interfaces will be removed from this system.
        """
        report = self._get_item_report("system", system_name)
        all_interfaces = [x for x in report[0]["data"]["interfaces"]]
        user_delete_interfaces = list(args) if len(args) > 0 else all_interfaces
        result = {}
        if interface_name in user_delete_interfaces:
            if interface_name in all_interfaces:
                cmd_args = ["cobbler", "system", "edit", 
                            "--name={0}".format(system_name), 
                            "--interface={0}".format(interface_name), 
                            "--delete-interface", 
                            ]
                flag_result = self.shell_command(cmd_args)
                result[interface_name] = self._simple_result_dict(flag_result, 
                                                                  "Interface {0} removed {1}succefully.".format(interface_name, "" if flag_result else "un"))
            else:
                result[interface_name] = self._simple_result_dict(True, "Interface {0} does NOT exist. Not need to remove.".format(interface_name))
        return result
    
    # find system and change the netboot value if needed
    def _wrap_cobbler_find_system(self, q, name, flag_netboot):
        cobbler_handler = capi.BootAPI()
        func = getattr(cobbler_handler, "find_system")
        system = func(name)
        if flag_netboot != system.netboot_enabled:
            system.netboot_enabled = flag_netboot
            cobbler_handler.add_system(system)
        q.put(system)
        
    # power system
    def _wrap_cobbler_power_system(self, q, system, power_status):
        options = {
                    "on": "power_on",
                    "off": "power_off",
                    "reboot": "reboot",
                   }
        cobbler_handler = capi.BootAPI()
        # default action is power_on
        power_action = options.get(power_status.lower(), "power_on")
        func = getattr(cobbler_handler, power_action)
        func(system)
        q.put(power_action)
    
    @cobbler_object_exist("system")
    @authorization
    def deploy_system(self, system_name, **kwargs):
        """
         deploy a system.
        """
        system = self._call_cobbler_process("_wrap_cobbler_find_system", system_name, True)
        action = self._call_cobbler_process("_wrap_cobbler_power_system", system, "reboot")
        # monitor deploy status
        # to do ...
        return self._simple_result_dict(True, "Start to deploy system ...")
    
    @cobbler_object_exist("system")
    @authorization
    def power_system(self, system_name, **kwargs):
        """
         power on/off a system.
        """
        # get the value of 'power_on' set by user, default value is True or power ON
        power_status = "on" if kwargs.get("power_on", True) else "off"
        system = self._call_cobbler_process("_wrap_cobbler_find_system", system_name, False)
        action = self._call_cobbler_process("_wrap_cobbler_power_system", system, power_status)
        # monitor power on/off status
        # to do ...
        return self._simple_result_dict(True, "Start to power {0} system ...".format(power_status))
    
    def _simple_result_dict(self, result, msg="", data=None):
        return {"result": result, "description": msg, "data": data,}
    
    def _merge_arg_list(self, arg_list, content_dict):
        result = []
        curr_arg_list = [arg for arg in arg_list if arg in content_dict.keys()]
        for arg in curr_arg_list:
            if content_dict[arg]:
                result += ["--{0}={1}".format(arg, content_dict[arg])]
        return result
    
    def file_exist(self, filename):
        return os.path.isfile(filename)
    
    def mkdir(self, sdir):
        args = ["mkdir", "-p", sdir]
        return self.shell_command(args)
    
    def mount_image(self, image_name, location):
        args = ["mount", "-o", "loop", image_name, location]
        return self.shell_command(args)
    
    def umount_image(self, location):
        args = ["umount", "-o", "loop", location]
        return self.shell_command(args)
    
    def wget(self, url, location):
        supported_protocols = ["http", "ftp", "https",]
        supported_image = ["iso", ]
        protocol = url.split(":")[0]
        filename = url.split("/")[-1]
        filename_ext = filename.split(".")[-1]
        if protocol in supported_protocols and filename_ext in supported_image:
            args = ["wget", "-q", "-O", "{0}/{1}".format(location, filename), url,]
            if self.shell_command(args):
                result = (True, "{0}/{1}".format(location, filename))
            else:
                result = (False, "Fail to download file [{0}]".format(url))
        else:
            result = (False, "Not supported protocol [{0}] or image [{1}].".format(protocol, filename_ext))
        return result
    
    def shell_command(self, args):
        #print "==Command> ", " ".join(args)
        DEVNULL = open(os.devnull, "wb")
        return 0 == subprocess.call(args, stderr=DEVNULL, stdout=DEVNULL)

# TEST TEST TEST
if __name__ == "__main__":
    debug_status = {
                     "list_names": True,
                     "report_distro": False,
                     "report_profile": True,
                     "report_system": False,
                     "add_distro": False,
                     "add_profile": True,
                     "update_profile": True,
                     "add_system": False,
                     "update_system": False,
                     "remove_system_interface": False,
                     "remove_system": False,
                     "remove_profile": False,
                     "remove_distro": False,
                    }
    my_sys = {
               "name": "mysys140313",
               "profile": "test-profile-140313",
               "power": {
                           "power-address": "1.2.3.4",
                           "power-user": "test",
                           "power-pass": "nopassword",
                           "power-type": "ipmilan",
                           "power-id": 1,
                         },
               "interfaces": [
                               {
                                 "name": "ee1",
                                 "ip-address": "192.168.1.23",
                                 "mac-address": "aa:bb:cc:dd:ee:ff",
                                 "static": True,
                                 "management": True,
                                 "netmask": "255.255.255.0",
                                },
                              {
                                 "name": "ee2",
                                 "ip-address": "192.168.1.123",
                                 "mac-address": "aa:bb:cc:ee:dd:ff",
                                 "static": True,
                                 "management": False,
                                 "netmask": "255.255.255.0",
                                },
                              ],
              }
    my_sys_update = {
               "name": "mysys140313",
               "interfaces": [
                               {
                                 "name": "ee3",
                                 "ip-address": "192.168.1.234",
                                 "mac-address": "aa:bb:dd:dd:ee:ff",
                                 "static": True,
                                 "management": False,
                                 "netmask": "255.255.255.0",
                                },
                              ],
              }
    cp = CobblerProvision()
    user_token = cp.get_token("username", "password")
    kwargs = {"user_token": user_token}
    
    # list objects
    if debug_status["list_names"]:
        distro_names = cp.list_distro_names(**kwargs)
        print "distros names: ", distro_names["data"]
        profile_names = cp.list_profile_names(**kwargs)
        print "profiles names: ", profile_names["data"]
        system_names = cp.list_system_names(**kwargs)
        print "systems names: ", system_names["data"]
    # get object reports
    if debug_status["report_distro"]:
        # distro
        distro_name = "*x86_64"
        reports = cp.get_distro_report(distro_name)
        distros = reports["data"] if reports["result"] else []
        if len(distros) > 0:
            for distro in distros:
                print "{0} {1} {0}".format("="*10, distro["name"])
                print "distro report: {0}".format(distro)
        else:
            print "Cannot find distro with name {0}".format(distro_name)
    if debug_status["report_system"]:
        # system
        system_name = "gra*"
        reports = cp.get_system_report(system_name)
        systems = reports["data"] if reports["result"] else []
        if len(systems) > 0:
            for system in systems:
                print "{0} {1} {0}".format("="*10, system["name"])
                print "system report: {0}".format(system)
        else:
            print "Cannot find system with name {0}".format(system_name)
    
    distro_name = "test-distro-140313"
    profile_name = my_sys["profile"]
    system_name = my_sys["name"]
    # clean the test
    #cp.remove_system(system_name)
    #cp.remove_profile(profile_name)
    #cp.remove_distro(distro_name)
    
    # following is a clean test  ...
    
    # add distro
    if debug_status["add_distro"]:
        #url = "http://ftp.ussg.iu.edu/linux/ubuntu-releases/13.04/ubuntu-13.04-server-amd64.iso"
        # CentOS
        url = "http://mirrors.usc.edu/pub/linux/distributions/centos/6.5/isos/x86_64/CentOS-6.5-x86_64-bin-DVD1.iso"
        result = cp.add_distro(distro_name, url)
        print "add_distro result is: ", result
    # add profile
    if debug_status["add_profile"]:
        distro_name = "test-x86_64"
        kickstart_file = "/var/lib/cobbler/kickstarts/ktanaka.ks"
        result = cp.add_profile(profile_name, distro_name, kickstart_file)
        print "add profile, result is: ", result
    # report profile
    if debug_status["report_profile"]:
        reports = cp.get_profile_report(profile_name)
        profiles = reports["data"] if reports["result"] else []
        if len(profiles) > 0:
            for profile in profiles:
                print "{0} {1} {0}".format("="*10, profile["name"])
                print "profile report: {0}".format(profile)
        else:
            print "Cannot find profile with name {0}".format(profile_name)
    # update profile
    if debug_status["update_profile"]:
        kickstart_file = "/var/lib/cobbler/kickstarts/sample.ks"
        result = cp.update_profile(profile_name, kickstart_file)
        print "update profile, result is: ", result
    # report profile
    if debug_status["report_profile"]:
        reports = cp.get_profile_report(profile_name)
        profiles = reports["data"] if reports["result"] else []
        if len(profiles) > 0:
            for profile in profiles:
                print "{0} {1} {0}".format("="*10, profile["name"])
                print "profile report: {0}".format(profile)
        else:
            print "Cannot find profile with name {0}".format(profile_name)
    # add system
    if debug_status["add_system"]:
        result = cp.add_system(my_sys["name"], my_sys)
        print "add system, result is: ", result
    # update system
    if debug_status["update_system"]:
        result = cp.update_system(my_sys_update["name"], my_sys_update)
        print "update system, result is: ", result
    # remove a interface 
    if debug_status["remove_system_interface"]:
        system_name = my_sys_update["name"]
        interface_name = my_sys_update["interfaces"][0]["name"]
        result = cp.remove_system_interface(system_name, interface_name)
        print "remove system interface, result is: ", result
    # remove system
    if debug_status["remove_system"]:
        system_name = my_sys["name"]
        result = cp.remove_system(system_name)
        print "remove system, result is: ", result
    # remove profile
    if debug_status["remove_profile"]:
        result = cp.remove_profile(profile_name)
        print "remove profile, result is: ", result
    # remove distro
    if debug_status["remove_distro"]:
        result = cp.remove_distro(distro_name)
        print "remove distro, result is: ", result
