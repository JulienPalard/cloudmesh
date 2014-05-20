#!/usr/bin/env python

import sys
if not hasattr(sys, 'real_prefix'):
    print "ERROR: You are runing this script not inside a virtual machine"
    sys.exit()

try:
    from fabric.api import local, task 
except:
    os.system("pip install fabric")
    from fabric.api import local, task

import platform
import os

def is_ubuntu():
    """test sif the platform is ubuntu"""
    return platform.dist()[0] == 'Ubuntu'

def is_centos():
    """test if the platform is centos"""
    (centos, version, release) = platform.dist()
    if centos == "centos" and version != "6.4":
        print "Warning: centos %s is not tested" % version
    return centos == "centos"

def is_osx():
    return platform.system().lower() == 'darwin'

@task
def deploy():
    """deploys the system on supported distributions"""
    # download()
    (major, minor, micro, releaselevel, serial) = sys.version_info
    print "version_info", sys.version_info
    print "sys.prefix", sys.prefix
    if major != 2 or (major == 2 and minor < 7):
        print "Your version of python is not supported.  Please install python 2.7 for cloudmesh"
        sys.exit()
    if not hasattr(sys, 'real_prefix'):
        print "You do not appear to be in a vitualenv.  Please create and/or activate a virtualenv for cloudmesh installation"
        sys.exit()
    if is_ubuntu():
        ubuntu()
    elif is_centos():
        centos()
    elif is_osx():
        osx()
    else:
        print "OS distribution not supported; please see documatation for manual installation instructions."
        sys.exit()

    # install()

@task
def download():
    '''downloads cloudmesh'''
    local("git clone git@github.com:cloudmesh/cloudmesh.git")

@task
def install():
    sphinx_updates()
    local("pip install -r requirements.txt")
    local("python setup.py install")

@task
def install_mongodb():
    local("fab mongo.install")

def install_package(package):
    if is_ubuntu():
        local ("sudo apt-get -y install {0}".format(package))
    if is_centos():
        local("sudo yum -y install {0}".format(package))
    elif sys.platform == "darwin":
        print "Not yet supported"
        sys.exit()
    elif sys.platform == "win32":
        print "Windows is not supported"
        print "Use Linux instead"
        sys.exit()

@task
def install_packages(packages):
    for package in packages:
        install_package (package)

@task
def ubuntu():
    '''prepares an system and installs all 
    needed packages before we install cloudmesch'''

    local ("sudo apt-get update")
    install_packages(["python-dev",
                      "git",
                      "mercurial",
                      "curl",
                      "libldap2-dev",
                      "libsasl2-dev",
                      "libpng-dev",
                      "mongodb-server"])    
    install_packages(["rabbitmq-server"])
    install()
    install_mongodb()  # important that mongo_db installation be done only after all we install all needed python packages(as per requiremnts.txt)

def centos():
    install_packages (["git",
                       "mercurial",
                       "wget",
                       "gcc",
                       "make",
                       "readline-devel",
                       "zlib-devel",
                       "openssl-devel",
                       "openldap-devel",
                       "bzip2-devel",
                       "python-matplotlib",
                       "libpng-devel"])
    
    install_packages(["rabbitmq-server"])
    local('sudo sh -c "chkconfig rabbitmq-server on && service rabbitmq-server start"')
    install()
    install_mongodb() 

def osx():
    
    local("export CFLAGS=-Qunused-arguments")
    local("export CPPFLAGS=-Qunused-arguments")
    local('brew install wget')
    local('brew install mercurial')
    local('brew install freetype')
    local('brew install libpng')
    try:
        import numpy
        print "numpy already installed"
    except:
        local('pip install numpy')
    try:
        import matplotlib
        print "matplotlib already installed"
    except:
        local ('LDFLAGS="-L/usr/local/opt/freetype/lib -L/usr/local/opt/libpng/lib" CPPFLAGS="-I/usr/local/opt/freetype/include -I/usr/local/opt/libpng/include -I/usr/local/opt/freetype/include/freetype2" pip install matplotlib')

        # local('pip install matplotlib')
    
    install()
    install_mongodb()

def sphinx_updates():
    local('rm -rf /tmp/install-cloudmesh')
    local('mkdir -p /tmp/install-cloudmesh')
    local('cd /tmp/install-cloudmesh; hg clone http://bitbucket.org/birkenfeld/sphinx-contrib/')
    local('~/ENV/bicd /tmp/install-cloudmesh/sphinx-contrib/autorun; python setup.py install')

deploy()
