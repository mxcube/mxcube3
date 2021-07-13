from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from . import signals

from flask import Blueprint, Response, jsonify, request
from mxcube3.core import limsutils
from mxcube3.core import scutils

from mxcube3.core.qutils import UNCOLLECTED, SAMPLE_MOUNTED, COLLECTED
from mxcube3.core.scutils import set_current_sample

def init_route(mxcube, server, url_prefix):
    bp = Blueprint("sample_changer", __name__, url_prefix=url_prefix)

    @bp.route("/samples_list", methods=["GET"])
    @server.restrict
    def get_sample_list():
        scutils.get_sample_list()
        return jsonify(limsutils.sample_list_get())


    @bp.route("/state", methods=["GET"])
    @server.restrict
    def get_sc_state():
        state = mxcube.mxcubecore.beamline_ho.sample_changer.get_status().upper()
        return jsonify({"state": state})


    @bp.route("/loaded_sample", methods=["GET"])
    @server.restrict
    def get_loaded_sample():
        address, barcode = scutils.get_loaded_sample()
        return jsonify({"address": address, "barcode": barcode})


    @bp.route("/contents", methods=["GET"])
    @server.restrict
    def get_sc_contents_view():
        return jsonify(scutils.get_sc_contents())


    @bp.route("/select/<loc>", methods=["GET"])
    @server.require_control
    @server.require_control
    @server.restrict
    def select_location(loc):
        mxcube.mxcubecore.beamline_ho.sample_changer.select(loc)
        return scutils.get_sc_contents()


    @bp.route("/scan/<loc>", methods=["GET"])
    @server.require_control
    @server.restrict
    def scan_location(loc):
        # do a recursive scan
        mxcube.mxcubecore.beamline_ho.sample_changer.scan(loc, True)
        return scutils.get_sc_contents()


    @bp.route("/unmount_current", methods=["POST"])
    @server.require_control
    @server.restrict
    def unmount_current():
        try:
            res = scutils.unmount_current()
        except Exception as ex:
            res = (
                "Cannot unload sample",
                409,
                {"Content-Type": "application/json", "message": str(ex)},
            )
        return jsonify(res)


    @bp.route("/mount", methods=["POST"])
    @server.require_control
    @server.restrict
    def mount_sample():
        resp = Response(status=200)

        try:
            resp = jsonify(scutils.mount_sample(request.get_json()))
        except Exception as ex:
            resp = (
                "Cannot load sample",
                409,
                {"Content-Type": "application/json", "message": str(ex)},
            )

        return resp


    @bp.route("/unmount", methods=["POST"])
    @server.require_control
    @server.restrict
    def unmount_sample():
        try:
            resp = jsonify(scutils.unmount_sample(request.get_json()["sample"]))
        except Exception as ex:
            return (
                "Cannot unload sample",
                409,
                {"Content-Type": "application/json", "message": str(ex)},
            )
        return resp


    @bp.route("/capacity", methods=["GET"])
    @server.restrict
    def get_sc_capacity():
        try:
            ret = scutils.get_capacity()
        except Exception:
            return Response(status=409)
        else:
            return jsonify(capacity=ret)


    @bp.route("/get_maintenance_cmds", methods=["GET"])
    @server.restrict
    def get_maintenance_cmds():
        try:
            ret = scutils.get_maintenance_cmds()
        except Exception:
            return Response(status=409)
        else:
            return jsonify(cmds=ret)


    @bp.route("/get_global_state", methods=["GET"])
    @server.restrict
    def get_global_state():
        try:
            ret = scutils.get_global_state()

            if ret:
                state, cmdstate, msg = ret
            else:
                return jsonify(ret)

        except Exception:
            return Response(status=409)
        else:
            return jsonify(state=state, commands_state=cmdstate, message=msg)


    @bp.route("/get_initial_state", methods=["GET"])
    @server.restrict
    def get_initial_state():
        return jsonify(scutils.get_initial_state())


    @bp.route(
        "/send_command/<cmdparts>/<args>", methods=["GET"]
    )
    @server.require_control
    @server.restrict
    def send_command(cmdparts, args=None):
        try:
            ret = mxcube.mxcubecore.beamline_ho.sample_changer_maintenance.send_command(cmdparts, args)
        except Exception as ex:
            msg = str(ex)
            msg = msg.replace("\n", " - ")
            return (
                "Cannot execute command",
                406,
                {"Content-Type": "application/json", "message": msg},
            )
        else:
            return jsonify(response=ret)


    return bp