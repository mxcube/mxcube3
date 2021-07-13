import logging
from flask import Blueprint, jsonify, make_response

from mxcube3 import logging_handler


def init_route(mxcube, server, url_prefix):
    bp = Blueprint("log", __name__, url_prefix=url_prefix)

    @bp.route("/", methods=["GET"])
    @server.restrict
    def log():
        """
        Retrive log messages
        """
        messages = []

        for handler in logging.getLogger("MX3.HWR").handlers:
            if isinstance(handler, logging_handler.MX3LoggingHandler):
                messages = handler.buffer
        
        return jsonify(messages)

    return bp