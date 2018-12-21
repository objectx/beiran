"""
Beiran Docker Plugin command line interface module
"""

import asyncio
import click
from tabulate import tabulate

from beiran.util import json_streamer
from beiran.util import sizeof_fmt
from beiran.cli import pass_context


@click.group()
def cli():
    """Main subcommand method."""
    pass


@cli.group("image", short_help="docker image subcommand")
def image():
    """Group command for image management"""
    pass

@image.command('pull')
@click.option('--from', 'node', default=None,
              help='Pull from spesific node')
@click.option('--wait', 'wait', default=False, is_flag=True,
              help='Waits result of pulling image')
@click.option('--force', 'force', default=False, is_flag=True,
              help='Forces download of image even if the node is not recognised')
@click.option('--progress', 'progress', default=False, is_flag=True,
              help='Show image transfer progress')
@click.option('--whole-image-only', 'whole_image_only', default=False, is_flag=True,
              help='Pull an image from other node (not each layer)')
@click.argument('imagename')
@click.pass_obj
@pass_context
# pylint: disable-msg=too-many-arguments
def image_pull(ctx, node: str, wait: bool, force: bool, progress: bool,
               whole_image_only: bool, imagename: str):
    """Pull a container image from cluster or repository"""
    click.echo('Pulling image %s from %s!' % (imagename, node))

    if progress:
        progbar = click.progressbar(length=1)

        async def _pull_with_progress():
            """Pull image with async client"""
            resp = await ctx.async_beiran_client.pull_image(
                imagename,
                node=node,
                wait=wait,
                force=force,
                whole_image_only=whole_image_only,
                progress=True,
                raise_error=True
            )
            before = 0
            async for update in json_streamer(resp.content, '$.progress[::]'):
                progbar.update(update['progress'] - before)
                before = update['progress']

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_pull_with_progress())

        progbar.render_finish()  # type: ignore  # typing attribute missing error
        click.echo('done!')

    else:
        result = ctx.beiran_client.pull_image(
            imagename,
            node=node,
            wait=wait,
            force=force,
            whole_image_only=whole_image_only,
            progress=False,
            raise_error=True
        )

        if "started" in result:
            click.echo("Process is started")
        if "finished" in result:
            click.echo("Process is finished")

# pylint: enable-msg=too-many-arguments


@image.command('list')
@click.option('--all', 'all_nodes', default=False, is_flag=True,
              help='List images from all known nodes')
@click.option('--digests', default=False, is_flag=True,
              help='Show image digests')
@click.option('--node', default=None,
              help='List images from specific node')
@click.pass_obj
@pass_context
def image_list(ctx, all_nodes: bool, digests: bool, node: str):
    """List container images across the cluster"""

    def _get_availability(i):
        if i['availability'] == 'available':
            num = str(len(i['available_at']))
            return i['availability'] + '(' + num + ' node(s))'
        return i['availability']

    images = ctx.beiran_client.get_images(all_nodes=all_nodes, node_uuid=node)

    if digests:
        table = [
            [",\n".join(i['tags']), ",\n".join(i['repo_digests']), i['hash_id'],
             sizeof_fmt(i['size']), _get_availability(i)]
            for i in images
        ]
        headers = ["Tags", "Digests", "ID", "Size", "Availability"]
    else:
        table = [
            [",\n".join(i['tags']), i['hash_id'], sizeof_fmt(i['size']), _get_availability(i)]
            for i in images
        ]
        headers = ["Tags", "ID", "Size", "Availability"]

    click.echo(tabulate(table, headers=headers))


# ##########  Layer management commands

@cli.group("layer", short_help="docker layer subcommand")
def layer():
    """group command for layer management"""
    pass


@layer.command('list')
@click.option('--all', 'all_nodes', default=False, is_flag=True,
              help='List layers from all known nodes')
@click.option('--node', default=None,
              help='List layers from specific node')
@click.pass_obj
@pass_context
def layer_list(ctx, all_nodes: bool, node: str):
    """List container layers across the cluster"""
    layers = ctx.beiran_client.get_layers(all_nodes=all_nodes, node_uuid=node)
    table = [
        [i['digest'], sizeof_fmt(i['size']), str(len(i['available_at'])) + ' node(s)']
        for i in layers
    ]
    print(tabulate(table, headers=["Digest", "Size", "Availability"]))
