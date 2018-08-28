"""
Current beiran version constant plus version pretty-print method.
"""
from subprocess import Popen, PIPE
from os.path import abspath, dirname

from typing import Union

COMPONENTS = {
    'daemon': (0, 0, 8, 'dev', 0),
    'library': (0, 0, 8, 'dev', 0)
}


def git_sha():
    """ Git current head sha id
    Returns: git sha number

    """
    loc = abspath(dirname(__file__))
    try:
        process = Popen(
            "cd \"%s\" && git log -1 --format=format:%%h" % loc,
            shell=True,
            stdout=PIPE,
            stderr=PIPE
        )
        return process.communicate()[0]
    # OSError occurs on Unix-derived platforms lacking Popen's configured shell
    # default, /bin/sh. E.g. Android.
    except OSError:
        return None


def get_version(form: str = 'short', component: str = 'daemon') -> Union[dict, str]:
    """
    Return a version string for this package, based on `version`.

    Takes a single argument, ``form``, which should be one of the following
    strings:

    * ``branch``: just the major + minor, e.g. "0.9", "1.0".
    * ``short`` (default): compact, e.g. "0.9rc1", "0.9.0". For package
      filenames or SCM tag identifiers.
    * ``normal``: human readable, e.g. "0.9", "0.9.1", "0.9 beta 1". For e.g.
      documentation site headers.
    * ``verbose``: like ``normal`` but fully explicit, e.g. "0.9 final". For
      tag commit messages, or anywhere that it's important to remove ambiguity
      between a branch and the first final release within that branch.
    * ``all``: Returns all of the above, as a dict.
    """
    # Setup

    versions = {}
    version = COMPONENTS[component]
    branch = "%s.%s" % (version[0], version[1])
    tertiary = version[2]
    type_ = version[3]
    final = (type_ == "final")
    type_num = version[4]
    firsts = "".join([x[0] for x in type_.split()])

    # Branch
    versions['branch'] = branch

    # Short
    current_version = branch
    if tertiary or final:
        current_version += "." + str(tertiary)
    if not final:
        current_version += firsts
        if type_num:
            current_version += str(type_num)
    versions['short'] = current_version

    # Normal
    current_version = branch
    if tertiary:
        current_version += "." + str(tertiary)
    if not final and type_num:
        current_version += " " + type_ + " " + str(type_num)
    else:
        current_version += " pre-" + type_
    versions['normal'] = current_version

    # Verbose
    current_version = branch
    if tertiary:
        current_version += "." + str(tertiary)

    if not final and type_num:
        current_version += " " + type_ + " " + str(type_num)
    elif final:
        current_version += " final"
    else:
        current_version += " pre-" + type_

    versions['verbose'] = current_version

    try:
        return versions[form]
    except KeyError:
        if form == 'all':
            return versions
        raise TypeError('"%s" is not a valid form specifier.' % form)


__version__ = get_version('short')

if __name__ == "__main__":
    print({
        "Daemon": get_version('all'),
        "Client": get_version('all', 'cli')
    })
