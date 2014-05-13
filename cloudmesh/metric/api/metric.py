import sys
from tabulate import tabulate

class metric_api:

    def __init__(self):
        self.from_date = None
        self.to_date = None
        self.period = None
        self.metric = None
        self.cluster = None
        self.iaas = None
        self.user = None

    def __str__(self):
        result = ""
        result += "from_date: %s\n" % self.from_date
        result += "to_date:   %s\n" % self.to_date
        result += "period:    %s\n" % self.period
        result += "metric:    %s\n" % self.metric
        result += "cluster:   %s\n" % self.cluster
        result += "iaas:      %s\n" % self.iaas
        result += "user:      %s\n" % self.user
        return result
    
    def set_date(self, from_date, to_date):
        self.from_date = from_date
        self.to_date = to_date

    def set_period(self, period):
        self.period = period

    def set_metric(self, metric):
        self.metric = metric

    def set_cluster(self, cluster):
        self.cluster = cluster

    def set_iaas(self, cloud):
        self.iaas = cloud

    def set_cloud(self, cloud):
        ''' link to set_iaas '''
        self.set_iaas(cloud)

    def set_user(self, user):
        self.user = user

    def get_raw_data(self):
        # something from the server
        # for test dummy data
        res = [["HOST", "PROJECT", "cpu", "memory_mb", "disk_gb"],
               ["india","(total)",2, 4003,157],
               ["india","(used_now)", 3, 5120, 40],
               ["india","(used_max)",3,4608, 40],
                ["india","b70d90d65e464582b6b2161cf3603ced",1,512,0],
                ["india","66265572db174a7aa66eba661f58eb9e",2,4096,40]]
        self.raw_data = res

    def display(self, table_format="grid"):
        # table_format = 
        # plain,
        # simple,
        # grid,
        # pipe,
        # orgtbl,
        # rst,
        # mediawiki,
        # latex
        self.table = tabulate (self.raw_data, headers="firstrow", tablefmt=table_format)
        print self.table
        
    def get_stats(self):
        #print vars(self)
        self.get_raw_data()
        self.display("grid")
        return

    def stats(self):
        ''' link to get_stats '''
        return self.get_stats()
