# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import logging
import sys

from mxcube3 import mxcube

from .qutils import READY


from mxcube3.core.adapter.beamline_adapter import BeamlineAdapter


def init_signals():
    from mxcube3.routes import signals

    try:
        beamInfo = mxcube.mxcubecore.beamline_ho.beam
        if beamInfo is not None:
            for sig in signals.beam_signals:
                beamInfo.connect(beamInfo, sig, signals.beam_changed)
        else:
            logging.getLogger("MX3.HWR").error("beam_info is not defined")
    except Exception as ex:
        msg = "error connecting to beamline_adapter/beam_info hardware object "
        msg += "signals"
        logging.getLogger("MX3.HWR").exception(msg)
    try:

        actions =  mxcube.mxcubecore.HWR.get_hardware_object("beamcmds")
        if actions is not None:
            cmds = mxcube.mxcubecore.HWR.get_hardware_object("beamcmds").get_commands()
            for cmd in cmds:
                cmd.connect(
                    "commandBeginWaitReply", signals.beamline_action_start
                )
                cmd.connect("commandReplyArrived", signals.beamline_action_done)
                cmd.connect("commandReady", signals.beamline_action_done)
                cmd.connect("commandFailed", signals.beamline_action_failed)
        else:
            logging.getLogger("MX3.HWR").error(
                "beamline_actions hardware object is not defined"
            )
    except Exception as ex:
        msg = "error connecting to beamline actions hardware object signals"
        logging.getLogger("MX3.HWR").exception(msg)

    try:
        safety_shutter = mxcube.mxcubecore.beamline_ho.safety_shutter
        if safety_shutter is not None:
            safety_shutter.connect(
                safety_shutter,
                "shutterStateChanged",
                signals.safety_shutter_state_changed,
            )
        else:
            logging.getLogger("MX3.HWR").error("safety_shutter is not defined")
    except Exception as ex:
        logging.getLogger("MX3.HWR").error(
            "error loading safety_shutter hwo: %s" % str(ex)
        )

    try:
        mxcube.mxcubecore.plotting.connect(mxcube.mxcubecore.plotting, "new_plot", signals.new_plot)
        mxcube.mxcubecore.plotting.connect(mxcube.mxcubecore.plotting, "plot_data", signals.plot_data)
        mxcube.mxcubecore.plotting.connect(mxcube.mxcubecore.plotting, "plot_end", signals.plot_end)
    except Exception as ex:
        logging.getLogger("MX3.HWR").error("error loading plotting hwo: %s" % str(ex))

    try:
        mxcube.mxcubecore.beamline_ho.xrf_spectrum.connect(
            mxcube.mxcubecore.beamline_ho.xrf_spectrum, "new_plot", signals.new_plot
        )
        mxcube.mxcubecore.beamline_ho.xrf_spectrum.connect(
            mxcube.mxcubecore.beamline_ho.xrf_spectrum, "plot_data", signals.plot_data
        )
        mxcube.mxcubecore.beamline_ho.xrf_spectrum.connect(
            mxcube.mxcubecore.beamline_ho.xrf_spectrum, "plot_end", signals.plot_end
        )
        mxcube.mxcubecore.beamline_ho.xrf_spectrum.connect(
            mxcube.mxcubecore.beamline_ho.xrf_spectrum,
            "xrf_task_progress",
            signals.xrf_task_progress,
        )
    except Exception as ex:
        logging.getLogger("MX3.HWR").error("error loading plotting hwo: %s" % str(ex))


def diffractometer_init_signals():
    """
    Connect all the relevant hwobj signals with the corresponding
    callback method.
    """
    from mxcube3.routes import signals

    diffractometer = mxcube.mxcubecore.beamline_ho.diffractometer
    diffractometer.connect("phaseChanged", signals.diffractometer_phase_changed)


def get_aperture():
    """
    Returns list of apertures and the one currently used.

    :return: Tuple, (list of apertures, current aperture)
    :rtype: tuple
    """
    aperture_list, current_aperture = [], None
    beam = mxcube.mxcubecore.beamline_ho.beam
    
    aperture_list = beam.get_available_size()["values"]
    current_aperture = beam.get_value()[-1]

    return aperture_list, current_aperture


def get_beam_definer():
    beam_info = mxcube.mxcubecore.beamline_ho.beam

    if hasattr(beam_info, "beam_definer") and beam_info.beam_definer:
        bd = beam_info.beam_definer
    else:
        bd = beam_info.get_object_by_role("aperture")

    return bd


def get_viewport_info():
    """
    Get information about current "view port" video dimension, beam position,
    pixels per mm, returns a dictionary with the format:

        data = {"pixelsPerMm": pixelsPerMm,
                "imageWidth": width,
                "imageHeight": height,
                "format": fmt,
                "sourceIsScalable": source_is_scalable,
                "scale": scale,
                "videoSizes": video_sizes,
                "position": position,
                "shape": shape,
                "size_x": sx, "size_y": sy}

    :returns: Dictionary with view port data, with format described above
    :rtype: dict
    """
    fmt, source_is_scalable = "MJPEG", False

    if mxcube.CONFIG.app.VIDEO_FORMAT == "MPEG1":
        fmt, source_is_scalable = "MPEG1", True
        video_sizes = mxcube.mxcubecore.beamline_ho.sample_view.camera.get_available_stream_sizes()
        width, height, scale = mxcube.mxcubecore.beamline_ho.sample_view.camera.get_stream_size()
    else:
        scale = 1
        width = mxcube.mxcubecore.beamline_ho.sample_view.camera.get_width()
        height = mxcube.mxcubecore.beamline_ho.sample_view.camera.get_height()
        video_sizes = [(width, height)]

    pixelsPerMm = mxcube.mxcubecore.beamline_ho.diffractometer.get_pixels_per_mm()

    beam_info_dict = get_beam_info()

    data = {
        "pixelsPerMm": pixelsPerMm,
        "imageWidth": width,
        "imageHeight": height,
        "format": fmt,
        "sourceIsScalable": source_is_scalable,
        "scale": scale,
        "videoSizes": video_sizes,
        "videoHash": mxcube.mxcubecore.beamline_ho.sample_view.camera.stream_hash,
    }

    data.update(beam_info_dict)
    return data


def beamline_get_all_attributes():
    ho = BeamlineAdapter(mxcube.mxcubecore.beamline_ho)
    data = ho.dict()
    actions = list()

    try:
        cmds = mxcube.mxcubecore.HWR.get_hardware_object("beamcmds").get_commands()
    except Exception:
        cmds = []
    for cmd in cmds:
        args = []
        for arg in cmd.get_arguments():
            argname = arg[0]
            argtype = arg[1]
            args.append({"name": argname, "type": argtype})
            if argtype == "combo":
                args[-1]["items"] = cmd.get_combo_argument_items(argname)

        actions.append(
            {
                "name": cmd.name(),
                "username": cmd.name(),
                "state": READY,
                "arguments": args,
                "argument_type": cmd.argument_type,
                "messages": [],
                "type": cmd.type,
                "data": cmd.value(),
            }
        )

    data.update({"availableMethods": ho.get_available_methods()})

    data.update(
        {
            "path": mxcube.mxcubecore.beamline_ho.session.get_base_image_directory(),
            "actionsList": actions,
        }
    )

    data.update({"energyScanElements": ho.get_available_elements().get("elements", [])})

    return data


def beamline_abort_action(name):
    """
    Aborts an action in progress.

    :param str name: Owner / Actuator of the process/action to abort

    """
    try:
        cmds = mxcube.mxcubecore.HWR.get_hardware_object("beamcmds").get_commands()
    except Exception:
        cmds = []

    for cmd in cmds:
        if cmd.name() == name:
            cmd.abort()

    try:
        ho = BeamlineAdapter(mxcube.mxcubecore.beamline_ho).get_object(name.lower())
    except AttributeError:
        pass
    else:
        ho.stop()

def beamline_run_action(name, params):
    """
    Starts beamline action with name <name> and passes params as arguments

    : param str name: action to run
    """
    try:
        cmds = mxcube.mxcubecore.HWR.get_hardware_object("beamcmds").get_commands()
    except Exception:
        cmds = []

    for cmd in cmds:
        if cmd.name() == name:
            try:
                cmd.emit("commandBeginWaitReply", name)
                logging.getLogger("user_level_log").info(
                    "Starting %s(%s)", cmd.name(), ", ".join(map(str, params))
                )
                cmd(*params)
            except Exception:
                err = str(sys.exc_info()[1])
                raise Exception(str(err))

    else:
        msg = "Action cannot run: command '%s' does not exist" % name
        raise Exception(msg)

def get_beam_info():
    """
    Returns beam information retrieved by the beam_info hardware object,
    containing position, size and shape.

    :return: Beam info dictionary with keys: position, shape, size_x, size_y
    :rtype: dict
    """
    beam = mxcube.mxcubecore.beamline_ho.beam
    beam_info_dict = {"position": [], "shape": "", "size_x": 0, "size_y": 0}
    sx, sy, shape, label = beam.get_value()

    if beam is not None:
        beam_info_dict.update(
            {
                "position": beam.get_beam_position_on_screen(),
                "size_x": sx,
                "size_y": sy,
                "shape": shape.value,
            }
        )

    aperture_list, current_aperture = get_aperture()

    beam_info_dict.update(
        {"apertureList": aperture_list, "currentAperture": current_aperture}
    )

    return beam_info_dict


def prepare_beamline_for_sample():
    if hasattr(mxcube.mxcubecore.beamline_ho.collect, "prepare_for_new_sample"):
        mxcube.mxcubecore.beamline_ho.collect.prepare_for_new_sample()


def diffractometer_set_phase(phase):
    try:
        mxcube.mxcubecore.beamline_ho.diffractometer.wait_device_ready(30)
    except Exception:
        logging.getLogger("MX3.HWR").warning("Diffractometer not ready")

    mxcube.mxcubecore.beamline_ho.diffractometer.set_phase(phase)


def set_aperture(pos):
    beam = mxcube.mxcubecore.beamline_ho.beam
    msg = "Changing beam size to: %s" % pos
    logging.getLogger("MX3.HWR").info(msg)
    beam.set_value(pos)


def diffractometer_get_info():
    ret = {}

    try:
        ret["useSC"] = mxcube.mxcubecore.beamline_ho.diffractometer.use_sc
    except AttributeError:
        ret["useSC"] = False

    try:
        ret["currentPhase"] = mxcube.mxcubecore.beamline_ho.diffractometer.get_current_phase()
    except AttributeError:
        ret["currentPhase"] = "None"

    try:
        ret["phaseList"] = mxcube.mxcubecore.beamline_ho.diffractometer.get_phase_list()
    except AttributeError:
        ret["phaseList"] = []
        
    return ret


def get_detector_info():
    filetype = mxcube.mxcubecore.beamline_ho.detector.get_property("file_suffix")

    if filetype is None:
        filetype = "cbf"
        logging.getLogger("MX3.HWR").warning(
            "Detector file format not specified. Setting as cbf."
        )

    return filetype
