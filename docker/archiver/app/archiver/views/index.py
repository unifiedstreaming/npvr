from flask import make_response, render_template
from archiver import archiver_api


@archiver_api.route("/")
def index():
    """
    Show basic index page
    """
    return make_response(render_template("index.html"))
