from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json

from flask import Blueprint, Response, jsonify, request, session

from mxcube3.core import qutils
from mxcube3.core import limsutils


def init_route(mxcube, server, url_prefix):
    bp = Blueprint("queue", __name__, url_prefix=url_prefix)

    @bp.route("/start", methods=["PUT"])
    @server.require_control
    @server.restrict
    def queue_start():
        """
        Start execution of the queue.

        :returns: Respons object, status code set to:
                200: On success
                409: Queue could not be started
        """
        sid = request.get_json().get("sid", None)
        qutils.queue_start(sid)

        return Response(status=200)


    @bp.route("/stop", methods=["PUT"])
    @server.require_control
    @server.restrict
    def queue_stop():
        """
        Stop execution of the queue.

        :returns: Response object status code set to:
                200: On success
                409: Queue could not be stopped
        """
        qutils.queue_stop()
        return Response(status=200)


    @bp.route("/abort", methods=["PUT"])
    @server.require_control
    @server.restrict
    def queue_abort():
        """
        Abort execution of the queue.

        :returns: Response object, status code set to:
                200 On success
                409 queue could not be aborted
        """
        mxcube.mxcubecore.beamline_ho.queue_manager.stop()
        return Response(status=200)


    @bp.route("/pause", methods=["PUT"])
    @server.require_control
    @server.restrict
    def queue_pause():
        """
        Pause the execution of the queue

        :returns: Response object, status code set to:
                200: On success
                409: Queue could not be paused
        """
        msg = qutils.queue_pause()
        server.emit("queue", msg, namespace="/hwr")
        return Response(status=200)


    @bp.route("/unpause", methods=["PUT"])
    @server.require_control
    @server.restrict
    def queue_unpause():
        """
        Unpause execution of the queue

        :returns: Response object, status code set to:
                200: On success
                409: Queue could not be unpause
        """
        msg = qutils.queue_unpause()
        server.emit("queue", msg, namespace="/hwr")
        return Response(status=200)


    @bp.route("/clear", methods=["PUT", "GET"])
    @server.require_control
    @server.restrict
    def queue_clear():
        """
        Clear the queue.

        :returns: Response object, status code set to:
                200: On success
                409: Queue could not be started
        """
        qutils.queue_clear()
        return Response(status=200)


    @bp.route("/", methods=["GET"])
    @server.restrict
    def queue_get():
        """
        Get the queue
        :returns: Response object response Content-Type: application/json, json
                object containing the queue on the format returned by
                queue_to_dict. The status code is set to:

                200: On success
                409: On error, could not retrieve queue
        """
        resp = jsonify(qutils.queue_to_dict(include_lims_data=True))
        resp.status_code = 200
        return resp


    @bp.route("/queue_state", methods=["GET"])
    @server.restrict
    def queue_get_state():
        """
        Get the queue.

        :returns: Response object response Content-Type: application/json, json
                object containing the queue state. The status code is set to:

                200: On success
                409: On error, could not retrieve queue
        """
        resp = jsonify(qutils.get_queue_state())
        resp.status_code = 200
        return resp


    @bp.route("/<sid>/<tindex>/execute", methods=["PUT"])
    @server.require_control
    @server.restrict
    def execute_entry_with_id(sid, tindex):
        """
        Execute the entry at position (sampleID, task index) in queue
        :param str sid: sampleID
        :param int tindex: task index of task within sample with id sampleID

        :statuscode: 200, no error
                    409, queue entry could not be executed
        """
        try:
            qutils.execute_entry_with_id(sid, tindex)
        except Exception:
            return Response(status=409)
        else:
            return Response(status=200)


    @bp.route("/", methods=["PUT"])
    @server.require_control
    @server.restrict
    def set_queue():
        qutils.set_queue(request.get_json(), session)
        return Response(status=200)


    @bp.route("/", methods=["POST"])
    @server.require_control
    @server.restrict
    def queue_add_item():
        tasks = request.get_json()

        queue = qutils.queue_add_item(tasks)
        sample_list = limsutils.sample_list_get(current_queue=queue)

        resp = jsonify(
            {
                "sampleOrder": queue.get("sample_order", []),
                "sampleList": sample_list.get("sampleList", {}),
            }
        )
        resp.status_code = 200

        return resp


    @bp.route("/<sqid>/<tqid>", methods=["POST"])
    @server.require_control
    @server.restrict
    def queue_update_item(sqid, tqid):
        data = request.get_json()

        model = qutils.queue_update_item(sqid, tqid, data)

        resp = jsonify(qutils.queue_to_dict([model]))
        resp.status_code = 200

        return resp


    @bp.route("/delete", methods=["POST"])
    @server.require_control
    @server.restrict
    def queue_delete_item():
        item_pos_list = request.get_json()

        qutils.delete_entry_at(item_pos_list)

        return Response(status=200)


    @bp.route("/set_enabled", methods=["POST"])
    @server.require_control
    @server.restrict
    def queue_enable_item():
        params = request.get_json()
        qid_list = params.get("qidList", None)
        enabled = params.get("enabled", False)
        qutils.queue_enable_item(qid_list, enabled)

        return Response(status=200)


    @bp.route("/<sid>/<ti1>/<ti2>/swap", methods=["POST"])
    @server.require_control
    @server.restrict
    def queue_swap_task_item(sid, ti1, ti2):
        qutils.swap_task_entry(sid, int(ti1), int(ti2))
        return Response(status=200)


    @bp.route("/<sid>/<ti1>/<ti2>/move", methods=["POST"])
    @server.require_control
    def queue_move_task_item(sid, ti1, ti2):
        qutils.move_task_entry(sid, int(ti1), int(ti2))
        return Response(status=200)


    @bp.route("/sample-order", methods=["POST"])
    @server.require_control
    @server.restrict
    def queue_set_sample_order():
        sample_order = request.get_json().get("sampleOrder", [])
        qutils.set_sample_order(sample_order)
        return Response(status=200)


    @bp.route("/<sample_id>", methods=["PUT"])
    @server.require_control
    @server.restrict
    def update_sample(sample_id):
        """
        Update a sample info
            :parameter node_id: entry identifier, integer. It can be a sample
                or a task within a sample
            :request Content-Type: application/json, object containing the
                parameter(s) to be updated, any parameter not sent will
                not be modified.
            :statuscode: 200: no error
            :statuscode: 409: sample info could not be updated, possibly because
                the given sample does not exist in the queue
        """
        params = json.loads(request.data)
        node_id = int(sample_id)

        try:
            qutils.update_sample(node_id, params)
            resp = jsonify({"QueueId": node_id})
            resp.status_code = 200
            return resp
        except Exception:
            return Response(status=409)


    @bp.route("/<node_id>/toggle", methods=["PUT"])
    @server.require_control
    @server.restrict
    def toggle_node(node_id):
        """
        Toggle a sample or a method checked status
            :parameter id: node identifier, integer
            :statuscode: 200: no error
            :statuscode: 409: node could not be toggled
        """
        qutils.toggle_node(int(node_id))
        return Response(status=200)


    @bp.route("/dc", methods=["GET"])
    @server.restrict
    def get_default_dc_params():
        """
        returns the default values for an acquisition (data collection).
        """
        resp = jsonify(qutils.get_default_dc_params())

        resp.status_code = 200
        return resp


    @bp.route("/char_acq", methods=["GET"])
    @server.restrict
    def get_default_char_acq_params():
        """
        returns the default values for a characterisation acquisition.
        TODO: implement as_dict in the qmo.AcquisitionParameters
        """
        resp = jsonify(qutils.get_default_char_acq_params())

        resp.status_code = 200
        return resp


    @bp.route("/char", methods=["GET"])
    @server.restrict
    def get_default_char_params():
        """
        returns the default values for a characterisation.
        """
        p = (
            mxcube.mxcubecore.beamline_ho.characterisation.get_default_characterisation_parameters().as_dict()
        )
        resp = jsonify(p)
        resp.status_code = 200
        return resp


    @bp.route("/mesh", methods=["GET"])
    @server.restrict
    def get_default_mesh_params():
        """
        returns the default values for a mesh.
        """
        resp = jsonify(qutils.get_default_mesh_params())
        resp.status_code = 200
        return resp


    @bp.route("/xrf", methods=["GET"])
    @server.restrict
    def get_default_xrf_parameters():
        """
        returns the default values for a xrf scan
        """
        resp = jsonify(qutils.get_default_xrf_parameters())
        resp.status_code = 200
        return resp


    @bp.route("/automount", methods=["POST"])
    @server.require_control
    @server.restrict
    def set_autmount():
        automount = request.get_json()
        qutils.set_auto_mount_sample(automount)
        resp = jsonify({"automount": automount})
        resp.status_code = 200

        return resp


    @bp.route("/num_snapshots", methods=["PUT"])
    @server.require_control
    @server.restrict
    def set_num_snapshots():
        data = request.get_json()
        mxcube.NUM_SNAPSHOTS = data.get("numSnapshots", 4)
        resp = jsonify({"numSnapshots": data.get("numSnapshots", 4)})
        resp.status_code = 200

        return resp


    @bp.route("/group_folder", methods=["POST"])
    @server.require_control
    @server.restrict
    def set_group_folder():
        path = request.get_json().get("path", "")

        resp = jsonify(qutils.set_group_folder(path))
        resp.status_code = 200

        return resp


    @bp.route("/group_folder", methods=["GET"])
    @server.restrict
    def get_group_folder():
        resp = jsonify({"path": mxcube.mxcubecore.beamline_ho.session.get_group_name()})
        resp.status_code = 200

        return resp


    @bp.route("/auto_add_diffplan", methods=["POST"])
    @server.require_control
    @server.restrict
    def set_autoadd():
        autoadd = request.get_json()
        qutils.set_auto_add_diffplan(autoadd)
        resp = jsonify({"auto_add_diffplan": autoadd})
        resp.status_code = 200
        return resp


    return bp