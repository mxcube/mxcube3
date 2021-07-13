# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import io

from flask import Blueprint, Response, jsonify, request, send_file

from mxcube3.core import wfutils

def init_route(mxcube, server, url_prefix):
    bp = Blueprint("workflow", __name__, url_prefix=url_prefix)

    @bp.route("/", methods=["GET"])
    @server.restrict
    def workflow():
        return jsonify(wfutils.get_available_workflows())


    @bp.route("/", methods=["POST"])
    @server.restrict
    def sumbit_parameters():
        data = request.get_json()
        wfutils.submit_parameters(data)
        return Response(status=200)


    @bp.route("/mesh_result/<gid>/<t>", methods=["GET"])
    #@server.restrict
    def get_grid_data(gid, t, rand):
        res = send_file(
            io.BytesIO(wfutils.get_mesh_result(gid, t)),
            mimetype="image/png"
        )

        return res

    # This route is only for testing
    @bp.route("/dialog/<wf>", methods=["GET"])
    @server.restrict
    def workflow_dialog(wf):
        dialog = wfutils.test_workflow_dialog(wf)
        server.emit("workflowParametersDialog", dialog, namespace="/hwr")

        return Response(status=200)

    return bp