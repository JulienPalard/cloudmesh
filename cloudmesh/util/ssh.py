import sys
sys.stderr = open('/dev/null')       # Silence silly warnings from paramiko
import paramiko as pm
sys.stderr = sys.__stderr__
#import os
import ast
import re
import os

''' Contains the ssh class. Can be used in casews when you want the output of an ssh call but need to do steps before and after the call
as part of the ssh session''' 

class AllowAllKeys(pm.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        return
    
class ssh:
    def __init__(self,host,username,password='') :
        self.host = host#'jedi000.cc.gatech.edu'
        self.username = username#'hlee676'
        self.password = password#''
        self.setup()
        
    def setup(self):
        self.client = pm.SSHClient()
        self.client.load_system_host_keys()
        self.client.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        self.client.set_missing_host_key_policy(AllowAllKeys())
        self.client.connect(self.host, username=self.username, password=self.password)
    
    def ssh_session(self,command,init=None,exit=None):
        channel = self.client.invoke_shell()
        stdin = channel.makefile('wb')
        stdout = channel.makefile('rb')
        query = ""
        if init != None:
            query += init + "\n"
        query += command
        if exit != None:
            query+="\n"+exit+"\n"
        #bash\ncm list flavors jedi\nexit\nexit
        #print query
        stdin.write(query)
        output = stdout.read()
        #print output
        if init != None:
            output = re.split(command,output)
            output = output[1]
        if exit != None:
            exit = exit.split("\n")
            exit = exit[0]
            output = re.split(".*"+exit,output)
        output = output[0]
        stdout.close()
        stdin.close()
        return output
    
    def destroy(self):    
        self.client.close()
