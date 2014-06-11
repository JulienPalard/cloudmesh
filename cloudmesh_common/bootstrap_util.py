"""Bootstrap Cloudmesh finctions.

This file contains basic utility functions that must not need any
import from cloudmesh OR any other non-standard python
modules. Everything in this file must execute on a clean python 2.7.x
environment.

"""
from string import Template
import os


def grep(pattern, filename):
    """Very simple grep that returns the first matching line in a file.

    String matching only, does not do REs as currently implemented.
    """
    try:
        return (L for L in open(filename) if L.find(pattern) >= 0).next()
    except StopIteration:
        return ''


def banner(txt=None, c="#"):
    """prints a banner of the form with a frame of # arround the txt::

      ############################
      # txt
      ############################

    .

    :param txt: a text message to be printed
    :type txt: string
    :param c: thecharacter used instead of c
    :type c: character
    """
    print
    print "#", 70 * c
    if txt is not None:
        print "#", txt
        print "#", 70 * c


def path_expand(text):
    """ returns a string with expanded variable.

    :param text: the path to be expanded, which can include ~ and $ variables
    :param text: string

    """
    template = Template(text)
    result = template.substitute(os.environ)
    result = os.path.expanduser(result)
    return result


def yn_choice(message, default='y', tries=None):
    """asks for a yes/no question.
    :param message: the message containing the question
    :param default: the default answer
    """
    # http://stackoverflow.com/questions/3041986/python-command-line-yes-no-input"""
    choices = 'Y/n' if default.lower() in ('y', 'yes') else 'y/N'
    if tries == None:
        choice = raw_input("%s (%s) " % (message, choices))
        values = ('y', 'yes', '') if default == 'y' else ('y', 'yes')
        return True if choice.strip().lower() in values else False
    else:
        while tries > 0:
            choice = raw_input("%s (%s) " % (message, choices))
            choice = choice.strip().lower()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            else:
                print "Invalid input..."
                tries = tries - 1
