
import logging

from flask import Blueprint, jsonify


def init_route(mxcube, server, url_prefix):
    bp = Blueprint("main", __name__, url_prefix=url_prefix)
    
    @server.route("/samplegrid")
    @server.route("/datacollection")
    @server.route("/samplechanger")
    @server.route("/logging")
    @server.route("/remoteaccess")
    @server.restrict
    def serve_static_file():
        logging.getLogger("HWR").info("[Main] Serving main page")
        return server.flask.send_static_file("index.html")


    @server.route("/")
    @server.route("/login")
    def unrestricted_serve_static_file():
        logging.getLogger("HWR").info("[Main] Serving main page")
        return server.flask.send_static_file("index.html")

    @bp.route("/uiproperties")
    @server.restrict
    def get_ui_properties():
        return jsonify(mxcube.get_ui_properties())

    return bp