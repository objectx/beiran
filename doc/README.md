# Beirand Docs

Please see Makefile and use it to generate documents. If you need to change
basic settings and how Sphinx generates docs, modify `conf.py` file.

## Usage

### Add new doc

Modify existing `.rst` files, or if it is needed create a new `.rst` and append 
it to `index.rst` to be shown in main page.

### Generate docs

Use `make html` to generate docs as html and `make help` for other options.

A directory called `build` and some sub directories appear after 
a successful doc generation.
