import logging

from flask import Blueprint, Response

from mxcube3.core import qutils
from mxcube3.routes import signals
from mxcube3.core.utils import to_camel


def init_route(mxcube, server, url_prefix):
    bp = Blueprint("mockup", __name__, url_prefix=url_prefix)

    @bp.route("/isready", methods=["GET"])
    @server.restrict
    def mockup_ready():
        logging.getLogger("HWR").info("[Routes] Called mockup ready")
        print((mxcube.mxcubecore.resolution.get_value()))
        return str(mxcube.resolution.isReady())


    @bp.route("/newres/<int:newres>", methods=["PUT"])
    @server.restrict
    def mockup_newres(newres):
        logging.getLogger("HWR").info("[Routes] Called mockup setting new resolution")
        return mxcube.mockups.setResolution(newres)


    @bp.route("/diff_plan/<sid>", methods=["GET"])
    @server.restrict
    def create_diff_plan(sid):
        """Juts for creating a diff plan as if it were created by edna and so on.
        """

        acq_parameters = mxcube.mxcubecore.beamline_ho.get_default_acquisition_parameters()
        ftype = mxcube.mxcubecore.beamline_ho.detector_hwobj.get_property("file_suffix")
        ftype = ftype if ftype else ".?"

        task = {
            "parameters": {
                "first_image": acq_parameters.first_image,
                "num_images": 111,
                "osc_start": acq_parameters.osc_start,
                "osc_range": 42,
                "kappa": acq_parameters.kappa,
                "kappa_phi": acq_parameters.kappa_phi,
                "overlap": acq_parameters.overlap,
                "exp_time": 456,
                "num_passes": acq_parameters.num_passes,
                "resolution": acq_parameters.resolution,
                "energy": acq_parameters.energy,
                "transmission": acq_parameters.transmission,
                "shutterless": acq_parameters.shutterless,
                "detector_mode": acq_parameters.detector_mode,
                "inverse_beam": False,
                "take_dark_current": True,
                "skip_existing_images": False,
                "take_snapshots": True,
                "helical": False,
                "mesh": False,
                "prefixTemplate": "{PREFIX}_{POSITION}",
                "subDirTemplate": "{ACRONYM}/{ACRONYM}-{NAME}",
                "prefix": "foo",
                "shape": "P1",  # -1
            },
            "checked": {True},
        }

        sample_model, sample_entry = qutils.get_entry(sid)
        dc_model, dc_entry = qutils._create_dc(task)
        qutils.set_dc_params(dc_model, dc_entry, task, sample_model)
        pt = dc_model.acquisitions[0].path_template

        if mxcube.mxcubecore.beamline_ho.queue_model.check_for_path_collisions(pt):
            msg = "[QUEUE] data collection could not be added to sample: "
            msg += "path collision"
            raise Exception(msg)

        dc_model.set_origin(3)
        dc_model.set_enabled(False)

        char, char_entry = qutils.get_entry(3)

        char.diffraction_plan.append([dc_model])
        mxcube.mxcubecore.beamline_ho.queue_model.emit("diff_plan_available", (char, [dc_model]))

        return Response(status=200)


    @bp.route("/shape_mock_result/<sid>", methods=["GET"])
    def shape_mock_result(sid):
        shape = mxcube.mxcubecore.beamline_ho.sample_view.camera.get_shape(sid)
        hm = {}
        cm = {}

        if shape:
            from random import random

            for i in range(1, shape.num_rows * shape.num_cols + 1):
                hm[i] = [
                    i,
                    [
                        int(random() * 255),
                        int(random() * 255),
                        int(random() * 255),
                        int(random()),
                    ],
                ]

            for i in range(1, shape.num_rows * shape.num_cols + 1):
                cm[i] = [
                    i,
                    [
                        int(random() * 255),
                        int(random() * 255),
                        int(random() * 255),
                        int(random()),
                    ],
                ]

        res = {"heatmap": hm, "crystalmap": cm}

        mxcube.mxcubecore.beamline_ho.sample_view.camera.set_grid_data(sid, res)
        signals.grid_result_available(to_camel(shape.as_dict()))

        return Response(status=200)

    return bp