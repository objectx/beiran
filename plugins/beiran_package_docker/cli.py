"""
Beiran Docker Plugin command line interface module
"""

import click
import json
import tabulate
import asyncio
from beiran.util import sizeof_fmt


@click.group()
@click.pass_context
def docker(ctx=None, debug=False):
    """Main subcommand method."""
    pass


# image subcommand group
@click.group()
@click.pass_obj
def image(self):
    """Group command for image management"""
    pass


docker.add_command(image)


@click.command('pull')
@click.option('--from', 'node', default=None,
              help='Pull from spesific node')
@click.option('--wait', 'wait', default=False, is_flag=True,
              help='Waits result of pulling image')
@click.option('--force', 'force', default=False, is_flag=True,
              help='Forces download of image even if the node is not recognised')
@click.option('--progress', 'progress', default=False, is_flag=True,
              help='Show image transfer progress')
@click.argument('imagename')
@click.pass_obj
# pylint: disable-msg=too-many-arguments
def image_pull(self, node, wait, force, progress, imagename):
    """Pull a container image from cluster or repository"""
    click.echo('Pulling image %s from %s!' % (imagename, node))

    if progress:
        progbar = click.progressbar(length=1)

        # We should use decent JSON stream parser.
        # This is a temporary solution.
        async def json_streamer(stream, subpath="*"):
            """Parse a stream of JSON chunks"""
            if subpath:
                pass
            while not stream.at_eof():
                data = await stream.readchunk()
                try:
                    json_str = data[0].decode("utf-8")[:-1]
                    json_dir = json.loads(json_str)
                    yield json_dir
                except json.decoder.JSONDecodeError:
                    pass

        async def pulling(progress):
            """Pull image with async client"""
            resp = await self.async_beiran_client.pull_image(imagename,
                                                             node=node,
                                                             wait=wait,
                                                             force=force,
                                                             progress=progress)
            before = 0
            async for update in json_streamer(resp.content, 'progress.*'):
                progbar.update(update['progress'] - before)
                before = update['progress']

        loop = asyncio.get_event_loop()
        loop.run_until_complete(pulling(progress))

        progbar.render_finish()
        click.echo('done!')

    else:
        result = self.beiran_client.pull_image(imagename,
                                               node=node,
                                               wait=wait,
                                               force=force,
                                               progress=progress)

        if "started" in result:
            click.echo("Process is started")
        if "finished" in result:
            click.echo("Process is finished")


# pylint: enable-msg=too-many-arguments

image.add_command(image_pull)


@click.command('list')
@click.option('--all', 'all_nodes', default=False, is_flag=True,
              help='List images from all known nodes')
@click.option('--node', default=None,
              help='List images from specific node')
@click.pass_obj
def image_list(self, all_nodes, node):
    """List container images across the cluster"""

    def _get_availability(i):
        if i['availability'] == 'available':
            num = str(len(i['available_at']))
            return i['availability'] + '(' + num + ' node(s))'
        return i['availability']

    images = self.beiran_client.get_images(all_nodes=all_nodes, node_uuid=node)
    table = [
        [",\n".join(i['tags']), sizeof_fmt(i['size']), _get_availability(i)]
        for i in images
    ]
    click.echo(tabulate(table, headers=["Tags", "Size", "Availability"]))


image.add_command(image_list)


# ##########  Layer management commands

@click.group()
@click.pass_obj
def layer(self):
    """group command for layer management"""
    pass


docker.add_command(layer)


@click.command('list')
@click.option('--all', 'all_nodes', default=False, is_flag=True,
              help='List layers from all known nodes')
@click.option('--node', default=None,
              help='List layers from specific node')
@click.pass_obj
def layer_list(self, all_nodes, node):
    """List container layers across the cluster"""
    layers = self.beiran_client.get_layers(all_nodes=all_nodes, node_uuid=node)
    table = [
        [i['digest'], sizeof_fmt(i['size']), str(len(i['available_at'])) + ' node(s)']
        for i in layers
    ]
    print(tabulate(table, headers=["Digest", "Size", "Availability"]))


layer.add_command(layer_list)
