from flask import Blueprint, Flask
from flask_cors import CORS
from os import environ
from celery import Celery
from flasgger import Swagger
import json
from archiver.utils import state_backend


app = Flask(__name__, static_folder=None)
# load default config
app.config.from_object("archiver.config.default")
# optionally load environment config
if "APP_CONFIG" in environ:
    app.config.from_envvar("APP_CONFIG")
CORS(app)

# swagger stuffs
swagger = Swagger(app)


# pretty print json filter for jinja
def pretty_json(value):
    return json.dumps(value, indent=2)


app.jinja_env.filters["pretty_json"] = pretty_json


def make_celery(app):
    celery = Celery(app.import_name)
    # celery.conf.update(app.config)
    celery.config_from_object("archiver.config.default")
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)

state = state_backend.StateBackend(app=celery)

# use blueprints to get multiple possible endpoints e.g. if behind a reverse
# proxy

archiver_api = Blueprint(
    "archiver_api",
    __name__,
    template_folder="templates",
    static_folder="static",
)

import archiver.views  # noqa: E402,F401
import archiver.tasks  # noqa: E402,F401


app.register_blueprint(archiver_api, url_prefix="/")


# handle reverse proxy which might rewrite the URL
class ReverseProxied(object):
    """Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In haproxy:

    option forwardfor
    http-request add-header X-Forwarded-Proto https if { ssl_fc }
    http-request add-header X-Path-Prefix "/archiver"

    :param app: the WSGI application
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path_prefix = environ.get("HTTP_X_PATH_PREFIX", "")
        if path_prefix:
            environ["SCRIPT_NAME"] = path_prefix
            path_info = environ["PATH_INFO"]
            if path_info.startswith(path_prefix):
                environ["PATH_INFO"] = path_info[len(path_prefix) :]

        scheme = environ.get("HTTP_X_FORWARDED_PROTO", "")
        if scheme:
            environ["wsgi.url_scheme"] = scheme
        return self.app(environ, start_response)


app.wsgi_app = ReverseProxied(app.wsgi_app)
