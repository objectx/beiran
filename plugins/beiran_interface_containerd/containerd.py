# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
containerd interface plugin
"""
import asyncio

from beiran.plugin import BaseInterfacePlugin
from beiran_interface_containerd.services.cri.image_service import ImageServiceClient

from beiran_package_container.util import ContainerUtil

PLUGIN_NAME = 'containerd'
PLUGIN_TYPE = 'interface'

# pylint: disable=attribute-defined-outside-init
class ContainerdInterface(BaseInterfacePlugin):
    """Containerd support for Beiran"""
    DEFAULTS = {
        'containerd_socket_path': "unix:///run/containerd/containerd.sock"
    }

    async def init(self):
        self.image_service_client = ImageServiceClient(self.config['containerd_socket_path'])

        # get storage path
        response = await self.image_service_client.image_fs_info()
        self.storage_path = response.image_filesystems[0].fs_id.mountpoint

    async def load_depend_plugin_instances(self, instances: list) -> None:
        """Load instances of plugins that has dependencies on this plugin"""
        self.container = instances['package:container'] # type: ignore

    async def start(self):
        self.log.debug("starting containerd plugin")

        # this is async but we will let it run in
        # background, we have no rush and it will run
        # forever anyway
        self.probe_task = self.loop.create_task(self.probe_daemon())
        self.on('containerd.new_image', self.new_image_saved)
        self.on('containerd.existing_image_deleted', self.existing_image_deleted)

    async def stop(self):
        if self.probe_task:
            self.probe_task.cancel()

    async def probe_daemon(self):
        """Deal with local containerd states"""
        try:
            self.log.debug("Probing containerd")

            await self.image_service_client.get_all_image_datas()

            # Delete all data regarding our node
            await ContainerUtil.reset_info_of_node(self.node.uuid.hex)

            # # wait until we can update our containerd info
            # await self.util.update_containerd_info(self.node)

            # connected to containerd
            self.emit('up')
            self.node.save()

            # try:
            #     # Get mapping of diff-id and digest mappings of containerd
            #     await self.util.get_diffid_mappings()
            #     # Get layerdb mapping
            #     await self.util.get_layerdb_mappings()
            # except PermissionError as err:
            #     self.log.error("Cannot access containerd storage, please run as sudo for now")
            #     raise err

            # # Get Images
            # self.log.debug("Getting containerd image list..")
            # image_list = await self.aiodocker.images.list(all=1)
            # not_intermediates = await self.aiodocker.images.list()

            # for image_data in image_list:
            #     self.log.debug("existing image..%s", image_data)

            #     if image_data in not_intermediates:
            #         await self.save_image(image_data['Id'], skip_updates=True)
            #     else:
            #         await self.save_image(image_data['Id'], skip_updates=True,
            #                               skip_updating_layer=True)

            # # This will be converted to something like
            # #   daemon.plugins['containerd'].setReady(true)
            # # in the future; will we in containerd plugin code.
            # self.history.update('init')
            # self.status = 'ready'

            # Do not block on this
            self.probe_task = self.loop.create_task(self.listen_daemon_events())

        except Exception as err:  # pylint: disable=broad-except
            await self.daemon_error(err)

    async def listen_daemon_events(self):
        """
        Subscribes aiodocker events channel and logs them.
        If containerd is unavailable calls deamon_lost method
        to emit the lost event.
        """
        # new_image_events = ['pull', 'load', 'tag', 'commit', 'import']
        # remove_image_events = ['delete']

        # try:
        #     # await until containerd is unavailable
        #     self.log.debug("subscribing to containerd events for further changes")
        #     subscriber = self.aiodocker.events.subscribe()
        #     while True:
        #         event = await subscriber.get()
        #         if event is None:
        #             break

        #         # log the event
        #         self.log.debug("containerd event: %s[%s] %s",
        #                        event['Action'], event['Type'], event.get('id', 'event has no id'))

        #         # handle commit container (and build new image)
        #         if event['Type'] == 'container' and event['Action'] in new_image_events:
        #             await self.save_image(event['Actor']['Attributes']['imageID'])

        #         # handle new image events
        #         if event['Type'] == 'image' and event['Action'] in new_image_events:
        #             await self.save_image(event['id'])

        #         # handle untagging image
        #         if event['Type'] == 'image' and event['Action'] == 'untag':
        #             await self.untag_image(event['id'])

        #         # handle delete existing image events
        #         if event['Type'] == 'image' and event['Action'] in remove_image_events:
        #             await self.delete_image(event['id'])

        #     await self.daemon_lost()
        # except Exception as err:  # pylint: disable=broad-except
        #     await self.daemon_error(str(err))
        pass

    async def daemon_error(self, error: str):
        """
        Daemon error emitter.
        Args:
            error (str): error message

        """
        # This will be converted to something like
        #   daemon.plugins['containerd'].setReady(false)
        # in the future; will we in containerd plugin code.
        self.log.error("containerd connection error: %s", error, exc_info=True)
        self.last_error = error
        self.status = 'error'

        # re-schedule
        self.log.debug("sleeping 10 seconds before retrying")
        await asyncio.sleep(10)
        self.probe_task = self.loop.create_task(self.probe_daemon())
        self.log.debug("re-scheduled probe_daemon")

    async def daemon_lost(self):
        """
        Daemon lost emitter.
        """
        # This will be converted to something like
        #   daemon.plugins['containerd'].setReady(false)
        # in the future; will we in containerd plugin code.
        self.emit('down')
        self.log.warning("containerd connection lost")

        # re-schedule
        await asyncio.sleep(30)
        self.probe_task = self.loop.create_task(self.probe_daemon())

    async def new_image_saved(self, image_id: str):
        """placeholder method for new_image_saved event"""
        self.log.debug("a new image reported by containerd deamon registered...: %s", image_id)

    async def existing_image_deleted(self, image_id: str):
        """placeholder method for existing_image_deleted event"""
        self.log.debug("an existing image and its layers in deleted...: %s", image_id)
