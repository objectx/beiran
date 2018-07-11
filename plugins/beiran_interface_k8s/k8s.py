"""
Docker packaging plugin
"""

import asyncio
import docker

from beiran.plugin import BaseInterfacePlugin, History

from .models import DockerImage, DockerLayer
from .models import MODEL_LIST
from .util import DockerUtil
from .api import ROUTES
from .api import Services as ApiDependencies


PLUGIN_NAME = 'k8s'
PLUGIN_TYPE = 'interface'

class K8SInterface(BaseInterfacePlugin):
	pass
