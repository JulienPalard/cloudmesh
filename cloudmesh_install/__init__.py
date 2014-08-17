"""Common methods and classes used at the intall time."""
import sys
from cloudmesh_common.bootstrap_util import path_expand


_config_dir_prefix__ = "~/.futuregrid"

__config_dir__ = path_expand(_config_dir_prefix__)


def config_file(filename):
    return __config_dir__ + filename

def config_file_prefix():
    return __config_dir_prefix__ 

