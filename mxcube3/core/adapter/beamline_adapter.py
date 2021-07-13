# -*- coding: utf-8 -*-
import logging
import math
import importlib
import pprint

from functools import reduce

from mxcubecore.ConvertUtils import make_table

from mxcube3.core.adapter.adapter_base import AdapterBase
from mxcube3.core.adapter.utils import get_adapter_cls_from_hardware_object

from mxcube3.core import utils

BEAMLINE_ADAPTER = None

# Singleton like interface is needed to keep the same referance to the
# adapter object and its corresponding hardware objects, so that the signal
# system wont cleanup signal handlers. (PyDispatcher removes signal handlers
# when a object is garbage collected)


def BeamlineAdapter(*args):
    global BEAMLINE_ADAPTER

    if BEAMLINE_ADAPTER is None:
        BEAMLINE_ADAPTER = _BeamlineAdapter(*args)

    return BEAMLINE_ADAPTER


class _BeamlineAdapter:
    """
    Adapter between Beamline route and Beamline hardware object.
    """

    def __init__(self, beamline_hwobj, app):
        self._application = app
        self._config = app.CONFIG.app.adapter_properties or []
        self._bl = beamline_hwobj
        self._ho_dict = {}
        self._configured_adapter_dict = {}
        self.adapter_dict = {}

        workflow = self._bl.workflow

        if workflow:
            workflow.connect("parametersNeeded", self.wf_parameters_needed)

    def wf_parameters_needed(self, params):
         self._application.server.emit(
            "workflowParametersDialog", params, broadcast=True, namespace="/hwr"
        )

    def get_object(self, name):
        return self.get_attr_from_path(name)

    def dict(self):
        """
        Build dictionary value-representation for each beamline attribute
         Returns:
           (dict): The dictionary.
        """
        attributes = {}

        for attr_name in self._application.mxcubecore.adapter_dict:
            _d = self._application.mxcubecore.get_adapter(attr_name).dict()
            attributes.update({attr_name: _d})

        return {"attributes": attributes}

    def get_available_methods(self):
        """
        Get the available methods.
        Returns:
            (list): The methods.
        """
        return self._bl.available_methods

    def get_available_elements(self):
        escan = self._bl.energy_scan
        elements = []

        if escan:
            elements = escan.get_elements()

        return {"elements": elements}

    def get_acquisition_limit_values(self):
        """
        Get the limits for the acquisition parameters.
        Returns:
            (dict): The limits.
        """
        _limits = self._bl.get_acquisition_limit_values()
        limits = {}

        for key, value in _limits.items():
            if isinstance(value, str) and "," in value:
                try:
                    limits[key] = list(map(float, _limits[key].split(",")))
                except BaseException:
                    msg = "[BEAMLINE_ADAPTER] Could not get limits for %s," % key
                    msg += " using -10000, 10000"
                    logging.getLogger("MX3.HWR").info(msg)
                    limits[key] = [-10000, 10000]
            else:
                limits[key] = value

        return limits