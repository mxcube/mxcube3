from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from flask import Blueprint, Response, jsonify, request

import os
import json

from mxcube3.core import beamlineutils
from mxcube3.core import sviewutils


def init_route(mxcube, server, url_prefix):
    bp = Blueprint("sampleview", __name__, url_prefix=url_prefix)

    @bp.route("/camera/subscribe", methods=["GET"])
    @server.restrict
    def subscribe_to_camera():
        """
        Subscribe to the camera streaming
            :response: image as html Content-type
        """
        if mxcube.CONFIG.app.VIDEO_FORMAT == "MPEG1":
            result = Response(status=200)
        else:
            frame = sviewutils.stream_video(mxcube.mxcubecore.beamline_ho.sample_view.camera)
            result = Response(frame, mimetype='multipart/x-mixed-replace; boundary="!>"')

        return result


    @bp.route("/camera/unsubscribe", methods=["PUT"])
    @server.restrict
    def unsubscribe_to_camera():
        """
        SampleCentring: unsubscribe from the camera streaming
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        mxcube.mxcubecore.beamline_ho.sample_view.camera.streaming_greenlet.kill()
        return Response(status=200)


    @bp.route("/camera/save", methods=["PUT"])
    @server.restrict
    def snapshot():
        """
        Save snapshot of the sample view
        data = {generic_data, "Path": path} # not sure if path should be available,
        or directly use the user/proposal path
        Return: 'True' if command issued succesfully, otherwise 'False'.
        """
        try:
            mxcube.mxcubecore.beamline_ho.sample_view.camera.takeSnapshot(
                os.path.join(os.path.dirname(__file__), "snapshots/")
            )
            return "True"
        except Exception:
            return "False"


    @bp.route("/camera", methods=["GET"])
    @server.restrict
    def get_image_data():
        """
        Get size of the image of the diffractometer
            :response Content-type:application/json, example:
            {  "imageHeight": 576, "imageWidth": 768,
            "pixelsPerMm": [1661.1295681063123, 1661.1295681063123]
            }
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        data = beamlineutils.get_viewport_info()

        resp = jsonify(data)
        resp.status_code = 200
        return resp


    @bp.route("/camera", methods=["POST"])
    @server.restrict
    def set_image_size():
        """
        """
        params = request.get_json()

        res = sviewutils.set_image_size(int(params["width"]), int(params["height"]))

        resp = jsonify(res)
        resp.status_code = 200
        return resp


    @bp.route("/centring/<point_id>/moveto", methods=["PUT"])
    @server.require_control
    @server.restrict
    def move_to_centred_position(point_id):
        """
        Move to the given centred position.
            :parameter id: centred position identifier, integer
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        point = sviewutils.move_to_centred_position(point_id)

        if point:
            return Response(status=200)
        else:
            return Response(status=409)


    @bp.route("/shapes", methods=["GET"])
    @server.restrict
    def get_shapes():
        """
        Retrieve all the stored centred positions.
            :response Content-type: application/json, the stored centred positions.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        shapes = sviewutils.get_shapes()

        resp = jsonify(shapes)
        resp.status_code = 200
        return resp


    @bp.route("/shapes/<sid>", methods=["GET"])
    @server.restrict
    def get_shape_with_sid(sid):
        """
        Retrieve requested shape information.
            :response Content-type: application/json, the stored centred positions.
            :statuscode: 200: no error
            :statuscode: 409: shape not found
        """
        shape = sviewutils.get_shapes()

        if shape is not None:
            resp = jsonify(shape)
            resp.status_code = 200
            return resp
        else:
            return Response(status=409)


    @bp.route("/shapes/<sid>", methods=["POST"])
    def shape_add_cell_result(sid):
        """
        Update cell result data.
            :parameter shape_data: dict with result info (cell number, result value)
            :response Content-type: application/json, response status.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        params = request.get_json()

        cell_number = params.get("cell", 0)
        result = params.get("result", 0)

        sviewutils.shape_add_cell_result(sid, cell_number, result)
        return Response(status=200)


    @bp.route("/shapes", methods=["POST"])
    @server.require_control
    @server.restrict
    def update_shapes():
        """
        Update shape information.
            :parameter shape_data: dict with shape information (id, type, ...)
            :response Content-type: application/json, the stored centred positions.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        resp = Response(status=409)
        shapes = request.get_json().get("shapes", [])

        resp = jsonify(sviewutils.update_shapes(shapes))
        resp.status_code = 200

        return resp


    @bp.route("/shapes/<sid>", methods=["DELETE"])
    @server.require_control
    @server.restrict
    def delete_shape(sid):
        """
        Retrieve all the stored centred positions.
            :response Content-type: application/json, the stored centred positions.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        mxcube.mxcubecore.beamline_ho.sample_view.delete_shape(sid)
        return Response(status=200)


    @bp.route("/shapes/rotate_to", methods=["POST"])
    @server.require_control
    @server.restrict
    def rotate_to():
        """
        Rotate Phi to the position where the given shape was defined

            :parameter sid: The shape id
            :response Content-type: application/json, the stored centred positions.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        sid = request.get_json().get("sid", -1)

        try:
            sviewutils.rotate_to(sid)
        except Exception:
            resp = Response(status=409)
        else:
            resp = Response(status=200)

        return resp


    @bp.route("/zoom", methods=["PUT"])
    @server.require_control
    @server.restrict
    def move_zoom_motor():
        """
        Move the zoom motor.
            :request Content-type: application/json, new position {'level': 4}.
            Note: level specified as integer (not 'Zoom 4')
            :response Content-type: application/json, new scale value,
            example: {"pixelsPerMm": [ 1661.1, 1661.1]}
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        params = request.data
        pos = json.loads(params).get("level", 0)

        res = sviewutils.move_zoom_motor(pos)

        resp = jsonify(res)
        resp.status_code = 200
        return resp


    @bp.route("/backlighton", methods=["PUT"])
    @server.require_control
    @server.restrict
    def back_light_on():
        """
        Activate the backlight of the diffractometer.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        sviewutils.back_light_on()
        return Response(status=200)


    @bp.route("/backlightoff", methods=["PUT"])
    @server.require_control
    @server.restrict
    def back_light_off():
        """
        Switch off the backlight of the diffractometer.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        sviewutils.back_light_off()
        return Response(status=200)


    @bp.route("/frontlighton", methods=["PUT"])
    @server.require_control
    @server.restrict
    def front_light_on():
        """
        Activate the frontlight of the diffractometer.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        sviewutils.front_light_on()
        return Response(status=200)


    @bp.route("/frontlightoff", methods=["PUT"])
    @server.require_control
    @server.restrict
    def front_light_off():
        """
        Switch off the frontlight of the diffractometer.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        sviewutils.front_light_off()
        return Response(status=200)


    @bp.route("/<motid>/<newpos>", methods=["PUT"])
    @server.require_control
    @server.restrict
    def move_motor(motid, newpos):
        """
            Move or Stop the given motor.
            :parameter motid: motor name, 'Phi', 'Focus', 'PhiZ', 'PhiY', 'Zoom',
            'BackLightSwitch','BackLight','FrontLightSwitch', 'FrontLight',
            'Sampx', 'Sampy'
            :parameter newpos: new position, double, stop: string
            :statuscode: 200: no error
            :statuscode: 409: error
        """

        try:
            sviewutils.move_motor(motid, newpos)
        except Exception as ex:
            return (
                "Could not move motor %s" % str(ex),
                409,
                {"Content-Type": "application/json", "msg": str(ex)},
            )
        else:
            return Response(status=200)


    @bp.route("/<elem_id>", methods=["GET"])
    @server.restrict
    def get_status_of_id(elem_id):
        """
        Get position and status of the given element
            :parameter id: moveable to get its status, 'Phi', 'Focus', 'PhiZ',
            'PhiY', 'Zoom', 'BackLightSwitch','BackLight','FrontLightSwitch',
            'FrontLight','Sampx', 'Sampy'
            :response Content-type: application/json, {motorname:
                {'Status': status, 'position': position} }
            :statuscode: 200: no error
            :statuscode: 409: error
        """

        try:
            ret = sviewutils.get_status_of_id(elem_id)
            resp = jsonify(ret)
            resp.status_code = 200
            return resp
        except Exception:
            return Response(status=409)


    @bp.route("/centring/startauto", methods=["GET"])
    @server.require_control
    @server.restrict
    def centre_auto():
        """
        Start automatic (lucid) centring procedure.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        sviewutils.start_auto_centring()
        return Response(status=200)


    @bp.route("/centring/start3click", methods=["PUT"])
    @server.require_control
    @server.restrict
    def centre_3_click():
        """
        Start 3 click centring procedure.
            :statuscode: 200: no error
            :statuscode: 409: error
        """

        try:
            data = sviewutils.start_manual_centring()
        except Exception as ex:
            resp = (
                "Could not move motor %s" % str(ex),
                409,
                {"Content-Type": "application/json", "msg": str(ex)},
            )
        else:
            resp = jsonify(data)
            resp.status_code = 200

        return resp


    @bp.route("/centring/abort", methods=["PUT"])
    @server.require_control
    @server.restrict
    def abort_centring():
        """
        Abort centring procedure.
            :statuscode: 200: no error
            :statuscode: 409: error
        """
        sviewutils.abort_centring()
        return Response(status=200)


    @bp.route("/centring/click", methods=["PUT"])
    @server.require_control
    @server.restrict
    def click():
        """
        The 3-click method needs the input from the user, a running 3click centring
        procedure must be set before

        :request Content-type: application/json, integer positions of the clicks,
                            {clickPos={"x": 123,"y": 456}}
        :response Content-type: application/json, integer, number of clicks
                                left {'clickLeft': 3 | 2 | 1}
        :statuscode: 200: no error
        :statuscode: 409: error
        """
        pos = json.loads(request.data).get("clickPos", None)

        data = sviewutils.centring_handle_click(pos["x"], pos["y"])

        resp = jsonify(data)
        resp.status_code = 200
        return resp


    @bp.route("/centring/accept", methods=["PUT"])
    @server.require_control
    @server.restrict
    def accept_centring():
        """
        Accept the centring position.
        """
        mxcube.mxcubecore.beamline_ho.diffractometer.accept_centring()
        return Response(status=200)


    @bp.route("/centring/reject", methods=["PUT"])
    @server.require_control
    @server.restrict
    def reject_centring():
        """Reject the centring position."""
        sviewutils.reject_centring()
        return Response(status=200)


    @bp.route("/movetobeam", methods=["PUT"])
    @server.require_control
    @server.restrict
    def move_to_beam():
        """Go to the beam position from the given (x, y) position."""
        pos = json.loads(request.data).get("clickPos")

        sviewutils.move_to_beam(pos["x"], pos["y"])

        return Response(status=200)


    @bp.route("/centring/centring_method", methods=["PUT"])
    @server.require_control
    @server.restrict
    def set_centring_method():
        """
        Set MXCuBE to use automatic (lucid) centring procedure when
        mounting samples

        :statuscode: 200: no error
        :statuscode: 409: error

        """
        method = json.loads(request.data).get("centringMethod", None)
        sviewutils.set_centring_method(method)
        return Response(status=200)


    return bp