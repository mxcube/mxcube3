# -*- coding: utf-8 -*-
import gevent
import logging
from flask import (
    Blueprint,
    session,
    jsonify,
    Response,
    request,
    make_response,
    copy_current_request_context,
)

from flask_socketio import join_room, leave_room

from mxcube3.core import loginutils


def init_route(mxcube, server, url_prefix):
    bp = Blueprint("remote_access", __name__, url_prefix=url_prefix)

    @bp.route("/request_control", methods=["POST"])
    @server.restrict
    def request_control():
        """
        """
        @copy_current_request_context
        def handle_timeout_gives_control(sid, timeout=30):
            gevent.sleep(timeout)

            if mxcube.TIMEOUT_GIVES_CONTROL:
                user = loginutils.get_user_by_sid(sid)

                # Pass control to user if still waiting
                if user.get("requestsControl"):
                    toggle_operator(sid, "Timeout expired, you have control")

        data = request.get_json()
        remote_addr = loginutils.remote_addr()

        # Is someone already asking for control
        for observer in loginutils.get_observers():
            if observer["requestsControl"] and observer["host"] != remote_addr:
                msg = "Another user is already asking for control"
                return make_response(msg, 409)

        user = loginutils.get_user_by_sid(session.sid)

        user["name"] = data["name"]
        user["requestsControl"] = data["control"]
        user["message"] = data["message"]

        observers = loginutils.get_observers()
        gevent.spawn(handle_timeout_gives_control, session.sid, timeout=10)

        server.emit("observersChanged", observers, namespace="/hwr")

        return make_response("", 200)


    @bp.route("/take_control", methods=["POST"])
    @server.restrict
    def take_control():
        """
        """
        # Already master do nothing
        if loginutils.is_operator(session.sid):
            return make_response("", 200)

        # Not inhouse user so not allowed to take control by force,
        # return error code
        if not session["loginInfo"]["loginRes"]["Session"]["is_inhouse"]:
            return make_response("", 409)

        toggle_operator(session.sid, "You were given control")

        return make_response("", 200)


    @bp.route("/give_control", methods=["POST"])
    @server.restrict
    def give_control():
        """
        """
        sid = request.get_json().get("sid")
        toggle_operator(sid, "You were given control")

        return make_response("", 200)


    def toggle_operator(new_op_sid, message):
        current_op = loginutils.get_operator()

        new_op = loginutils.get_user_by_sid(new_op_sid)
        loginutils.set_operator(new_op["sid"])
        new_op["message"] = message

        observers = loginutils.get_observers()

        # Append the new data path so that it can be updated on the client
        new_op["rootPath"] = mxcube.mxcubecore.beamline_ho.session.get_base_image_directory()

        # Current op might have logged out, while this is happening
        if current_op:
            current_op["rootPath"] = mxcube.mxcubecore.beamline_ho.session.get_base_image_directory()
            current_op["message"] = message
            server.emit(
                "setObserver", current_op, room=current_op["socketio_sid"], namespace="/hwr"
            )

        server.emit("observersChanged", observers, namespace="/hwr")
        server.emit("setMaster", new_op, room=new_op["socketio_sid"], namespace="/hwr")


    def remain_observer(observer_sid, message):
        observer = loginutils.get_user_by_sid(observer_sid)
        observer["message"] = message

        server.emit(
            "setObserver", observer, room=observer["socketio_sid"], namespace="/hwr"
        )


    @bp.route("/", methods=["GET"])
    @server.restrict
    def observers():
        """
        """
        data = {
            "observers": loginutils.get_observers(),
            "sid": session.sid,
            "master": loginutils.is_operator(session.sid),
            "observerName": loginutils.get_observer_name(),
            "allowRemote": mxcube.ALLOW_REMOTE,
            "timeoutGivesControl": mxcube.TIMEOUT_GIVES_CONTROL,
        }

        return jsonify(data=data)


    @bp.route("/allow_remote", methods=["POST"])
    @server.restrict
    def allow_remote():
        """
        """
        allow = request.get_json().get("allow")

        if mxcube.ALLOW_REMOTE and allow == False:
            server.emit("forceSignoutObservers", {}, namespace="/hwr")

        mxcube.ALLOW_REMOTE = allow

        return Response(status=200)


    @bp.route("/timeout_gives_control", methods=["POST"])
    @server.restrict
    def timeout_gives_control():
        """
        """
        control = request.get_json().get("timeoutGivesControl")
        mxcube.TIMEOUT_GIVES_CONTROL = control

        return Response(status=200)


    def observer_requesting_control():
        observer = None

        for o in loginutils.get_observers():
            if o["requestsControl"]:
                observer = o

        return observer


    @bp.route("/request_control_response", methods=["POST"])
    @server.restrict
    def request_control_response():
        """
        """
        data = request.get_json()
        new_op = observer_requesting_control()

        # Request was denied
        if not data["giveControl"]:
            remain_observer(new_op["sid"], data["message"])
        else:
            toggle_operator(new_op["sid"], data["message"])

        new_op["requestsControl"] = False

        return make_response("", 200)


    @bp.route("/chat", methods=["POST"])
    @server.restrict
    def append_message():
        message = request.get_json().get("message", "")
        sid = request.get_json().get("sid", "")

        if message and sid:
            loginutils.append_message(message, sid)

        return Response(status=200)


    @bp.route("/chat", methods=["GET"])
    @server.restrict
    def get_all_mesages():
        return jsonify({"messages": loginutils.get_all_messages()})


    @server.flask_socketio.on("connect", namespace="/hwr")
    @server.ws_restrict
    def connect():
        user = loginutils.get_user_by_sid(session.sid)

        # Make sure user is logged, session may have been closed i.e by timeout
        if user:
            user["socketio_sid"] = request.sid

        # (Note: User is logged in if operator)
        if loginutils.is_operator(session.sid):
            if (
                not mxcube.mxcubecore.beamline_ho.queue_manager.is_executing()
                and not loginutils.DISCONNECT_HANDLED
            ):
                loginutils.DISCONNECT_HANDLED = True
                server.emit("resumeQueueDialog", namespace="/hwr")
                msg = "Client reconnected, Queue was previously stopped, asking "
                msg += "client for action"
                logging.getLogger("HWR").info(msg)


    @server.flask_socketio.on("disconnect", namespace="/hwr")
    @server.ws_restrict
    def disconnect():
        if (
            loginutils.is_operator(session.sid)
            and mxcube.mxcubecore.beamline_ho.queue_manager.is_executing()
        ):

            loginutils.DISCONNECT_HANDLED = False
            logging.getLogger("HWR").info("Client disconnected")


    @server.flask_socketio.on("setRaMaster", namespace="/hwr")
    @server.ws_restrict
    def set_master(data):
        leave_room("observers", namespace="/ui_state")
        
        return session.sid


    @server.flask_socketio.on("setRaObserver", namespace="/hwr")
    @server.ws_restrict
    def set_observer(data):
        name = data.get("name", "")
        observers = loginutils.get_observers()
        observer = loginutils.get_user_by_sid(session.sid)

        if observer and name:
            observer["name"] = name
            server.emit("observerLogin", observer, include_self=False, namespace="/hwr")

        server.emit("observersChanged", observers, namespace="/hwr")
        join_room("observers", namespace="/ui_state")

        return session.sid

    return bp