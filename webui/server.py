from ConfigParser import SafeConfigParser
from cloudmesh.provisioner.provisioner import *
from cloudmesh.config.cm_config import cm_config
from cloudmesh.util.webutil import setup_imagedraw
from cloudmesh.util.util import address_string
from cloudmesh.cloudmesh_mongo import cloudmesh_mongo
from datetime import datetime
from flask import Flask, render_template, flash, send_from_directory
#from flask.ext.autoindex import AutoIndex
from flask_flatpages import FlatPages
#from pprint import pprint
import os
import pkg_resources
import sys
import types



sys.path.insert(0, '.')
sys.path.insert(0, '..')


# ============================================================
# DYNAMIC MODULE MANAGEMENT
# ============================================================

all_modules = ['pbs',
               'flatpages',
               'nose',
               'inventory',
               'provisioner',
               'keys',
               'menu',
               'profile',
               'git',
               'cloud',
               'workflow']

exclude_modules = ['workflow', 'cloud']

modules = [m for m in all_modules if m not in exclude_modules]
    
for m in modules:
    print "Loading module", m
    exec "from modules.{0} import {0}_module".format(m)


# ============================================================
# DYNAMIC MODULE MANAGEMENT
# ============================================================

debug = True

with_cloudmesh = False

# not sure what this is for ?????
server_config = SafeConfigParser(
    {'name': 'flasktest'})  # Default database name
server_config.read("server.config")

# ============================================================
# allowing the yaml file to be written back upon change
# ============================================================

with_write = True

# ============================================================
# setting up reading path for the use of yaml
# ============================================================

default_path = '.futuregrid/cloudmesh.yaml'
home = os.environ['HOME']
filename = "%s/%s" % (home, default_path)

# ============================================================
# global vars
# ============================================================

SECRET_KEY = 'development key'
DEBUG = debug
FLATPAGES_AUTO_RELOAD = debug
FLATPAGES_EXTENSION = '.md'



# ============================================================
# STARTING THE FLASK APP
# ============================================================

app = Flask(__name__)
app.config.from_object(__name__)
app.debug = debug
pages = FlatPages(app)


# dynamic app loading from defined modules
# app.register_blueprint(keys_module, url_prefix='',)

for m in modules:
    print "Loading module", m
    exec "app.register_blueprint({0}_module, url_prefix='',)".format(m)


app.secret_key = SECRET_KEY

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))
            
# @app.context_processor
# def inject_pages():
#    return dict(pages=pages)
# app.register_blueprint(menu_module, url_prefix='/', )
# if debug:
#    AutoIndex(app, browse_root=os.path.curdir)

# ============================================================
# VERSION
# ============================================================

version = pkg_resources.get_distribution("cloudmesh").version

@app.context_processor
def inject_version():
    return dict(version=version)

# ============================================================
# ROUTE: mongo
# ============================================================

@app.route('/mongo/flavors')
def mongo_flavors():
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    #filter()
    config = cm_config()
    
    c = cloudmesh_mongo()
    c.activate()
    clouds=c.flavors()
    
    """    
    2
    disk 20
    name m1.small
    links [{u'href': u'http://198.202.120.83:8774/v1.1/1ae6813a3a6d4cebbeb1912f6d139ad0/flavors/2', u'rel': u'self'}, {u'href': u'http://198.202.120.83:8774/1ae6813a3a6d4cebbeb1912f6d139ad0/flavors/2', u'rel': u'bookmark'}]
    OS-FLV-EXT-DATA:ephemeral 0
    ram 2048
    cm_refresh 2013-08-06T21-44-13Z
    OS-FLV-DISABLED:disabled False
    cm_id sierra-openstack-grizzly-flavors-m1-small
    vcpus 1
    cm_cloud sierra-openstack-grizzly
    swap 
    os-flavor-access:is_public True
    rxtx_factor 1.0
    cm_kind flavors
    _id 5201a66d7df38caf0fe160bc
    cm_type openstack
    id 2
    """


    for cloud in clouds:
        print cloud
        for flavor in clouds[cloud]:
            print flavor
            for attribute in clouds[cloud][flavor]:
                print attribute, clouds[cloud][flavor][attribute]

    os_attributes = [
                     'id',
                     'name',
                     'vcpus',
                     'ram',
                     'disk',
                     'cm_refresh',
                     ]
    
    return render_template('mongo_flavors.html',
                           address_string=address_string,
                           attributes=os_attributes,
                           updated=time_now,
                           clouds=clouds,
                           config=config)

# ============================================================
# ROUTE: mongo
# ============================================================

@app.route('/mongo')
def mongo_table():
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    #filter()
    config = cm_config()
    
    c = cloudmesh_mongo()
    c.activate()
    clouds=c.servers()
    
    """
    for cloud in clouds:
        print cloud
        for server in clouds[cloud]:
            print server
            for attribute in clouds[cloud][server]:
                print attribute, clouds[cloud][server][attribute]
    """
    os_attributes = ['name','addresses','flavor','id','user_id','metadata','key_name','created']
    
    return render_template('mongo.html',
                           address_string=address_string,
                           attributes=os_attributes,
                           updated=time_now,
                           clouds=clouds,
                           config=config)
# ============================================================
# ROUTE: sitemap
# ============================================================

"""
@app.route("/site-map/")
def site_map():
    links = []
    for rule in app.url_map.iter_rules():
        print"PPP>",  rule, rule.methods, rule.defaults, rule.endpoint, rule.arguments
        # Filter out rules we can't navigate to in a browser
        # and rules that require parameters
        try:
            if "GET" in rule.methods and len(rule.defaults) >= len(rule.arguments):
                url = url_for(rule.endpoint)
                links.append((url, rule.endpoint))
                print "Rule added", url, links[url]
        except:
            print "Rule not activated"
    # links is now a list of url, endpoint tuples
"""


# ============================================================
# ROUTE: /
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

# @app.route('/workflow')
# def display_diagram():
#    return render_template('workflow.html')



# ============================================================
# ROUTE: LOGIN
# ============================================================


@app.route('/login')
def login():
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template('login.html',
                           updated=time_now)
                           

# ============================================================
# ROUTE: workflows
# ============================================================


@app.route('/workflows/<filename>')
def retrieve_files(filename):
    """    Retrieve files that have been uploaded    """
    return send_from_directory('workflows', filename)


# ============================================================
# FILTER: timesince
# ============================================================

@app.template_filter()
def timesince(dt, format="float", default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """
    if dt == "None" or dt == "" or dt == None or dt == "completed":
        return "completed"
    
    # now = datetime.utcnow()
    now = datetime.now()
    if format == 'float':
        diff = now - datetime.fromtimestamp(dt)
    else:
        diff = now - dt
        
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)

    return default

# ============================================================
# FILTER: get_tuple element from string
# ============================================================

@app.template_filter()
def get_tuple_element_from_string(obj, i):
    l = obj[1:-1].split(", ")
    return l[i][1:-1]

# ============================================================
# FILTER: is list
# ============================================================

@app.template_filter()
def is_list(obj):
    return isinstance(obj, types.ListType)

# ============================================================
# FILTER: only numbers
# ============================================================

@app.template_filter()
def only_numbers(str):
    return ''.join(c for c in str if c.isdigit())

# ============================================================
# FILTER: simple_data, cuts of microseconds
# ============================================================

@app.template_filter()
def simple_date(d):
    return str(d).rpartition(':')[0]

# ============================================================
# FILTER: state color
# ============================================================

@app.template_filter()
def state_color(state):
    s = state.lower()
    if s == "active":
        color = "#336600"
    else:
        color = "#FFCC99"
    return color

# ============================================================
# FILTER: state style
# ============================================================

@app.template_filter()
def state_style(state):
    color = state_color(state)
    return 'style="background:{0}; font:bold"'.format(color)


# ============================================================
# ROUTE: PAGES
# ============================================================


@app.route('/<path:path>/')
def page(path):
    page = pages.get_or_404(path)
    return render_template('page.html', page=page)


if __name__ == "__main__":
    setup_imagedraw()
    # setup_plugins()
    # setup_noderenderers()
    app.run()
