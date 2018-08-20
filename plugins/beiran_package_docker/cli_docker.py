"""
Beiran Docker Plugin command line interface module
"""

import asyncio
import click
from tabulate import tabulate

from beiran.util import json_streamer
from beiran.util import sizeof_fmt
from beiran.cli import pass_context


@click.group("docker", short_help="docker subcommands")
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
@click.argument('imagename')
@click.pass_obj
@pass_context
# pylint: disable-msg=too-many-arguments
def image_pull(ctx, node, wait, force, progress, imagename):
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
                progress=True,
                raise_error=True
            )
            before = 0
            async for update in json_streamer(resp.content, '$.progress[::]'):
                progbar.update(update['progress'] - before)
                before = update['progress']

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_pull_with_progress())

        progbar.render_finish()
        click.echo('done!')

    else:
        result = ctx.beiran_client.pull_image(
            imagename,
            node=node,
            wait=wait,
            force=force,
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
@click.option('--node', default=None,
              help='List images from specific node')
@click.pass_obj
@pass_context
def image_list(ctx, all_nodes, node):
    """List container images across the cluster"""

    def _get_availability(i):
        if i['availability'] == 'available':
            num = str(len(i['available_at']))
            return i['availability'] + '(' + num + ' node(s))'
        return i['availability']

    images = ctx.beiran_client.get_images(all_nodes=all_nodes, node_uuid=node)
    table = [
        [",\n".join(i['tags']), sizeof_fmt(i['size']), _get_availability(i)]
        for i in images
    ]
    click.echo(tabulate(table, headers=["Tags", "Size", "Availability"]))


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
def layer_list(ctx, all_nodes, node):
    """List container layers across the cluster"""
    layers = ctx.beiran_client.get_layers(all_nodes=all_nodes, node_uuid=node)
    table = [
        [i['digest'], sizeof_fmt(i['size']), str(len(i['available_at'])) + ' node(s)']
        for i in layers
    ]
    print(tabulate(table, headers=["Digest", "Size", "Availability"]))