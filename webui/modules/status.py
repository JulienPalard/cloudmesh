from flask import Blueprint
from flask import render_template, request, redirect
from cloudmesh.pbs.pbs import PBS
from cloudmesh.config.cm_config import cm_config
import cloudmesh
from flask.ext.login import login_required
from datetime import datetime

from cloudmesh.util.logger import LOGGER

log = LOGGER(__file__)

status_module = Blueprint('status_module', __name__)

#
# ROUTE: status
#


@status_module.route('/status')
@login_required
def display_status():

    msg = ""
    status = ""

    values = {
              'india' : { 'jobs' : 3, 'users' : 50},
              'bravo' : { 'jobs' : 13, 'users' : 40},
              'echo' : { 'jobs' : 23, 'users' : 30},
              'hotel' : { 'jobs' : 0, 'users' : 0},
              'sierra' : { 'jobs' : 43, 'users' : 10},
              'alamo' : { 'jobs' : 0, 'users' : 0},
              'delta' : { 'jobs' : 0, 'users': 0}
              }

    config = cm_config()
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    user = config.get("cloudmesh.hpc.username")

    services = {}
    qinfo = {}

    for host in ['sierra.futuregrid.org', 'india.futuregrid.org']:
        pbs = PBS(user, host)
        services[host] = pbs.service_distribution()
        qinfo[host] = pbs.qinfo()


    machines = services.keys()

    # print "FFF", machines

    #
    # collecting all atttributes
    #
    all_attributes = set()

    for machine in machines:
        attributes = set(list(services[machine].keys()))
        print "P", attributes
        all_attributes.update(attributes)

        # print "XXX", all_attributes

    spider_services = {'machines' : machines,
                       'categories' : list(all_attributes),
                       'data' : {}}

    #
    # seeting all attributes to 0
    #

    for machine in machines:
        ser = []
        i = 0
        for attribute in all_attributes:
            try:
                ser.append(services[machine][attribute])
            except:
                ser.append(0)
            i = i + 1
        spider_services['data'][machine] = ser

    # print "SSS", spider_services

    # Users and Jobs
    total_jobs = {}
    for machine in machines:
        for qserver in qinfo[machine]:
            total_jobs[qserver] = 0
            try:
                hostname = qserver.split('.')[0]
            except:
                hostname = ""
            for qname in qinfo[machine][qserver]:
                total_jobs[qserver] += qinfo[machine][qserver][qname]['total_jobs']
            values[hostname]['jobs'] = total_jobs[qserver]

    return render_template('status/status.html',
                           services=spider_services,
                           values=values,
                           status=status,
                           show=msg)
