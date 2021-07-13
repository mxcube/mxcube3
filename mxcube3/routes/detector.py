from flask import Blueprint, jsonify

from mxcube3.core import beamlineutils

def init_route(mxcube, server, url_prefix):
    bp = Blueprint("detector", __name__, url_prefix=url_prefix)

    @bp.route("/", methods=["GET"])
    @server.restrict
    def get_detector_info():
        """
        Retrieves general info from the detector.
            :response Content-type: application/json, example:
                {'filetype': 'h5'},
            :statuscode: 200: no error
            :statuscode: 409: error
        """

        resp = jsonify({"fileSuffix": beamlineutils.get_detector_info()})
        resp.status_code = 200
        return resp

    return bp