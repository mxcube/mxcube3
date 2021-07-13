# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

import PIL
import gevent.event

from io import StringIO
import base64

from mxcube3 import mxcube
from mxcube3.core.utils import to_camel, from_camel
from mxcube3.core import scutils
from mxcube3.core import beamlineutils
from mxcube3.core import utils

from queue_entry import CENTRING_METHOD
from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState


SAMPLE_IMAGE = None
CLICK_COUNT = 0
CLICK_LIMIT = 3
CENTRING_POINT_ID = None


def centring_clicks_left():
    global CLICK_COUNT, CLICK_LIMIT
    return CLICK_LIMIT - CLICK_COUNT


def centring_reset_click_count():
    global CLICK_COUNT
    CLICK_COUNT = 0


def centring_click():
    global CLICK_COUNT
    CLICK_COUNT += 1


def centring_remove_current_point():
    from mxcube3.routes import signals

    global CENTRING_POINT_ID

    if CENTRING_POINT_ID:
        mxcube.mxcubecore.beamline_ho.sample_view.delete_shape(CENTRING_POINT_ID)
        signals.send_shapes(update_positions=False)
        CENTRING_POINT_ID = None


def centring_add_current_point(*args):
    from mxcube3.routes import signals

    global CENTRING_POINT_ID
    shape = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(CENTRING_POINT_ID)

    # There is no current centered point shape when the centring is done
    # by software like Workflows, so we add one.
    if not shape:
        try:
            if args[0]:
                motors = args[1]["motors"]
                x, y = mxcube.mxcubecore.beamline_ho.diffractometer.motor_positions_to_screen(motors)
                centring_update_current_point(motors, x, y)
                shape = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(CENTRING_POINT_ID)
        except Exception:
            logging.getLogger("MX3.HWR").exception("Centring failed !")

    if shape:
        shape.state = "SAVED"
        signals.send_shapes(update_positions=False)
        CENTRING_POINT_ID = None


def centring_update_current_point(motor_positions, x, y):
    from mxcube3.routes import signals

    global CENTRING_POINT_ID
    point = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(CENTRING_POINT_ID)

    if point:
        point.move_to_mpos([motor_positions], [x, y])
    else:
        point = mxcube.mxcubecore.beamline_ho.sample_view.add_shape_from_mpos(
            [motor_positions], (x, y), "P"
        )
        point.state = "TMP"
        point.selected = True
        CENTRING_POINT_ID = point.id

    signals.send_shapes(update_positions=False)


def wait_for_centring_finishes(*args, **kwargs):
    """
    Executed when a centring is finished. It updates the temporary
    centred point.
    """

    try:
        centring_status = args[1]
    except IndexError:
        centring_status = {"valid": False}

    # we do not send/save any centring data if there is no sample
    # to avoid the 2d centring when no sample is mounted
    if scutils.get_current_sample().get("sampleID", "") == "":
        return

    # If centering is valid add the point, otherwise remove it
    if centring_status["valid"]:
        motor_positions = centring_status["motors"]
        motor_positions.pop("zoom", None)
        motor_positions.pop("beam_y", None)
        motor_positions.pop("beam_x", None)

        x, y = mxcube.mxcubecore.beamline_ho.diffractometer.motor_positions_to_screen(
            motor_positions
        )

        centring_update_current_point(motor_positions, x, y)
        mxcube.mxcubecore.beamline_ho.diffractometer.emit("stateChanged", (True,))

        if mxcube.AUTO_MOUNT_SAMPLE:
            mxcube.mxcubecore.beamline_ho.diffractometer.accept_centring()


def init_signals():
    """
    Connect all the relevant hwobj signals with the corresponding
    callback method.
    """
    from mxcube3.routes import signals

    dm = mxcube.mxcubecore.beamline_ho.diffractometer

    # for motor in utils.get_centring_motors():

    #     @utils.RateLimited(6)
    #     def pos_cb(pos, motor=motor, **kw):
    #         movable = utils.get_movable_state_and_position(motor)

    #         if movable:
    #             signals.motor_position_callback(movable[motor])
    #         else:
    #             logging.getLogger("MX3.HWR").exception(
    #                 "Could not call position callback for %s" % motor
    #             )

    #     def state_cb(state, motor=motor, **kw):
    #         movable = utils.get_movable_state_and_position(motor)

    #         if movable:
    #             # TODO check if there is a bug in get_state of expoerter motor ?
    #             movable[motor]["state"] = state.value

    #             signals.motor_state_callback(movable[motor], **kw)
    #         else:
    #             logging.getLogger("MX3.HWR").exception(
    #                 "Could not call state callback for %s" % motor
    #             )

        #setattr(dm, "_%s_pos_callback" % motor, pos_cb)
        #setattr(dm, "_%s_state_callback" % motor, state_cb)
        #dm.connect(dm.get_object_by_role(motor), "valueChanged", pos_cb)
        #dm.connect(dm.get_object_by_role(motor), "stateChanged", state_cb)

    #for actuator_name in ["FrontLight", "BackLight"]:

    #    @utils.RateLimited(3)
        #def light_pos_cb(pos, actuator_name=actuator_name, **kw):
        #    movable = utils.get_movable_state_and_position(motor)

        #    if movable:
        #        signals.motor_position_callback(movable[motor])
        #    else:
        #        logging.getLogger("MX3.HWR").exception(
        #            "Could not call position callback for %s" % motor
        #        )

        #def light_state_cb(state, actuator_name=actuator_name, **kw):
        #    movable = utils.get_movable_state_and_position(actuator_name)
        #    signals.motor_state_callback(movable[actuator_name], **kw)
        #    signals.motor_state_callback(movable[actuator_name + "Switch"], **kw)
        #    signals.motor_position_callback(movable[actuator_name + "Switch"])

        #setattr(dm, "_%s_light_state_callback" % actuator_name, light_state_cb)
        #setattr(dm, "_%s_light_pos_callback" % actuator_name, light_pos_cb)

        #try:
        #    motor = dm.get_object_by_role(actuator_name)
        #    motor.connect(motor, "valueChanged", light_pos_cb)
        #    motor_sw = dm.get_object_by_role(actuator_name + "Switch")
        #    motor_sw.connect(motor_sw, "stateChanged", light_state_cb)

        #except Exception as ex:
        #    logging.getLogger("MX3.HWR").exception(str(ex))

    dm.connect("centringStarted", signals.centring_started)
    dm.connect(dm, "centringSuccessful", wait_for_centring_finishes)
    dm.connect(dm, "centringFailed", wait_for_centring_finishes)
    dm.connect("centringAccepted", centring_add_current_point)
    mxcube.mxcubecore.beamline_ho.sample_view.connect("newGridResult", handle_grid_result)

    global CLICK_LIMIT
    CLICK_LIMIT = int(mxcube.mxcubecore.beamline_ho.click_centring_num_clicks or 3)


def new_sample_video_frame_received(img, width, height, *args, **kwargs):
    """
    Executed when a new image is received, update the centred positions
    and set the gevent so the new image can be sent.
    """
    global SAMPLE_IMAGE

    # Assume that we are gettign a qimage if we are not getting a str,
    # to be able to handle data sent by hardware objects used in MxCuBE 2.x
    # Passed as str in Python 2.7 and bytes in Python 3
    if isinstance(img, str):
        img = img
    elif isinstance(img, bytes):
        img = img
    else:
        rawdata = img.bits().asstring(img.numBytes())
        strbuf = StringIO()
        image = PIL.Image.frombytes("RGBA", (width, height), rawdata)
        (r, g, b, a) = image.split()
        image = PIL.Image.merge("RGB", (b, g, r))
        image.save(strbuf, "JPEG")
        img = strbuf.get_value()

    SAMPLE_IMAGE = img

    mxcube.mxcubecore.beamline_ho.sample_view.camera.new_frame.set()
    mxcube.mxcubecore.beamline_ho.sample_view.camera.new_frame.clear()


def stream_video(camera):
    """it just send a message to the client so it knows that there is a new
    image. A HO is supplying that image
    """
    global SAMPLE_IMAGE

    mxcube.mxcubecore.beamline_ho.sample_view.camera.new_frame = gevent.event.Event()

    try:
        mxcube.mxcubecore.beamline_ho.sample_view.camera.disconnect(
            "imageReceived", new_sample_video_frame_received
        )
    except KeyError:
        pass

    mxcube.mxcubecore.beamline_ho.sample_view.camera.connect(
        "imageReceived", new_sample_video_frame_received
    )

    while True:
        try:
            camera.new_frame.wait()
            yield (
                b"--frame\r\n"
                b"--!>\nContent-type: image/jpeg\n\n" + SAMPLE_IMAGE + b"\r\n"
            )
        except Exception:
            pass


def set_image_size(width, height):
    mxcube.mxcubecore.beamline_ho.sample_view.camera.restart_streaming((width, height))
    return beamlineutils.get_viewport_info()


def move_to_centred_position(point_id):
    point = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(point_id)

    if point:
        motor_positions = point.get_centred_position().as_dict()
        mxcube.mxcubecore.beamline_ho.diffractometer.move_motors(motor_positions)

    return point


def get_shapes():
    shape_dict = {}

    for shape in mxcube.mxcubecore.beamline_ho.sample_view.get_shapes():
        s = shape.as_dict()
        shape_dict.update({shape.id: s})

    return {"shapes": to_camel(shape_dict)}


def get_shape_width_sid(sid):
    shape = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(sid)

    if shape is not None:
        shape = shape.as_dict()
        return {"shape": to_camel(shape)}

    return shape


def shape_add_cell_result(sid, cell, result):
    from mxcube3.routes import signals

    shape = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(sid)
    shape.set_cell_result(cell, result)
    signals.grid_result_available(to_camel(shape.as_dict()))


def handle_grid_result(shape):
    from mxcube3.routes import signals

    signals.grid_result_available(to_camel(shape.as_dict()))


def update_shapes(shapes):
    updated_shapes = []

    for s in shapes:
        shape_data = from_camel(s)
        pos = []

        # Get the shape if already exists
        shape = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(shape_data.get("id", -1))

        # If shape does not exist add it
        if not shape:
            refs, t = shape_data.pop("refs", []), shape_data.pop("t", "")

            # Store pixels per mm for third party software, to facilitate
            # certain calculations

            beam_info_dict = beam_info_dict = beamlineutils.get_beam_info()

            shape_data[
                "pixels_per_mm"
            ] = mxcube.mxcubecore.beamline_ho.diffractometer.get_pixels_per_mm()
            shape_data["beam_pos"] = (
                beam_info_dict.get("position")[0],
                beam_info_dict.get("position")[1],
            )
            shape_data["beam_width"] = beam_info_dict.get("size_x", 0)
            shape_data["beam_height"] = beam_info_dict.get("size_y", 0)

            # Shape does not have any refs, create a new Centered position
            if not refs:
                try:
                    x, y = shape_data["screen_coord"]
                    mpos = mxcube.mxcubecore.beamline_ho.diffractometer.get_centred_point_from_coord(
                        x, y, return_by_names=True
                    )
                    pos.append(mpos)

                    # We also store the center of the grid
                    if t == "G":
                        # coords for the center of the grid
                        x_c = x + (shape_data["num_cols"] / 2.0) * shape_data["cell_width"]
                        y_c = y + (shape_data["num_rows"] / 2.0) * shape_data["cell_height"]
                        center_positions = mxcube.mxcubecore.beamline_ho.diffractometer.get_centred_point_from_coord(
                            x_c, y_c, return_by_names=True
                        )
                        pos.append(center_positions)

                    shape = mxcube.mxcubecore.beamline_ho.sample_view.add_shape_from_mpos(
                        pos, (x, y), t
                    )
                except Exception:
                    logging.getLogger("HWR.MX3").info(shape_data)

            else:
                shape = mxcube.mxcubecore.beamline_ho.sample_view.add_shape_from_refs(refs, t)

        # shape will be none if creation failed, so we check if shape exists
        # before setting additional parameters
        if shape:
            shape.update_from_dict(shape_data)
            shape_dict = to_camel(shape.as_dict())
            updated_shapes.append(shape_dict)

    return {"shapes": updated_shapes}


def rotate_to(sid):
    if sid:
        shape = mxcube.mxcubecore.beamline_ho.sample_view.get_shape(sid)
        cp = shape.get_centred_position()
        phi_value = round(float(cp.as_dict().get("phi", None)), 3)
        if phi_value:
            try:
                mxcube.mxcubecore.beamline_ho.diffractometer.centringPhi.set_value(phi_value)
            except Exception:
                raise


def move_zoom_motor(pos):
    zoom_motor = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role("zoom")
    if zoom_motor.get_state() != HardwareObjectState.READY:
        return (
            "motor is already moving",
            406,
            {"Content-Type": "application/json", "msg": "zoom already moving"},
        )

    if isinstance(zoom_motor, AbstractNState):
        zoom_motor.set_value(zoom_motor.value_to_enum(pos))
    else:
        zoom_motor.set_value(pos)

    scales = mxcube.mxcubecore.beamline_ho.diffractometer.get_pixels_per_mm()
    return {"pixelsPerMm": [scales[0], scales[1]]}


def back_light_on():
    motor = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role("BackLightSwitch")
    motor.set_value(motor.VALUES.IN)


def back_light_off():
    motor = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role("BackLightSwitch")
    motor.set_value(motor.VALUES.OUT)


def front_light_on():
    motor = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role("FrontLightSwitch")
    motor.set_value(motor.VALUES.IN)


def front_light_off():
    motor = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role("FrontLightSwitch")
    motor.set_value(motor.VALUES.OUT)


def move_motor(motid, newpos):
    motor = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role(motid.lower())

    if newpos == "stop":
        motor.stop()
        return True
    else:
        motor.set_value(float(newpos))

        return True


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
    if "Light" in elem_id:
        ret = utils.get_light_state_and_intensity()
    else:
        ret = utils.get_movable_state_and_position(elem_id)

    if ret:
        return ret
    else:
        raise Exception("Could not get status of movable")


def start_auto_centring():
    """
    Start automatic (lucid) centring procedure.
        :statuscode: 200: no error
        :statuscode: 409: error
    """
    if not mxcube.mxcubecore.beamline_ho.diffractometer.current_centring_procedure:
        msg = "Starting automatic centring"
        logging.getLogger("user_level_log").info(msg)

        mxcube.mxcubecore.beamline_ho.diffractometer.start_centring_method(
            mxcube.mxcubecore.beamline_ho.diffractometer.C3D_MODE
        )
    else:
        msg = "Could not starting automatic centring, already centring."
        logging.getLogger("user_level_log").info(msg)


def start_manual_centring():
    """
    Start 3 click centring procedure.
        :statuscode: 200: no error
        :statuscode: 409: error
    """
    if mxcube.mxcubecore.beamline_ho.diffractometer.is_ready():
        if mxcube.mxcubecore.beamline_ho.diffractometer.current_centring_procedure:
            logging.getLogger("user_level_log").info("Aborting current centring ...")
            mxcube.mxcubecore.beamline_ho.diffractometer.cancel_centring_method(reject=True)

        logging.getLogger("user_level_log").info("Centring using 3-click centring")

        mxcube.mxcubecore.beamline_ho.diffractometer.start_centring_method(
            mxcube.mxcubecore.beamline_ho.diffractometer.MANUAL3CLICK_MODE
        )

        centring_reset_click_count()
    else:
        logging.getLogger("user_level_log").warning("Diffracomter is busy, cannot start centering")
        raise RuntimeError("Diffracomter is busy, cannot start centering")

    return {"clicksLeft": centring_clicks_left()}


def abort_centring():
    try:
        logging.getLogger("user_level_log").info("User canceled centring")
        mxcube.mxcubecore.beamline_ho.diffractometer.cancel_centring_method()
        centring_remove_current_point()
    except:
        logging.getLogger("MX3.HWR").warning("Canceling centring failed")


def centring_handle_click(x, y):
    if mxcube.mxcubecore.beamline_ho.diffractometer.current_centring_procedure:
        mxcube.mxcubecore.beamline_ho.diffractometer.imageClicked(x, y, x, y)
        centring_click()
    else:
        if not centring_clicks_left():
            centring_reset_click_count()
            mxcube.mxcubecore.beamline_ho.diffractometer.cancel_centring_method()

            mxcube.mxcubecore.beamline_ho.diffractometer.start_centring_method(
                mxcube.mxcubecore.beamline_ho.diffractometer.MANUAL3CLICK_MODE
            )

    return {"clicksLeft": centring_clicks_left()}


def reject_centring():
    mxcube.mxcubecore.beamline_ho.diffractometer.reject_centring()
    centring_remove_current_point()


def move_to_beam(x, y):
    msg = "Moving point x: %s, y: %s to beam" % (x, y)
    logging.getLogger("user_level_log").info(msg)

    if getattr(mxcube.mxcubecore.beamline_ho.diffractometer, "move_to_beam") is None:
        # v > 2.2, or perhaps start_move_to_beam?
        mxcube.mxcubecore.beamline_ho.diffractometer.move_to_beam(x, y)
    else:
        # v <= 2.1
        mxcube.mxcubecore.beamline_ho.diffractometer.move_to_beam(x, y)


def set_centring_method(method):
    if method == CENTRING_METHOD.LOOP:
        msg = "Using automatic loop centring when mounting samples"
        mxcube.CENTRING_METHOD = CENTRING_METHOD.LOOP
    else:
        msg = "Using click centring when mounting samples"
        mxcube.CENTRING_METHOD = CENTRING_METHOD.MANUAL

    logging.getLogger("user_level_log").info(msg)
