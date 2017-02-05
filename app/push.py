# -*- coding: utf-8 -*-

import os
import click

from flask import Flask
from lib.push import linebots

@click.command()
@click.option("-p", "--port", default=8000)
@click.option("-h", "--host", default="0.0.0.0")
def run(port, host):
    app = Flask(__name__)
    app.register_blueprint(linebots.blueprint)

    port = int(os.environ.get("PORT", port))
    app.run(host=host, port=port)

if __name__ == "__main__":
    run()
