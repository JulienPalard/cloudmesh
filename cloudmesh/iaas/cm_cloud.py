from cloudmesh_common.logger import LOGGER
from cloudmesh.config.cm_config import cm_config
from cloudmesh.cm_mongo import cm_mongo
from tabulate import tabulate
from cloudmesh_common.util import banner, dict_uni_to_ascii
from pprint import pprint
from cloudmesh.util.menu import menu_return_num
from cloudmesh_common.bootstrap_util import yn_choice, path_expand
import sys
from cloudmesh.config.ConfigDict import ConfigDict

log = LOGGER(__file__)

def shell_command_cloud(arguments):
    """
        ::

            Usage:
                cloud
                cloud list [--column=COLUMN]
                cloud info [CLOUD|--all]
                cloud alias <name> [CLOUD]
                cloud select [CLOUD]
                cloud on [CLOUD]
                cloud off [CLOUD]
                cloud add CLOUDFILE [--force]
                cloud remove [CLOUD|--all]
                cloud default [CLOUD|--all]
                cloud setflavor [CLOUD]
                cloud setimage [CLOUD]
                cloud setdefault [CLOUD]
                
            Arguments:

              CLOUD          the name of a cloud to work on
              CLOUDFILE      a yaml file(with full file path) contains cloud information
              name           new cloud name to set

            Options:

               -v                verbose model
               --column=COLUMN   specify what information to display. For
                                 example, --column=active,label. Available
                                 columns are active, label, host, type/version,
                                 type, heading, user, credentials, defaults
                                 (all to diplay all, semiall to display all
                                 except credentials and defaults)
               --all             work on all clouds
               --force           if same cloud exists in database, it will be 
                                 overwritten

            Description:
                the place to manage clouds

                cloud list [--column=COLUMN]
                    lists the stored clouds, optionally, specify columns for more
                    cloud information. For example, --column=active,label

                cloud info [CLOUD|--all]  
                    provides the available information about the cloud in dict format 
                    options: specify CLOUD to display it, --all to display all,
                             otherwise selected cloud will be used

                cloud alias <name> [CLOUD]
                    sets a new name for a cloud
                    options: specify CLOUD to work with, otherwise selected cloud 
                             will be used

                cloud select [CLOUD]
                    selects a cloud to work with from a list of clouds if CLOUD is
                    not given

                cloud on [CLOUD]
                cloud off [CLOUD]
                    activates or deactivates a cloud, if CLOUD is not given, 
                    selected cloud will be activated or deactivated

                cloud add CLOUDFILE [--force]
                    adds cloud information to database. CLOUDFILE is a yaml file with 
                    full file path. Inside the yaml, clouds should be written in the
                    form: 
                    cloudmesh: clouds: cloud1...
                                       cloud2...
                    please check ~/.futuregrid/cloudmesh.yaml
                    options: --force, by default, existing cloud in database can't be
                             overwirtten, enable --force to overwrite if same cloud 
                             name encountered

                cloud remove [CLOUD|--all]
                    remove a cloud from mongo, if CLOUD is not given, selected cloud 
                    will be reomved.
                    CAUTION: remove all is enabled(remove --all)
                    
                cloud default [CLOUD|--all]
                cloud setflavor [CLOUD]
                cloud setimage [CLOUD]
                cloud setdefault [CLOUD]
                    view or manage cloud's default flavor and image, and set default 
                    cloud
                    options: CLOUD, specify a cloud to work on, otherwise selected 
                             cloud will be used
                             default, list default infomation of cloud, --all to 
                                      display all clouds defaults
                             setflavor, set default flaovr of a cloud
                             setimage, set default image of a cloud
                             setcloud, set default cloud

    """
    call = CloudCommand(arguments)
    call.call_procedure()
    
    
class CloudManage(object): 
    '''
    a class provides funtions used to manage cloud info in the mongo
    '''
    try:
        mongo = cm_mongo()
    except:
        log.error("There is a problem with the mongo server")
    
    
    def get_clouds(self, username, admin=False, getone=False, cloudname=None):
        '''
        retreive cloud information from db_clouds
        '''
        if getone:
            return self.mongo.db_clouds.find_one({'cm_kind': 'cloud', 'cm_user_id': username, 'cm_cloud': cloudname})
        if admin: 
            return self.mongo.db_clouds.find({'cm_kind': 'cloud'})
        else:
            return self.mongo.db_clouds.find({'cm_kind': 'cloud', 'cm_user_id': username})
        
        
    def get_selected_cloud(self, username):
        user = self.mongo.db_user.find_one({'cm_user_id': username})
        try:
            cloud = user['selected_cloud']
        except:
            defaults = self.mongo.db_defaults.find_one({'cm_user_id': username})
            try:
                cloud = defaults['cloud']
            except:
                log.warning("no selected cloud and no default cloud is setup, please use command 'cloud select [CLOUD]' to select a cloud")
                sys.exit()
            self.mongo.db_user.update({'cm_user_id': username}, {'$set': {'selected_cloud': cloud}})
        
        return cloud.encode("ascii")
    
    
    def update_selected_cloud(self, username, cloudname):
        '''
        set user selected cloud, which is current worked on cloud in the shell
        '''
        self.mongo.db_user.update({'cm_user_id': username}, {'$set': {'selected_cloud': cloudname}})
    
    
    def get_default_cloud(self, username):
        '''
        get the default cloud, return None if not set
        '''
        try:
            cloud = self.mongo.db_defaults.find_one({'cm_user_id': username})['cloud']
        except:
            cloud = None
        return cloud
    
    
    def update_default_cloud(self, username, cloudname):
        '''
        set default cloud
        '''
        self.mongo.db_defaults.update({'cm_user_id': username}, {'$set': {'cloud': cloudname}})
    
    
    def update_cloud_name(self, username, cloudname, newname):
        '''
        change the cloud name in db
        before use this function, check whether cloud exists in db_clouds
        '''
        self.mongo.db_clouds.update({'cm_kind': 'cloud', 'cm_user_id': username, 'cm_cloud': cloudname}, {'$set': {'cm_cloud': newname}})
        try:
            if cloudname == self.mongo.db_user.find_one({'cm_user_id': username})['selected_cloud']:
                self.update_selected_cloud(username, newname)
        except:
            pass
        try:
            if cloudname == self.mongo.db_defaults.find_one({'cm_user_id': username})['cloud']:
                self.update_default_cloud(username, newname)
        except:
            pass    
     
        
    def activate_cloud(self, username, cloudname):
        '''
        activate a cloud 
        '''
        cloud = self.mongo.get_cloud(cm_user_id=username, cloud_name=cloudname, force=True)
        if cloud == None:
            return 0
        else: 
            defaults = self.mongo.db_defaults.find_one({'cm_user_id': username})
            if cloudname not in defaults['registered_clouds']:
                defaults['registered_clouds'].append(cloudname)
            if cloudname not in defaults['activeclouds']:
                defaults['activeclouds'].append(cloudname)
            self.mongo.db_defaults.update({'cm_user_id': username}, defaults, upsert=True)
            return 1
    
    
    def deactivate_cloud(self, username, cloudname):
        '''
        deactivate a cloud
        simply delete the cloud name from activecloud in db_defaults
        '''
        defaults = self.mongo.db_defaults.find_one({'cm_user_id': username})
        if cloudname in defaults['activeclouds']:
            defaults['activeclouds'].remove(cloudname)
        self.mongo.db_defaults.update({'cm_user_id': username}, defaults, upsert=True)
        

    def import_cloud_to_mongo(self, d, cloudname, username):
        '''
        insert a cloud to db_clouds
        additionally, add values cm_cloud, cm_kind=cloud, cm_user_id
        before use this function, check whether cloud exists in db_clouds
        cloud name duplicate is not allowed
        '''
        if d['cm_type'] in ['openstack']:
            if d['credentials']['OS_USERNAME']:
                del d['credentials']['OS_USERNAME']
            if d['credentials']['OS_PASSWORD']:
                del d['credentials']['OS_PASSWORD']
            if d['credentials']['OS_TENANT_NAME']:
                del d['credentials']['OS_TENANT_NAME']
        elif d['cm_type'] in ['ec2', 'aws']:
            if d['credentials']['EC2_ACCESS_KEY']:
                del d['credentials']['EC2_ACCESS_KEY']
            if d['credentials']['EC2_SECRET_KEY']:
                del d['credentials']['EC2_SECRET_KEY']
        elif d['cm_type'] in ['azure']:
            if d['credentials']['subscriptionid']:
                del d['credentials']['subscriptionid']
                
        d['cm_cloud']=cloudname
        d['cm_kind']='cloud'
        d['cm_user_id']=username
        
        #remove default part from yaml
        if d['default']:
            del d['default']
                
        self.mongo.db_clouds.insert(d)


    def remove_cloud(self, username, cloudname):
        '''
        remove selected_cloud value if such cloud is removed
        [NOT IMPLEMENTED]default cloud, active cloud, register cloud too if necessary
        '''
        self.mongo.db_clouds.remove({'cm_kind': 'cloud', 'cm_user_id': username, 'cm_cloud': cloudname})
        cloud = None
        try:
            cloud = self.mongo.db_user.find_one({'cm_user_id': username})['selected_cloud']
        except:
            pass
        if cloudname == cloud:
            self.mongo.db_user.update({'cm_user_id': username}, {'$unset': {'selected_cloud': ''}})


    def get_cloud_defaultinfo(self, username, cloudname):
        '''
        return names of dfault flavor and image of a cloud, none if not exits
        '''
        res = {}
        
        flavor_id = self.get_default_flavor_id(username, cloudname)
        if flavor_id == None:
            flavorname = "none"
        else:
            try:
                flavorname = self.get_flavors(cloudname=cloudname, getone=True, id=flavor_id)['name']
            except:
                log.error("problem in retriving flavor name")
                flavorname = 'none'
        res['flavor'] = flavorname
        
        image_id = self.get_default_image_id(username, cloudname)
        if image_id == None:
            imagename = "none"
        else:
            try:
                imagename = self.get_images(cloudname=cloudname, getone=True, id=image_id)['name']
            except:
                log.error("problem in retriving image name")
                imagename = 'none'
        res['image'] = imagename
        
        return res
        
        
        
    def get_default_flavor_id(self, username, cloudname):
        '''
        return the id of the dafault flavor of a cloud
        '''
        flavor_id = None
        try:
            flavor_id = self.mongo.db_defaults.find_one({'cm_user_id': username})['flavors'][cloudname]
        except:
            pass
        return flavor_id 
    
    
    def update_default_flavor_id(self, username, cloudname, id):
        '''
        update the id of default flavor of a cloud
        '''
        self.mongo.db_defaults.update({'cm_user_id': username}, {'$set': {'flavors': {cloudname: id}}})
    
  
        
    def get_flavors(self, getall=False, cloudname=None, getone=False, id=None):
        '''
        retrieve flavor information from db_clouds
        '''
        if getone:
            return self.mongo.db_clouds.find_one({'cm_kind': 'flavors', 'cm_cloud': cloudname, 'id': id})
        elif getall:
            return self.mongo.db_clouds.find({'cm_kind': 'flavors'})
        else:
            return self.mongo.db_clouds.find({'cm_kind': 'flavors', 'cm_cloud': cloudname})
        
    
        
    def get_default_image_id(self, username, cloudname):
        '''
        return the id of the dafault image of a cloud
        '''
        image_id = None
        try:
            image_id = self.mongo.db_defaults.find_one({'cm_user_id': username})['images'][cloudname]
        except:
            pass
        return image_id 
    
    def update_default_image_id(self, username, cloudname, id):
        '''
        update the id of default image of a cloud
        '''
        self.mongo.db_defaults.update({'cm_user_id': username}, {'$set': {'images': {cloudname: id}}})
    
    
        
    def get_images(self, getall=False, cloudname=None, getone=False, id=None):
        '''
        retrieve image information from db_clouds
        '''
        if getone:
            return self.mongo.db_clouds.find_one({'cm_kind': 'images', 'cm_cloud': cloudname, 'id': id})
        elif getall:
            return self.mongo.db_clouds.find({'cm_kind': 'images'})
        else:
            return self.mongo.db_clouds.find({'cm_kind': 'images', 'cm_cloud': cloudname})

   
    # ------------------------------------------------------------------------
    # supporting functions for shell
    # ------------------------------------------------------------------------
    def print_cloud_flavors(self, username=None, cloudname=None, itemkeys=None, refresh=False, output=False):
        '''
        prints flavors of a cloud in shell
        :param username: string user name
        :param cloudname: string one cloud name
        :param itemkesys: a list of lists, each list's first item will be used as header name, the folling ones
        are the path to the value that user wants in the dict, for example:
            itemkeys = [
                         ['id', 'id'],
                         ['name', 'name'],
                         ['vcpus', 'vcpus'],
                         ['ram', 'ram'],
                         ['disk', 'disk'],
                         ['refresh time', 'cm_refrsh']
                       ]
                       first id is the header name, second id is a path
        :param refresh: refresh flavors of the cloud before printing
        :param output: designed for shell command 'cloud setflavor', output flavor names
        '''
        if refresh:
            self.mongo.activate(cm_user_id=username, names=[cloudname])
            self.mongo.refresh(cm_user_id=username, names=[cloudname], types=['flavors'])
            
        flavors_dict = self.mongo.flavors(clouds=[cloudname], cm_user_id=username)
        
        if output:
            flavor_names = []
            flavor_ids = []
            headers = ['index']
        else:
            headers = []
            
        index = 1
        to_print = []
        
        def _getFromDict(dataDict, mapList):
            #ref: http://stackoverflow.com/questions/14692690/access-python-nested-dictionary-items-via-a-list-of-keys
            return reduce(lambda d, k: d[k], mapList, dataDict)
        
        for i, v in flavors_dict[cloudname].iteritems():
            values = []
            if output:
                values.append(str(index))
                flavor_names.append(v['name'])
                flavor_ids.append(v['id'])
                
            for k in itemkeys:
                headers.append(k[0])
                try:
                    values.append(str(_getFromDict(v, k[1:])))
                except:
                    #print sys.exc_info()
                    values.append(None)
            index = index + 1
            to_print.append(values)
        
        count = index-1
        
        sentence =  "flavors of cloud '{0}'".format(cloudname)
        print "+"+"-"*(len(sentence)-2)+"+"
        print sentence
        print tabulate(to_print, headers, tablefmt="grid")
        sentence = "count: {0}".format(count)
        print sentence
        print "+"+"-"*(len(sentence)-2)+"+"
        
        if output:
            return [flavor_names, flavor_ids]
    
    
    def print_cloud_images(self, username=None, cloudname=None, itemkeys=None, refresh=False, output=False):
        '''
        refer to print_cloud_flavors
        '''
        if refresh:
            self.mongo.activate(cm_user_id=username, names=[cloudname])
            self.mongo.refresh(cm_user_id=username, names=[cloudname], types=['images'])
            
        images_dict = self.mongo.images(clouds=[cloudname], cm_user_id=username)
        
        if output:
            image_names = []
            image_ids = []
            headers = ['index']
        else:
            headers = []
            
        index = 1
        to_print = []
        
        def _getFromDict(dataDict, mapList):
            #ref: http://stackoverflow.com/questions/14692690/access-python-nested-dictionary-items-via-a-list-of-keys
            return reduce(lambda d, k: d[k], mapList, dataDict)
        
        for i, v in images_dict[cloudname].iteritems():
            values = []
            cm_type = v['cm_type']
            if output:
                values.append(str(index))
                image_names.append(v['name'])
                image_ids.append(v['id'])
                
            for k in itemkeys[cm_type]:
                headers.append(k[0])
                try:
                    values.append(str(_getFromDict(v, k[1:])))
                except:
                    #print sys.exc_info()
                    values.append(None)
            index = index + 1
            to_print.append(values)
        
        count = index-1
            
        sentence =  "images of cloud '{0}'".format(cloudname)
        print "+"+"-"*(len(sentence)-2)+"+"
        print sentence
        print tabulate(to_print, headers, tablefmt="grid")
        sentence = "count: {0}".format(count)
        print sentence
        print "+"+"-"*(len(sentence)-2)+"+"
        
        if output:
            return [image_names, image_ids]
    
    # ------------------------------------------------------------------------
    
class CloudCommand(CloudManage):
    '''
    a class provides cloud command functions
    '''
    try:
        config = cm_config()
    except:
        log.error("There is a problem with the configuration yaml files")
        
    username = config['cloudmesh']['profile']['username']
       
    def __init__(self, args):
        self.args = args
        
    def _cloud_list(self):
        if self.args["--column"]:
            if self.args["--column"] == 'all':
                col_option = ['active', 'user', 'label', 'host', 'type/version', 'type', 'heading', 'credentials', 'defaults']
            elif self.args["--column"] == 'semiall':
                col_option = ['active', 'user', 'label', 'host', 'type/version', 'type', 'heading']
            else:
                col_option = [x.strip() for x in self.args["--column"].split(',')]

            if not set(col_option).issubset(set(['active', 'label', 'host', 'type/version', 'type', 'heading', 'user', 'credentials', 'defaults'])):
                log.warning("ERROR: one or more column type doesn't exist, available columns are: active,label,host,type/version,type,heading,user,credentials,defaults  ('all' to diplay all, 'semiall' to display all except credentials and defauts)")
                return       
        else:
            col_option = ['active']
        headers = ['cloud'] + col_option
        standard_headers = []
        
        def attribute_name_map(name):
            if name == "cloud":
                return "cm_cloud"
            elif name == "label":
                return "cm_label"
            elif name == "host":
                return "cm_host"
            elif name == "type/version":
                return "cm_type_version"
            elif name == "type":
                return "cm_type"
            elif name == "heading":
                return "cm_heading"
            elif name == "user":
                return "cm_user_id"
            elif name == "credentials":
                return "credentials"
            elif name == "defaults":
                return "default"
            else:
                return name
        
        for item in headers:
            standard_headers.append(attribute_name_map(item))
            
        clouds = self.get_clouds(self.username)
        clouds = clouds.sort([('cm_cloud', 1)])
        activeclouds = self.mongo.active_clouds(self.username)
        
        to_print = []
        
        for cloud in clouds:
            res = []
            for key in standard_headers:
                # -------------------------------------------------
                # special informations from other place
                # -------------------------------------------------
                if key == "active":
                    if cloud['cm_cloud'] in activeclouds:
                        res.append('True')
                    else:
                        res.append(' ')
                elif key == "default":
                    defaultinfo = self.get_cloud_defaultinfo(self.username, cloud['cm_cloud'])
                    res.append(str(defaultinfo))
                # -------------------------------------------------
                else:
                    try:
                        res.append(str(cloud[key]))
                    except:
                        res.append(' ')
            to_print.append(res)
            
        print tabulate(to_print, headers, tablefmt="grid")
        
        if clouds.count() == 0:
            log.info("no cloud in database, please import cloud information by 'cloud add CLOUDFILE'")
        
        
    def _cloud_info(self):
        def printing(cloud):
            cloud = dict_uni_to_ascii(cloud)
            banner(cloud['cm_cloud'])
            pprint(cloud)
            # -------------------------------------------------
            # special informations from other place
            # -------------------------------------------------
            print "#", 70 * "-"
            if cloud['cm_cloud'] in self.mongo.active_clouds(self.username):
                print "active: True"
            else:
                print "active: False"
                
            defaultinfo = self.get_cloud_defaultinfo(self.username, cloud['cm_cloud'])
            print "default flavor: {0}".format(defaultinfo['flavor'])
            print "default image: {0}".format(defaultinfo['image'])
            print "#", 70 * "#", "\n"
            # -------------------------------------------------
            
        if self.args['CLOUD']:
            cloud = self.get_clouds(self.username, getone=True, cloudname=self.args['CLOUD'])
            if cloud == None:
                log.warning("ERROR: could not find cloud '{0}'".format(self.args['CLOUD']))
            else:
                printing(cloud)
        elif self.args['--all']:
            clouds = self.get_clouds(self.username)
            clouds = clouds.sort([('cm_cloud', 1)])
            if clouds.count() == 0:
                log.info("no cloud in database, please import cloud information by 'cloud add CLOUDFILE'")
                return
            for cloud in clouds:
                printing(cloud)
        else:
            selected_cloud = self.get_selected_cloud(self.username)  
            cloud = self.get_clouds(self.username, getone=True, cloudname=selected_cloud)
            if cloud == None:
                log.warning("no cloud information of '{0}' in database".format(selected_cloud))
                return
            printing(cloud)
        
        
    def _cloud_select(self):
        if self.args['CLOUD']:
            cloud = self.get_clouds(self.username, getone=True, cloudname=self.args['CLOUD'])
            if cloud == None:
                log.warning("no cloud information of '{0}' in database, please import it by 'cloud add CLOUDFILE'".format(self.args['CLOUD']))
                return
            self.update_selected_cloud(self.username, self.args['CLOUD'])
            print "cloud '{0}' is selected".format(self.args['CLOUD'])
        else:
            clouds = self.get_clouds(self.username)
            cloud_names = []
            for cloud in clouds:
                cloud_names.append(cloud['cm_cloud'].encode("ascii"))
            cloud_names.sort()
            res = menu_return_num(title="select a cloud", menu_list=cloud_names, tries=3)
            if res == 'q': return
            self.update_selected_cloud(self.username, cloud_names[res])
            print "cloud '{0}' is selected".format(cloud_names[res])
            
    def _cloud_alias(self):
        if self.args['CLOUD']:
            name = self.args['CLOUD']
        else:
            name = self.get_selected_cloud(self.username)
        if self.get_clouds(self.username, getone=True, cloudname=name) == None:
            log.error("no cloud information of '{0}' in database".format(name))
            return
        if yn_choice("rename cloud '{0}' to '{1}'?".format(name, self.args['<name>']), default = 'n', tries = 3):
            self.update_cloud_name(self.username, name, self.args['<name>'])
        else:
            return
                
    def _cloud_activate(self):
        if self.args['CLOUD']:
            name = self.args['CLOUD']
        else:
            name = self.get_selected_cloud(self.username)
        if self.get_clouds(self.username, getone=True, cloudname=name) == None:
            log.error("no cloud information of '{0}' in database".format(name))
            return
        if yn_choice("activate cloud '{0}'?".format(name), default = 'n', tries = 3):
            res = self.activate_cloud(self.username, name)
            if res == 0:
                return
            elif res == 1:
                print "cloud '{0}' activated.".format(name)
        else:
            return
        
    def _cloud_deactivate(self):
        if self.args['CLOUD']:
            name = self.args['CLOUD']
        else:
            name = self.get_selected_cloud(self.username)
        if self.get_clouds(self.username, getone=True, cloudname=name) == None:
            log.error("no cloud information of '{0}' in database".format(name))
            return
        if yn_choice("activate cloud '{0}'?".format(name), default = 'n', tries = 3):
            self.deactivate_cloud(self.username, name)
            print "cloud '{0}' deactivated.".format(name)
        else:
            return
        
    def _cloud_import(self):
        try:
            file = path_expand(self.args["CLOUDFILE"])
            fileconfig = ConfigDict(filename=file)
        except:
            log.error("ERROR: could not load file, please check filename and its path")
            return
        
        try:
            cloudsdict = fileconfig.get("cloudmesh", "clouds")
        except:
            log.error("ERROR: could not get clouds information from yaml file, please check you yaml file, clouds information must be under 'cloudmesh' -> 'clouds' -> cloud1...")
            return
        cloud_names = []
        clouds = self.get_clouds(self.username)
        for cloud in clouds:
            cloud_names.append(cloud['cm_cloud'].encode("ascii"))
        
        for key in cloudsdict:
            if key in cloud_names:
                if self.args['--force']:
                    self.remove_cloud(self.username, key)
                    self.import_cloud_to_mongo(cloudsdict[key], key, self.username)
                    print "cloud '{0}' overwritten.".format(key)
                else:
                    print "ERROR: cloud '{0}' exists in database, please remove it from database first, or enable '--force' when add".format(key)
            else:
                self.import_cloud_to_mongo(cloudsdict[key], key, self.username)
                print "cloud '{0}' added.".format(key)
                
        
    def _cloud_remove(self):
        if self.args['--all']:
            if yn_choice("!!!CAUTION!!! Remove all clouds from database?", default = 'n', tries = 3):
                cloud_names = []
                clouds = self.get_clouds(self.username)
                for cloud in clouds:
                    cloud_names.append(cloud['cm_cloud'].encode("ascii"))
                for name in cloud_names:
                    self.remove_cloud(self.username, name)
                    print "cloud '{0}' removed.".format(name)
                return
            else:
                return
                    
        if self.args['CLOUD']:
            name = self.args['CLOUD']
        else:
            name = self.get_selected_cloud(self.username)
        if self.get_clouds(self.username, getone=True, cloudname=name) == None:
            log.error("no cloud information of '{0}' in database".format(name))
            return
        if yn_choice("remove cloud '{0}' from database?".format(name), default = 'n', tries = 3):
            self.remove_cloud(self.username, name)
            print "cloud '{0}' removed.".format(name)
            return
        else:
            return
        
    def _cloud_list_default(self):
        '''
        think: refresh before list?
        '''
        headers = ['cloud', 'default flavor', 'default image']
        to_print = []
        if self.args['--all']:
            #list all clouds' default flavor and image, default cloud
            
            clouds = self.get_clouds(self.username)
            clouds = clouds.sort([('cm_cloud', 1)])
            for cloud in clouds:
                defaultinfo = self.get_cloud_defaultinfo(self.username, cloud['cm_cloud'])
                row = [cloud['cm_cloud'].encode("ascii"), defaultinfo['flavor'], defaultinfo['image']]
                to_print.append(row)
            print tabulate(to_print, headers, tablefmt="grid")
            
            current_default = self.get_default_cloud(self.username)
            sentence =  "current default cloud '{0}'".format(current_default)
            print "+"+"-"*(len(sentence)-2)+"+"
            print sentence
            print "+"+"-"*(len(sentence)-2)+"+"
        else:
            name = self.get_working_cloud_name()
            if name:
                defaultinfo = self.get_cloud_defaultinfo(self.username, name)
                to_print = [[name, defaultinfo['flavor'], defaultinfo['image']]]
                print tabulate(to_print, headers, tablefmt="grid")
            else:
                return
    
    def _cloud_set_default_cloud(self):
        name = self.get_working_cloud_name()
        if name:
            current_default = self.get_default_cloud(self.username)
            sentence =  "current default cloud '{0}'".format(current_default)
            print "+"+"-"*(len(sentence)-2)+"+"
            print sentence
            print "+"+"-"*(len(sentence)-2)+"+"
            if yn_choice("set default cloud to '{0}'?".format(name), default = 'n', tries = 3):
                self.update_default_cloud(self.username, name)
            else:
                return
        else:
            return
        
        
    def _cloud_set_flavor(self):
        '''
        refresh before actually select a flaovr of the cloud
        '''
        name = self.get_working_cloud_name()
        if name:
            itemkeys = [
                     	['id', 'id'],
                     	['name', 'name'],
                     	['vcpus', 'vcpus'],
                     	['ram', 'ram'],
                     	['disk', 'disk'],
                     	['refresh time', 'cm_refresh']
                       ]
            flavor_lists = self.print_cloud_flavors(username=self.username, cloudname=name, itemkeys=itemkeys, refresh=False, output=True)
            res = menu_return_num(title="select a flavor by index", menu_list=flavor_lists[0], tries=3)
            if res == 'q': return
            self.update_default_flavor_id(self.username, name, flavor_lists[1][res])
            print "'{0}' is selected".format(flavor_lists[0][res])
        else:
            return
        
        
    def _cloud_set_image(self):
        '''
        refresh before actually select a image of the cloud
        '''
        name = self.get_working_cloud_name()
        if name:
            itemkeys = {"openstack":
                        [
                            # [ "Metadata", "metadata"],
                            [ "name" , "name"],
                            [ "status" , "status"],
                            [ "id", "id"],
                            [ "type_id" , "metadata", "instance_type_id"],
                            [ "iname" , "metadata", "instance_type_name"],
                            [ "location" , "metadata", "image_location"],
                            [ "state" , "metadata", "image_state"],
                            [ "updated" , "updated"],
                            #[ "minDisk" , "minDisk"],
                            [ "memory_mb" , "metadata", 'instance_type_memory_mb'],
                            [ "fid" , "metadata", "instance_type_flavorid"],
                            [ "vcpus" , "metadata", "instance_type_vcpus"],
                            #[ "user_id" , "metadata", "user_id"],
                            #[ "owner_id" , "metadata", "owner_id"],
                            #[ "gb" , "metadata", "instance_type_root_gb"],
                            #[ "arch", ""]
                        ],
                      "ec2":
                        [
                            # [ "Metadata", "metadata"],
                            [ "state" , "extra", "state"],
                            [ "name" , "name"],
                            [ "id" , "id"],
                            [ "public" , "extra", "is_public"],
                            [ "ownerid" , "extra", "owner_id"],
                            [ "imagetype" , "extra", "image_type"]
                        ],
                      "azure":
                        [
                            [ "name", "label"],
                            [ "category", "category"],
                            [ "id", "id"],
                            [ "size", "logical_size_in_gb" ],
                            [ "os", "os" ]
                        ],
                      "aws":
                        [
                            [ "state", "extra", "state"],
                            [ "name" , "name"],
                            [ "id" , "id"],
                            [ "public" , "extra", "ispublic"],
                            [ "ownerid" , "extra", "ownerid"],
                            [ "imagetype" , "extra", "imagetype"]
                        ]
                     }
            image_lists = self.print_cloud_images(username=self.username, cloudname=name, itemkeys=itemkeys, refresh=False, output=True)
            res = menu_return_num(title="select a image by index", menu_list=image_lists[0], tries=3)
            if res == 'q': return
            self.update_default_image_id(self.username, name, image_lists[1][res])
            print "'{0}' is selected".format(image_lists[0][res])
        else:
            return
     
        
        
        
        
    # --------------------------------------------------------------------------
    def get_working_cloud_name(self):
        '''
        get the name of a cloud to be work on, if CLOUD not given, will pick the
        elected cloud
        '''
        if self.args['CLOUD']:
            name = self.args['CLOUD']
        else:
            name = self.get_selected_cloud(self.username)
        if self.get_clouds(self.username, getone=True, cloudname=name) == None:
            log.error("no cloud information of '{0}' in database".format(name))
            return False
        return name

    def call_procedure(self):
        #print self.args ###########
        if self.args['list'] == True:
            call = 'list'
        elif self.args['info'] == True:
            call = 'info'
        elif self.args['alias'] == True:
            call = 'alias'
        elif self.args['select'] == True:
            call = 'select'
        elif self.args['on'] == True:
            call = 'activate'
        elif self.args['off'] == True:
            call = 'deactivate'
        elif self.args['add'] == True:
            call = 'import'
        elif self.args['remove'] == True:
            call = 'remove'
        elif self.args['default'] == True:
            call = 'list_default'
        elif self.args['setflavor'] == True:
            call = 'set_flavor'
        elif self.args['setimage'] == True:
            call = 'set_image'
        elif self.args['setdefault'] == True:
            call = 'set_default_cloud'
        else:
            call = 'list'
        func = getattr(self, "_cloud_" + call)
        func()
    
    
# ------------------------------------------------------------------------
# supporting functions 
# ------------------------------------------------------------------------
  

# ------------------------------------------------------------------------

