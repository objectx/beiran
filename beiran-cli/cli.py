#!/bin/env python
import click

@click.group()
def cli():
    pass

@click.group()
def image():
    pass
cli.add_command(image)

@click.command('pull')
@click.argument('imagename')
def image_pull(imagename):
    """Pull a container image from cluster or repository"""
    click.echo('Pulling image %s!' % imagename)
image.add_command(image_pull)

@click.command('list')
def image_list():
    """List container images across the cluster"""
    click.echo('Listing images!')
image.add_command(image_list)

if __name__ == '__main__':
    cli()

