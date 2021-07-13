# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
import logging
import time
import gevent
import gevent.event
import types
import inspect
import base64
import os
import sys
import email.utils
import smtplib
from email.mime.text import MIMEText
from email.utils import make_msgid

from mxcube3 import mxcube


from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState

SNAPSHOT_RECEIVED = gevent.event.Event()
SNAPSHOT = None

def RateLimited(maxPerSecond):
    minInterval = 1.0 / float(maxPerSecond)

    def decorate(func):
        lastTimeCalled = [0.0]

        def rateLimitedFunction(*args, **kargs):
            elapsed = time.time() - lastTimeCalled[0]
            leftToWait = minInterval - elapsed
            if leftToWait > 0:
                # ignore update
                return
            ret = func(*args, **kargs)
            lastTimeCalled[0] = time.time()
            return ret

        return rateLimitedFunction

    return decorate


def _proposal_id(session):
    try:
        return int(session["loginInfo"]["loginRes"]["Proposal"]["number"])
    except (KeyError, TypeError, ValueError):
        return None


def get_light_state_and_intensity():
    """
    Return the light actuator state (in/out) and the light motor level. It takes
    into accojunt the two find of light hwobj available
        * MicrodiffLight + MicrodiffInOut
        * Combined hwobj such as ID30Light
    """
    ret = dict()

    for light in ("BackLight", "FrontLight"):
        hwobj = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role(light)
        hwobj_switch = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role(
            light + "Switch"
        )
        switch_state = 1 if hwobj_switch.get_value().name == "IN" else 0

        ret.update(
            {
                light: {
                    "name": light,
                    "state": hwobj.get_state().value,
                    "position": hwobj.get_value(),
                    "limits": hwobj.get_limits(),
                },
                light
                + "Switch": {
                    "name": light + "Switch",
                    "state": HardwareObjectState.READY.value,
                    "position": switch_state,
                },
            }
        )
    return ret


def get_light_limits():
    ret = dict()

    for light in ("BackLight", "FrontLight"):
        item_role = light.lower()

        hwobj = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role(item_role)

        ret.update({light: {"limits": hwobj.get_limits()}})

    return ret


def get_movable_state_and_position(item_name):
    try:
        if "light" in item_name.lower():
            # handle all *light* items in the same way;
            # this returns more than needed, but it doesn't
            # matter
            return get_light_state_and_intensity()
        hwobj = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role(item_name)

        if hwobj is None:
            msg = (
                "[UTILS.GET_MOVABLE_STATE_AND_POSITION] No movable with role '%s'"
                % item_name
            )
            logging.getLogger("MX3.HWR").error(msg)
            return {item_name: {"name": item_name, "state": None, "position": None}}
        else:
            if hasattr(hwobj, "get_current_position_name"):
                # a motor similar to zoom
                pos_name = hwobj.get_current_position_name()
                if pos_name:
                    pos = hwobj.predefined_positions[pos_name]
                else:
                    pos = None
            elif isinstance(hwobj, AbstractNState):
                pos = hwobj.get_value().value
            else:
                pos = hwobj.get_value()

            return {
                item_name: {
                    "name": item_name,
                    "state": hwobj.get_state().value,
                    "position": pos,
                }
            }
    except Exception:
        logging.getLogger("MX3.HWR").exception(
            "[UTILS.GET_MOVABLE_STATE_AND_POSITION] could not get item '%s'" % item_name
        )


def get_movable_limits(item_name):
    item_role = item_name.lower()

    try:
        if "light" in item_role:
            # handle all *light* items in the same way;
            # this returns more than needed, but it doesn't
            # matter
            return get_light_limits()

        hwobj = mxcube.mxcubecore.beamline_ho.diffractometer.get_object_by_role(item_role)

        if hwobj is None:
            logging.getLogger("MX3.HWR").error(
                "[UTILS.GET_MOVABLE_LIMIT] No movable with role '%s'" % item_role
            )
            limits = (0, 0)
        else:
            limits = hwobj.get_limits()

        return {item_name: {"limits": limits}}
    except Exception:
        logging.getLogger("MX3.HWR").exception(
            "[UTILS.GET_MOVABLE_LIMIT] could not get item '%s'" % item_name
        )


_centring_motors_memo = None


def get_centring_motors():
    global _centring_motors_memo

    if not _centring_motors_memo:
        _centring_motors_memo = list(
            mxcube.mxcubecore.beamline_ho.diffractometer.get_positions().keys()
        )

        # Adding the two pseudo motors for sample alignment in the microscope
        # view
        _centring_motors_memo += [
            "sample_vertical",
            "sample_horizontal",
            "beamstop_distance",
        ]

    return _centring_motors_memo


def get_centring_motors_info():
    # the centring motors are: ["phi", "focus", "phiz", "phiy",
    # "zoom", "sampx", "sampy", "kappa", "kappa_phi"]

    ret = dict()
    for name in get_centring_motors():
        try:
            motor_info = get_movable_state_and_position(name)

            if motor_info and motor_info[name]["position"] is not None:
                ret.update(motor_info)

            motor_limits = get_movable_limits(name)

            if motor_limits and motor_limits[name]["limits"] is not None:
                ret[name].update(motor_limits[name])
        except KeyError:
            pass
            # logging.getLogger("MX3.HWR").exception(
            #     "[UTILS.GET_CENTRING_MOTORS_INFO]: Could not get %s" %name
            # )

    return ret


def _snapshot_received(data):
    snapshot_jpg = data.get("data", "")

    global SNAPSHOT
    SNAPSHOT = base64.b64decode(snapshot_jpg)
    SNAPSHOT_RECEIVED.set()


def _do_take_snapshot(filename, bw=False):
    mxcube.mxcubecore.beamline_ho.sample_view.save_snapshot(
        filename, overlay=False, bw=bw
    )

    # from . import loginutils
    # from mxcube3 import server, server

    # SNAPSHOT_RECEIVED.clear()
    # rid = loginutils.get_operator()["socketio_sid"]

    # with server.test_request_context():
    #     server.emit(
    #         "take_xtal_snapshot", namespace="/hwr", room=rid, callback=_snapshot_received
    #     )

    # SNAPSHOT_RECEIVED.wait(timeout=30)

    # with open(filename, "wb") as snapshot_file:
    #     snapshot_file.write(SNAPSHOT)


def save_snapshot(self, filename, bw=False):
    mxcube.mxcubecore.beamline_ho.sample_view.save_snapshot(
        filename, overlay=Flase, bw=bw
    )
    #_do_take_snapshot(filename, bw)


def take_snapshots(self, snapshots=None, _do_take_snapshot=_do_take_snapshot):
    if snapshots is None:
        # called via AbstractCollect
        dc_params = self.current_dc_parameters
        diffractometer = self.diffractometer
        move_omega_relative = diffractometer.move_omega_relative
    else:
        # called via AbstractMultiCollect
        # calling_frame = inspect.currentframe()
        calling_frame = inspect.currentframe().f_back.f_back

        dc_params = calling_frame.f_locals["data_collect_parameters"]
        diffractometer = self.diffractometer()
        move_omega_relative = diffractometer.phiMotor.set_value_relative

    if dc_params["take_snapshots"]:
        number_of_snapshots = mxcube.NUM_SNAPSHOTS
    else:
        number_of_snapshots = 0

    if number_of_snapshots > 0:
        if (
            hasattr(diffractometer, "set_phase")
            and diffractometer.get_current_phase() != "Centring"
        ):
            logging.getLogger("user_level_log").info(
                "Moving Diffractometer to CentringPhase"
            )
            diffractometer.set_phase("Centring", wait=True, timeout=200)

        snapshot_directory = dc_params["fileinfo"]["archive_directory"]
        if not os.path.exists(snapshot_directory):
            try:
                self.create_directories(snapshot_directory)
            except Exception:
                logging.getLogger("MX3.HWR").exception(
                    "Collection: Error creating snapshot directory"
                )

        logging.getLogger("user_level_log").info(
            "Taking %d sample snapshot(s)" % number_of_snapshots
        )

        for snapshot_index in range(number_of_snapshots):
            snapshot_filename = os.path.join(
                snapshot_directory,
                "%s_%s_%s.snapshot.jpeg"
                % (
                    dc_params["fileinfo"]["prefix"],
                    dc_params["fileinfo"]["run_number"],
                    (snapshot_index + 1),
                ),
            )
            dc_params[
                "xtalSnapshotFullPath%i" % (snapshot_index + 1)
            ] = snapshot_filename

            try:
                logging.getLogger("MX3.HWR").info(
                    "Taking snapshot number: %d" % (snapshot_index + 1)
                )
                _do_take_snapshot(snapshot_filename)
                #diffractometer.save_snapshot(snapshot_filename)
            except Exception:
                sys.excepthook(*sys.exc_info())
                raise RuntimeError("Could not take snapshot '%s'", snapshot_filename)

            if number_of_snapshots > 1:
                move_omega_relative(90)
                diffractometer.wait_ready()

def enable_snapshots(collect_object, diffractometer_object, sample_view):
    collect_object.take_crystal_snapshots = types.MethodType(
        take_snapshots, collect_object
    )

    diffractometer_object.save_snapshot = types.MethodType(
        save_snapshot, diffractometer_object
    )

    sample_view.set_ui_snapshot_cb(save_snapshot)

def send_mail(_from, to, subject, content):
    smtp = smtplib.SMTP("smtp", smtplib.SMTP_PORT)
    date = email.Utils.formatdate(localtime=True)

    msg = MIMEText(content)
    msg["Subject"] = subject
    msg["From"] = _from
    msg["To"] = to
    msg["Date"] = date
    msg["Message-ID"] = make_msgid()

    email_msg = msg.as_string()

    try:
        error_dict = smtp.sendmail(_from, to.split(","), email_msg)

        if error_dict:
            msg = "Could not send mail to %s, content %s, error was: %s"
            msg = msg % (to, content, str(error_dict))
            logging.getLogger().error(msg)
        else:
            msg = "Feedback sent to %s, msg: \n %s" % (to, content)
            logging.getLogger("MX3.HWR").info(msg)

    except smtplib.SMTPException as e:
        msg = "Could not send mail to %s, content %s, error was: %s"
        logging.getLogger().error(msg % (to, content, str(e)))
    finally:
        smtp.quit()


def send_feedback(sender_data):
    bl_name = mxcube.mxcubecore.beamline_ho.session.beamline_name
    local_user = sender_data.get("LOGGED_IN_USER", "")

    if not bl_name:
        try:
            bl_name = os.environ["BEAMLINENAME"].lower()
        except (KeyError):
            bl_name = "unknown-beamline"

    if not local_user:
        try:
            local_user = os.environ["USER"].lower()
        except (KeyError):
            local_user = "unknown_user"

    _from = mxcube.mxcubecore.beamline_ho.session.get_property("from_email", "")

    if not _from:
        _from = "%s@%s" % (
            local_user,
            mxcube.mxcubecore.beamline_ho.session.get_property("email_extension", ""),
        )

    # Sender information provided by user
    _sender = sender_data.get("sender", "")
    to = mxcube.mxcubecore.beamline_ho.session.get_property("feedback_email", "") + ",%s" % _sender
    subject = "[MX3 FEEDBACK] %s (%s) on %s" % (local_user, _sender, bl_name)
    content = sender_data.get("content", "")

    send_mail(_from, to, subject, content)


def str_to_camel(name):
    if isinstance(name, str):
        components = name.split("_")
        # We capitalize the first letter of each component except the first one
        # with the 'title' method and join them together.
        name = components[0] + "".join(x.title() for x in components[1:])

    return name


def str_to_snake(name):
    s = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s).lower()


def convert_dict(fun, d, recurse=True):
    converted = {}

    for key, value in d.items():
        if isinstance(value, dict) and recurse:
            value = convert_dict(fun, value)

        converted[fun(key)] = value

    return converted


def to_camel(d):
    return convert_dict(str_to_camel, d)


def from_camel(d):
    return convert_dict(str_to_snake, d)
