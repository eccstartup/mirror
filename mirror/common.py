#
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# mirror is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mirror. If not, write to:
#   The Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor
#   Boston, MA  02110-1301, USA.
#
#


"""Common functions for Mirror :("""

import os, sys
import time
import logging
import pkg_resources
import gettext
import locale

from mirror.error import *

log = logging.getLogger(__name__)

def get_version():
    """
    Returns the version of mirror from the python egg metadata

    :returns: the version of mirror

    """
    return pkg_resources.require("mirror")[0].version

def get_default_config_dir(filename=None):
    """
    :param filename: if None, only the config directory path is returned,
                     if provided, a path including the filename will be returned
    :type  filename: string
    :returns: a file path to the config directory and optional filename
    :rtype: string

    """

    from xdg.BaseDirectory import save_config_path
    if not filename:
        filename = ''
    try:
        return os.path.join(save_config_path("mirror"), filename)
    except OSError, e:
        log.error("Unable to use default config directory, exiting... (%s)", e)
        sys.exit(1)

def setup_translations():
    translations_path = resource_filename("mirror", "i18n")
    log.info("Setting up translations from %s", translations_path)

    try:
        if hasattr(locale, "bindtextdomain"):
            locale.bindtextdomain("mirror", translations_path)
        if hasattr(locale, "textdomain"):
            locale.textdomain("mirror")
        gettext.install("mirror", translations_path, unicode=True)
    except Exception, e:
        log.error("Unable to initialize gettext/locale")
        log.exception(e)
        import __builtin__
        __builtin__.__dict__["_"] = lambda x: x

def resource_filename(module, path):
    return pkg_resources.require("mirror>=%s" % get_version())[0].get_resource_filename(
        pkg_resources._manager, os.path.join(*(module.split('.')+[path]))
    )

def check_mirrord_running(pidfile):
    pid = None
    if os.path.isfile(pidfile):
        try:
            pid = int(open(pidfile).read().strip())
        except:
            pass

    def is_process_running(pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    if pid and is_process_running(pid):
        raise MirrordRunningError("Another mirrord is running with pid: %d", pid)

def lock_file(pidfile):
    """Actually the code below is needless..."""

    import fcntl
    try:
        fp = open(pidfile, "r+" if os.path.isfile(pidfile) else "w+")
    except IOError:
        raise MirrorError("Can't open or create %s", pidfile)

    try:
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        try:
            pid = int(fp.read().strip())
        except:
            raise MirrorError("Can't lock %s", pidfile)
        raise MirrorError("Can't lock %s, maybe another mirrord with pid %d is running",
                              pidfile, pid)

    fcntl.fcntl(fp, fcntl.F_SETFD, 1)
    fp.seek(0)
    fp.write("%d\n" % os.getpid())
    fp.truncate()
    fp.flush()

    # We need to return fp to keep a reference on it
    return fp

def find_rsync():
    """Find the path of rsync.

    :returns: the path of rsync or None if not found

    """
    paths = os.getenv("PATH").split(":")
    for path in paths:
        rsync = (path if path.endswith('/') else path + '/') + "rsync"
        if os.path.isfile(rsync):
            return rsync
    return None

def parse_timeout(timeout):
    """Parse timeout expression, e.g. 12h17m, 12h, 17m

    :returns: the seconds represented by timeout, or 0 if timeout is not valid

    """
    try:
        return int(timeout)
    except:
        pass
    h = timeout.find('h')
    m = timeout.find('m')
    if h > 0 or m > 0:
        try:
            return ((int(timeout[:h]) * 3600 if h > 0 else 0) 
                   + (int(timeout[h+1:m]) * 60 if m > 0 else 0))
        except:
            return 0
    else:
        return 0
