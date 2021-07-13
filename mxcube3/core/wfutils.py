# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from urllib.parse import quote
import base64

from mxcube3 import mxcube

def get_available_workflows():
    workflows = {}

    try:
        for wf in mxcube.mxcubecore.beamline_ho.workflow.get_available_workflows():
            # Rename name and path to wfname and wfpath in order to avoid name
            # clashes
            wf["wfname"] = wf.pop("name")
            wf["wfpath"] = wf.pop("path")

            workflows[wf["wfname"]] = wf
    except Exception:
        pass

    return {"workflows": workflows}


def submit_parameters(params):
    mxcube.mxcubecore.beamline_ho.workflow.set_values_map(params)


def get_mesh_result(gid, _type="heatmap"):
    base64data = mxcube.mxcubecore.beamline_ho.sample_view.get_grid_data(gid)
    base64data = base64data if base64data else ""

    data = base64.b64decode(base64data)
    return data
    
def test_workflow_dialog(wf):
    dialog = {
        "properties": {
            "name": {"title": "Task name", "type": "string", "minLength": 2},
            "description": {
                "title": "Description",
                "type": "string",
                "widget": "textarea",
            },
            "dueTo": {
                "title": "Due to",
                "type": "string",
                "widget": "compatible-datetime",
                "format": "date-time",
            },
        },
        "required": ["name"],
        "dialogName": "Trouble shooting !",
    }

    return dialog
