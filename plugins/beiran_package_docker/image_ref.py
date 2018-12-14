"""
Parse and normalize image reference
"""

from typing import Tuple

DEFAULT_DOMAIN = "docker.io"
DEFAULT_INDEX_DOMAIN = "index.docker.io"
OFFICIAL_REPO = "library"
DEFAULT_TAG = "latest"

ID_PREFIX = "sha256:"


def normalize_ref(ref: str, **kwargs) -> dict:
    """Parse and normalize image reference as a dictionaly
    """
    domain = DEFAULT_DOMAIN
    if 'index' in kwargs and kwargs['index']:
        domain = DEFAULT_INDEX_DOMAIN
    path_comp = ''

    splitted_ref = ref.split("/")
    if len(splitted_ref) == 1: # nginx, nginx:0.1
        name, sign, suffix = split_name_suffix(splitted_ref[0])
        path_comp = OFFICIAL_REPO

    elif len(splitted_ref) == 2: # repo/nginx, repo/nginx:0.1, domain/nginx
        if is_domain(splitted_ref[0]):
            domain = splitted_ref[0]

            if domain == DEFAULT_DOMAIN:
                path_comp = OFFICIAL_REPO

        else:
            path_comp = splitted_ref[0]
        name, sign, suffix = split_name_suffix(splitted_ref[1])

    else:
        if is_domain(splitted_ref[0]):
            domain = splitted_ref[0]
            path_comp = "/".join(splitted_ref[1:-1])
        else:
            path_comp = "/".join(splitted_ref[0:-1])

        name, sign, suffix = split_name_suffix(splitted_ref[-1])


    if path_comp == '':
        repo = name
    else:
        repo = path_comp + '/' + name

    return {
        'domain': domain,
        'repo': repo,
        'sign': sign,
        'suffix': suffix
    }

def marshal_normalize_ref(ref: str, **kwargs) -> str:
    """Parse and normalize image reference as a string
    """
    normalized = normalize_ref(ref, **kwargs)
    return marshal(normalized['domain'], normalized['repo'],
                   normalized['sign'], normalized['suffix'])


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

def is_tag(string: str):
    """Judge whether or not string is tag.
    """
    if ":" in string and "@" not in string:
        return True
    return False

# def is_id(string: str):
#     """Judge whether or not string is image id.
#     """
#     if string.startswith(ID_PREFIX):
#         return True
#     return False

def add_default_tag(name: str) -> str:
    """Return <name>:DEFAULT_TAG"""
    if ":" in name:
        return name
    return name + ":" + DEFAULT_TAG

def add_idpref(image_or_layer_id: str) -> str:
    """Return sha256:<image or layer id>"""
    if image_or_layer_id.startswith(ID_PREFIX):
        return image_or_layer_id
    return ID_PREFIX + image_or_layer_id

def del_idpref(image_or_layer_id: str) -> str:
    """
    Args:
        image_or_layer_id (str): 'sha256:<image or layer id>'

    Return:
        <image or layer id> (str)
    """
    if not image_or_layer_id.startswith(ID_PREFIX):
        return image_or_layer_id
    return image_or_layer_id.split(ID_PREFIX)[1]

def marshal(domain: str, repo: str, sign: str, suffix: str) -> str:
    """
    Marshall components of reference, and return normalized reference
    """
    return domain + "/" + repo + sign + suffix
