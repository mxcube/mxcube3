# -*- coding: utf-8 -*-
import os
import logging
import sys

from mxcube3 import blcontrol
from mxcube3.video import streaming
from mxcube3 import mxcube

from qutils import READY
import utils

from mxcube3.core.beamline_setup import BeamlineSetupMediator


def init_signals():
    from mxcube3.routes import signals

    try:
        beamInfo = blcontrol.beamline.getObjectByRole("beam_info")
        if beamInfo is not None:
            for sig in signals.beam_signals:
                beamInfo.connect(beamInfo, sig, signals.beam_changed)
        else:
            logging.getLogger('MX3.HWR').error("beam_info is not defined")
    except Exception as ex:
        msg = "error connecting to beamline_setup/beam_info hardware object "
        msg += "signals"
        logging.getLogger('MX3.HWR').exception(msg)
    try:
        actions = blcontrol.actions
        if actions is not None:
            cmds = actions.getCommands()
            for cmd in cmds:
                cmd.connectSignal("commandBeginWaitReply",
                                  signals.beamline_action_start)
                cmd.connectSignal("commandReplyArrived",
                                  signals.beamline_action_done)
                cmd.connectSignal("commandFailed",
                                  signals.beamline_action_failed)
        else:
            logging.getLogger('MX3.HWR').error(
                "beamline_actions hardware object is not defined")
    except Exception as ex:
        msg = "error connecting to beamline actions hardware object signals"
        logging.getLogger('MX3.HWR').exception(msg)

    try:
        safety_shutter = blcontrol.beamline.getObjectByRole("safety_shutter")
        if safety_shutter is not None:
            safety_shutter.connect(safety_shutter, 'shutterStateChanged',
                                   signals.safety_shutter_state_changed)
        else:
            logging.getLogger('MX3.HWR').error("safety_shutter is not defined")
    except Exception as ex:
        logging.getLogger('MX3.HWR').error(
            "error loading safety_shutter hwo: %s" % str(ex))

    try:
        blcontrol.plotting.connect(
            blcontrol.plotting, 'new_plot', signals.new_plot)
        blcontrol.plotting.connect(
            blcontrol.plotting, 'plot_data', signals.plot_data)
        blcontrol.plotting.connect(
            blcontrol.plotting, 'plot_end', signals.plot_end)
    except Exception as ex:
        logging.getLogger('MX3.HWR').error(
            "error loading plotting hwo: %s" % str(ex))

    try:
        blcontrol.beamline.xrf_spectrum_hwobj.connect(
            blcontrol.beamline.xrf_spectrum_hwobj, 'new_plot', signals.new_plot)
        blcontrol.beamline.xrf_spectrum_hwobj.connect(
            blcontrol.beamline.xrf_spectrum_hwobj, 'plot_data',
            signals.plot_data)
        blcontrol.beamline.xrf_spectrum_hwobj.connect(
            blcontrol.beamline.xrf_spectrum_hwobj, 'plot_end', signals.plot_end)
        blcontrol.beamline.xrf_spectrum_hwobj.connect(
            blcontrol.beamline.xrf_spectrum_hwobj, 'xrf_task_progress',
            signals.xrf_task_progress)
    except Exception as ex:
        logging.getLogger('MX3.HWR').error(
            "error loading plotting hwo: %s" % str(ex))


def diffractometer_init_signals():
    """
    Connect all the relevant hwobj signals with the corresponding
    callback method.
    """
    from mxcube3.routes import signals

    diffractometer = blcontrol.diffractometer
    diffractometer.connect(
        "phaseChanged", signals.diffractometer_phase_changed)


def get_aperture():
    """
    Returns list of apertures and the one currently used.

    :return: Tuple, (list of apertures, current aperture)
    :rtype: tuple
    """
    aperture_list, current_aperture = [], None
    aperture = get_beam_definer()

    if aperture is not None:
        aperture_list = aperture.getPredefinedPositionsList()
        current_aperture = aperture.getCurrentPositionName()

    return aperture_list, current_aperture


def get_beam_definer():
    beam_info = blcontrol.beamline.getObjectByRole("beam_info")

    if hasattr(beam_info, "beam_definer_hwobj") and \
       beam_info.beam_definer_hwobj:
        bd = beam_info.beam_definer_hwobj
    else:
        bd = beam_info.aperture_hwobj

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

    if mxcube.VIDEO_DEVICE and os.path.exists(mxcube.VIDEO_DEVICE):
        fmt, source_is_scalable = "MPEG1", True

    video_sizes = streaming.get_available_sizes(
        blcontrol.diffractometer.camera)
    width, height, scale = streaming.video_size()
    pixelsPerMm = blcontrol.diffractometer.get_pixels_per_mm()

    beam_info_dict = get_beam_info()

    data = {"pixelsPerMm": pixelsPerMm,
            "imageWidth": width,
            "imageHeight": height,
            "format": fmt,
            "sourceIsScalable": source_is_scalable,
            "scale": scale,
            "videoSizes": video_sizes}

    data.update(beam_info_dict)
    return data


def beamline_get_all_attributes():
    ho = BeamlineSetupMediator(blcontrol.beamline)
    data = ho.dict_repr()
    actions = list()

    try:
        cmds = blcontrol.actions.getCommands()
    except Exception:
        cmds = []
    for cmd in cmds:
        args = []
        for arg in cmd.getArguments():
            argname = arg[0]
            argtype = arg[1]
            args.append({"name": argname, "type": argtype})
            if argtype == 'combo':
                args[-1]["items"] = cmd.getComboArgumentItems(argname)

        actions.append({"name": cmd.name(), "username": cmd.userName(),
                        "state": READY, "arguments": args, "messages": [],
                        "type": cmd.type, "data": cmd.value()})

    data["movables"].update(get_all_motors())

    data.update({'availableMethods': ho.get_available_methods()})
    data.update({'path': blcontrol.session.get_base_image_directory(),
                 'actionsList': actions})
    data.update({'energyScanElements':
                 ho.get_available_elements().get("elements", [])})

    return data


def beamline_abort_action(name):
    """
    Aborts an action in progress.

    :param str name: Owner / Actuator of the process/action to abort

    """
    try:
        cmds = blcontrol.actions.getCommands()
    except Exception:
        cmds = []

    for cmd in cmds:
        if cmd.name() == name:
            cmd.abort()


def beamline_run_action(name, params):
    """
    Starts beamline action with name <name> and passes params as arguments

    : param str name: action to run
    """
    try:
        cmds = blcontrol.actions.getCommands()
    except Exception:
        cmds = []

    for cmd in cmds:
        if cmd.name() == name:
            try:
                cmd.emit('commandBeginWaitReply', name)
                logging.getLogger('user_level_log').info(
                    'Starting %s(%s)', cmd.userName(),
                    ", ".join(map(str, params)))
                cmd(*params)
            except Exception:
                err = str(sys.exc_info()[1])
                raise Exception(str(err))

    else:
        msg = "Action cannot run: command '%s' does not exist" % name
        raise Exception(msg)


def beamline_set_attribute(name, value):
    ho = BeamlineSetupMediator(blcontrol.beamline).getObjectByRole(name)

    try:
        ho.set(value)
        data = ho.dict_repr()
    except Exception as ex:
        msg = "Error setting bl attribute: " + str(ex)
        logging.getLogger('MX3.HWR').error(msg)
        raise ex

    return data


def beamline_get_attribute(name):
    """
    """
    ho = BeamlineSetupMediator(
        blcontrol.beamline).getObjectByRole(name.lower())
    data = {"name": name, "value": ""}

    try:
        data = ho.dict_repr()
        res = 200
    except Exception as ex:
        raise ex

    return data


def get_beam_info():
    """
    Returns beam information retrieved by the beam_info hardware object,
    containing position, size and shape.

    :return: Beam info dictionary with keys: position, shape, size_x, size_y
    :rtype: dict
    """
    beam_info = blcontrol.beamline.getObjectByRole("beam_info")
    beam_info_dict = {"position": [], "shape": "", "size_x": 0, "size_y": 0}

    if beam_info is not None:
        beam_info_dict.update(beam_info.get_beam_info())
        # Get the scale of the video stream, so that we can calculate
        # the correct beam posiition
        width, height, scale = streaming.video_size()
        position = beam_info.get_beam_position()
        beam_info_dict["position"] = position

    aperture_list, current_aperture = get_aperture()

    beam_info_dict.update({'apertureList': aperture_list,
                           'currentAperture': current_aperture})

    return beam_info_dict


def prepare_beamline_for_sample():
    if hasattr(blcontrol.collect, 'prepare_for_new_sample'):
        blcontrol.collect.prepare_for_new_sample()


def diffractometer_set_phase(phase):
    try:
        blcontrol.diffractometer.wait_device_ready(30)
    except Exception:
        logging.getLogger('MX3.HWR').warning('Diffractometer not ready')

    blcontrol.diffractometer.set_phase(phase)


def set_aperture(pos):
    beam_definer = get_beam_definer()
    msg = "Changing aperture diameter to: %s" % pos
    logging.getLogger('MX3.HWR').info(msg)
    beam_definer.moveToPosition(pos)


def diffractometer_get_info():
    ret = {}

    try:
        ret['useSC'] = blcontrol.diffractometer.use_sc
    except AttributeError:
        ret['useSC'] = False

    try:
        ret['currentPhase'] = blcontrol.diffractometer.current_phase
    except AttributeError:
        ret['currentPhase'] = 'None'

    try:
        ret['phaseList'] = blcontrol.diffractometer.get_phase_list()
    except AttributeError:
        ret['phaseList'] = []

    return ret


def get_detector_info():
    filetype = blcontrol.beamline.detector_hwobj.getProperty('file_suffix')

    if filetype is None:
        filetype = 'cbf'
        logging.getLogger('MX3.HWR').warning(
            'Detector file format not specified. Setting as cbf.')

    return filetype


def move_motor(name, pos):
    motor_hwobj = blcontrol.diffractometer.getObjectByRole(name)

    if motor_hwobj.getState() != 2:
        raise Exception(name + ' already moving')

    limits = motor_hwobj.getLimits()
    if not limits[0] <= float(pos) <= limits[1]:
        raise Exception(name + ' position out of range, ' + str(limits))

    motor_hwobj.move(float(pos))

    return get_motor(name)


def stop_motor(name):
    motor_hwobj = blcontrol.diffractometer.getObjectByRole(name.lower())

    try:
        motor_hwobj.stop()
    except Exception as ex:
        msg = "Could not stop motor '%s'" % name
        logging.getLogger('MX3.HWR').exception(msg)
        raise ex


def get_motor(name):
    if 'Light' in name:
        ret = utils.get_light_state_and_intensity()[name]
    else:
        ret = utils.get_movable_state_and_position(name)[name]

    if ret:
        return ret
    else:
        raise Exception("Could not get status of movable")


def get_all_motors():
    ret = utils.get_centring_motors_info()
    ret.update(utils.get_light_state_and_intensity())
    return ret


def set_movable(name, pos):
    if name.lower() in blcontrol.diffractometer.getRoles():
        res = move_motor(name, pos)
    else:
        res = beamline_set_attribute(name, pos)

    return res


def stop_movable(name):
    if name.lower() in blcontrol.diffractometer.getRoles():
        res = stop_motor(name)
    else:
        ho = BeamlineSetupMediator(blcontrol.beamline).\
            getObjectByRole(name.lower())

        res = ho.stop()

    return res


def get_movable(name):
    if name.lower() in blcontrol.diffractometer.getRoles():
        res = get_motor(name)
    else:
        res = beamline_get_attribute(name)

    return res


def get_all_movables():
    ret = beamline_get_all_attributes()["movables"]
    ret.update(utils.get_centring_motors_info())
    ret.update(utils.get_light_state_and_intensity())
    return ret
