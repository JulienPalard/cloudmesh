import envoy
from flask import Blueprint
from flask import render_template
from sh import git
from cloudmesh.util.gitinfo import GitInfo
from pprint import pprint
from flask.ext.login import login_required


from cloudmesh.util.logger import LOGGER

log = LOGGER(__file__)

git_module = Blueprint('git_module', __name__)


@git_module.route('/git')
@login_required
def display_git_authors():
    result = git("shortlog", "-s", "-n",
                 _tty_in=True, _tty_out=False).split("\n")
    authors = {}
    for line in result:
        print line
        try:
            (commits, name) = line.split("\t")
            authors[name] = {"name": name, "commits": commits}
        except:
            print "error:", line

    result = envoy.run('git log --all --format=\"%aN <%cE>\" | sort -u')
    print result.std_out

    """
    gitinfo = GitInfo()

    # print gitinfo.version()

    print "A"
    print gitinfo.authors()

    print "b"
    pprint(gitinfo.authors("dict"))

    print "c"
    pprint(gitinfo.emails())

    print "d"
    pprint(gitinfo.emails("dict"))

    print "e"
    pprint(gitinfo.info())

    print "f"
    print gitinfo.stat("laszewski@gmail.com")

    print "g"
    stats = gitinfo.compute()

    print stats

    print "h"
    for email in stats:
        p = stats[email]["percentage"]
        print "{0} {1:.3f}% {2:.3f}%  {3:.3f}% {4:.3f}%".format(email, p[0], p[1], p[2], p[3])
    """

    return render_template('general/git.html',
                           authors=authors)
