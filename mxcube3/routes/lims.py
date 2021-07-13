# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from subprocess import check_output
from os.path import isfile, join
import logging

from flask import Blueprint, jsonify, Response, send_file, request, render_template

from mxcubecore.HardwareObjects import queue_model_objects as qmo

from mxcube3.core import limsutils
from mxcube3.core import qutils
from . import signals


def init_route(mxcube, server, url_prefix):
    bp = Blueprint("lims", __name__, url_prefix=url_prefix)

    @bp.route("/synch_samples", methods=["GET"])
    @server.restrict
    def proposal_samples():
        try:
            res = jsonify(limsutils.synch_with_lims())
        except Exception as ex:
            res = (
                "Could not synchronize with LIMS",
                409,
                {"Content-Type": "application/json", "message": str(ex)},
            )

        return res

    @bp.route("/dc/thumbnail/<image_id>", methods=["GET"])
    @server.restrict
    def get_dc_thumbnail(image_id):
        fname, data = limsutils.get_dc_thumbnail(image_id)
        return send_file(data, attachment_filename=fname, as_attachment=True)


    @bp.route("/dc/image/<image_id>", methods=["GET"])
    @server.restrict
    def get_dc_image(image_id):
        fname, data = limsutils.get_dc_image(image_id)
        return send_file(data, attachment_filename=fname, as_attachment=True)


    @bp.route("/quality_indicator_plot/<dc_id>", methods=["GET"])
    @server.restrict
    def get_quality_indicator_plot(dc_id):
        fname, data = limsutils.get_quality_indicator_plot(dc_id)
        return send_file(data, attachment_filename=fname, as_attachment=True)


    @bp.route("/dc/<dc_id>", methods=["GET"])
    @server.restrict
    def get_dc(dc_id):
        data = mxcube.mxcubecore.beamline_ho.lims_rest.get_dc(dc_id)
        return jsonify(data)


    @bp.route("/proposal", methods=["POST"])
    @server.restrict
    def set_proposal():
        """
        Set the selected proposal.
        """
        proposal_number = request.get_json().get("proposal_number", None)
        limsutils.select_proposal(proposal_number)

        return Response(status=200)


    @bp.route("/proposal", methods=["GET"])
    @server.restrict
    def get_proposal():
        """
        Return the currently selected proposal. (The proposal list is part of the login_res)
        """
        proposal_info = limsutils.get_proposal_info(
            mxcube.mxcubecore.beamline_ho.session.proposal_code
        )

        return jsonify({"Proposal": proposal_info})


    def run_get_result_script(script_name, url):
        return check_output(["node", script_name, url], close_fds=True)


    def result_file_test(prefix):
        return isfile(join(server.template_folder, prefix))


    def apply_template(name, data):
        try:
            r = jsonify({"result": render_template(name, data=data)})
        except Exception:
            r = jsonify({"result": "No results yet, processing ..."})

        return r


    @bp.route("/results", methods=["POST"])
    @server.restrict
    def get_results():
        """
        """
        qid = request.get_json().get("qid", None)
        r = jsonify({"result": ""})

        if qid:
            model, entry = qutils.get_entry(qid)
            data = qutils.queue_to_dict([model], True)
            signals.update_task_result(entry)

            if isinstance(model, qmo.DataCollection):
                if result_file_test("data-collection-results.js"):
                    pass
                elif result_file_test("data-collection-results.html"):
                    r = apply_template("data-collection-results.html", data)

            elif isinstance(model, qmo.Characterisation) or isinstance(model, qmo.Workflow):
                if result_file_test("characterisation-results.js"):
                    try:
                        url_list = data["limsResultData"]["workflow_result_url_list"]
                    except Exception as ex:
                        logging.getLogger("MX3.HWR").warning(
                            "Error retrieving wf url list, {0}".format(ex.message)
                        )
                        url_list = None

                    if url_list:
                        r = jsonify(
                            {
                                "result": run_get_result_script(
                                    join(
                                        server.template_folder,
                                        "characterisation-results.js",
                                    ),
                                    url_list[0],
                                )
                            }
                        )
                    else:
                        r = apply_template("data-collection-results.html", data)

                elif result_file_test("characterisation-results.html"):
                    r = apply_template("characterisation-results.html", data)

            elif isinstance(model, qmo.Workflow):
                pass
            elif isinstance(model, qmo.XRFSpectrum):
                pass
            elif isinstance(model, qmo.EnergyScan):
                pass
            else:
                pass

        return r
    
    return bp