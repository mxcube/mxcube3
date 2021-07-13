from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json

from flask import Blueprint, Response, jsonify, request

from . import signals
from mxcube3.core import beamlineutils, utils

def init_route(mxcube, server, url_prefix):
    bp = Blueprint("diffractometer", __name__, url_prefix=url_prefix)

    @bp.route("/phase", methods=["GET"])
    @server.restrict
    def get_phase():
        """
        Retrieve the current phase in the diffractometer.
            :response Content-type: application/json, example:
                {'current_phase': 'Centring'},
                available phases: [Centring, BeamLocation, DataCollection,
                                Transfer]
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        data = {"current_phase": mxcube.mxcubecore.beamline_ho.diffractometer.get_current_phase()}
        resp = jsonify(data)
        resp.status_code = 200
        return resp


    @bp.route("/phaselist", methods=["GET"])
    @server.restrict
    def get_phase_list():
        """
        Retrieve the available phases in the diffractometer.
            :response Content-type: application/json,
                example: {'phase_list': [Centring, BeamLocation, DataCollection,
                                        Transfer]}
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        resp = jsonify(
            {"current_phase": mxcube.mxcubecore.beamline_ho.diffractometer.get_phase_list()}
        )
        resp.status_code = 200
        return resp


    @bp.route("/phase", methods=["PUT"])
    @server.require_control
    @server.restrict
    def set_phase():
        """
        Set the phase in the diffractometer.
            :request Content-type: application/json, an object containing
                the new phase as string, e.g. {'phase': 'Centring'}.
                [Centring, BeamLocation, DataCollection, Transfer]
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        params = request.data
        params = json.loads(params)
        phase = params["phase"]
        beamlineutils.diffractometer_set_phase(phase)
        return Response(status=200)


    @bp.route("/platemode", methods=["GET"])
    @server.restrict
    def md_in_plate_mode():
        """
        md_in_plate_mode: check if diffractometer is in plate mode or not
        data = {"md_in_plate_mode": } True /False
        return_data: data plus error code 200/409
        """
        md_in_plate_mode = mxcube.mxcubecore.beamline_ho.diffractometer.in_plate_mode()
        resp = jsonify({"md_in_plate_mode": md_in_plate_mode})
        resp.status_code = 200
        return resp


    @bp.route("/movables/state", methods=["GET"])
    @server.restrict
    def get_movables_state():
        ret = utils.get_centring_motors_info()
        ret.update(utils.get_light_state_and_intensity())
        resp = jsonify(ret)
        resp.status_code = 200
        return resp


    @bp.route("/aperture", methods=["PUT"])
    @server.require_control
    @server.restrict
    def set_aperture():
        """
        Move the aperture motor.
            :request Content-type: application/json, new position {'diameter': 50}.
                Note: level specified as integer (not 'Diameter 50')
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        params = request.data
        params = json.loads(params)
        new_pos = params["diameter"]
        beamlineutils.set_aperture(new_pos)

        return Response(status=200)


    @bp.route("/aperture", methods=["GET"])
    @server.restrict
    def get_aperture():
        ret = {}

        aperture_list, current_aperture = beamlineutils.get_aperture()

        ret.update({"apertureList": aperture_list, "currentAperture": current_aperture})

        resp = jsonify(ret)
        resp.status_code = 200
        return resp


    @bp.route("/info", methods=["GET"])
    @server.restrict
    def get_diffractometer_info():
        resp = jsonify(beamlineutils.diffractometer_get_info())
        resp.status_code = 200
        return resp

    return bp