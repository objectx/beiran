"""
Parse and normalize image reference
"""

from typing import Tuple

DEFAULT_DOMAIN = "docker.io"
OFFICIAL_REPO = "library"
DEFAULT_TAG = "latest"


def normalize_ref(ref: str) -> str:
    """Parse and normalize image reference.
    """
    splitted_ref = ref.split("/")
    if len(splitted_ref) == 1: # nginx, nginx:0.1
        domain = DEFAULT_DOMAIN
        path_comp = OFFICIAL_REPO
        name, sign, suffix = split_name_suffix(splitted_ref[0])

    elif len(splitted_ref) == 2: # repo/nginx, repo/nginx:0.1
        domain = DEFAULT_DOMAIN
        path_comp = splitted_ref[0]
        name, sign, suffix = split_name_suffix(splitted_ref[1])

    else:
        if is_domain(splitted_ref[0]):
            domain = splitted_ref[0]
            path_comp = "/".join(splitted_ref[1:-1])
        else:
            domain = DEFAULT_DOMAIN
            path_comp = "/".join(splitted_ref[0:-1])

        name, sign, suffix = split_name_suffix(splitted_ref[-1])

    return marshal(domain, path_comp, name, sign, suffix)


def split_name_suffix(string: str) -> Tuple[str, str, str]:
    """Split name and tag (digest)
    Args:
        string (str): must be <name>, <name>:<tag> or <name>@<digest>
    """
    sign = "@"
    splitted = string.split(sign)
    if len(splitted) != 2:
        # the string is <name>:<tag> or <name>
        sign = ":"
        splitted = string.split(sign)
        if len(splitted) == 1:
            return splitted[0], sign, DEFAULT_TAG
    return splitted[0], sign, splitted[1]


def is_domain(string: str) -> bool:
    """Judge whether or not string is domain.
    Args:
        string (str): prefix of reference (if reference is p1/p2/r/nginx, arg must be 'p1')
    """
    if ":" in string or "." in string:
        return True
    return False


def is_digest(string: str):
    """Judge whether or not string is digest.
    """
    if "@" in string:
        return True
    return False


def add_default_tag(name: str) -> str:
    """Return <name>:DEFAULT_TAG"""
    if ":" in name:
        return name
    return name + ":" + DEFAULT_TAG


def marshal(domain: str, path_comp: str, name: str, sign: str, suffix: str) -> str:
    """
    Marshall components of reference, and return normalized reference
    """
    return domain + "/" + path_comp + "/" + name + sign + suffix
