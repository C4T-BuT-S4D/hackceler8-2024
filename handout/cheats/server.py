import json
import logging
import os
import threading
from collections import defaultdict
from copy import deepcopy

from flask import Flask, request, redirect, url_for, render_template, send_from_directory

from cheats.settings import get_settings, update_settings, settings_forms
from cheats.state import get_state, update_state, State

def run_cheats_server(port: int) -> threading.Thread:
    app = Flask(__name__)
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    logging.getLogger('werkzeug').setLevel(logging.WARN)

    @app.get("/assets/<path:path>")
    def assets_static(path="."):
        return send_from_directory(
            os.path.join(os.path.dirname(__file__), "assets"), path
        )

    @app.get("/recordings/<path:path>")
    def recordings_autoindex(path="."):
        return send_from_directory(
            os.path.join(os.path.dirname(__file__), "recordings"), path
        )
    
    @app.route("/", methods=["GET"])
    def overview():
        state = get_state()
        return render_template("overview.html", state=state)
    
    @app.route("/track", methods=["POST"])
    def track():
        mapname = request.form.get("mapname")
        objnametype = request.form.get("objnametype")
        objname = request.form.get("objname")

        state = get_state()
        if state is None:
            return redirect(url_for("overview"))
        
        track_name = f"{mapname}_{objnametype}_{objname}".lower()
        do_track = True

        # atomically set tracking to true for the object
        def update(s: State):
            for obj in s.allobjs:
                if str(obj.mapname) == mapname and str(obj.obj.nametype) == objnametype and (str(obj.obj.name) == objname or (obj.obj.nametype == "warp" and str(obj.obj.map_name) == objname)):
                    obj.tracking = not obj.tracking
                    if obj.tracking:
                        logging.info(f"Tracking {track_name}")
                    else:
                        nonlocal do_track
                        do_track = False
                        logging.info(f"Stopped tracking {track_name}")
                    break
            return s
        update_state(update)

        if do_track:
            update_settings(lambda s: s["exact_track_objects"].add(track_name))
        else:
            update_settings(lambda s: s["exact_track_objects"].remove(track_name))

        return redirect(url_for("overview"))


    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        settings = get_settings()

        forms = [
            form(request.form, **settings)
            if request.method == "POST"
            else form(**settings)
            for form in settings_forms
        ]

        if request.method == "POST":
            data = dict()
            for form in forms:
                data.update(**deepcopy(form.data))

            logging.info(f"Updating cheat settings: {data}")

            update_settings(lambda s: s.update(**data))
            return redirect(url_for("settings"))

        return render_template("settings.html", forms=forms)

    @app.route("/macros", methods=["GET", "POST"])
    def macros():
        all_macros = get_settings()["macros"]

        chosen_macro = request.args.get("macro")
        if chosen_macro is None:
            chosen_macro = "0"

        try:
            chosen_macro = int(chosen_macro)
        except:
            return redirect(url_for("macros"))

        if chosen_macro < 0 or chosen_macro > len(all_macros):
            return redirect(url_for("macros"))

        if request.method == "POST":
            macro = all_macros[chosen_macro]
            macro.name = request.form.get("name")
            macro.keys = request.form.get("keys")

            update_settings(lambda s: s.update(macros=all_macros))

            with open(os.path.join(os.path.dirname(__file__), "macros.json"), "w") as f:
                json.dump([json.dumps({"name": macro.name, "keys": macro.keys}) for macro in all_macros], f)

            return redirect(url_for("macros", macro=chosen_macro))

        return render_template(
            "macros.html",
            all_macros=all_macros,
            chosen_macro=chosen_macro,
        )

    @app.route("/recordings", methods=["GET", "POST"])
    def recordings():
        all_recordings = os.listdir(
            os.path.join(os.path.dirname(__file__), "recordings")
        )

        recordings_by_map = defaultdict(list)
        for recording in all_recordings:
            if recording.count("_") < 1:
                continue
            if not recording.endswith(".json"):
                continue

            recordings_by_map[recording.split("_", 1)[0]].append(recording)

        map_names = sorted(recordings_by_map.keys())

        # Automatically reset the chosen recording if it is no longer available
        previously_chosen_recording = get_settings()["recording_filename"]
        if previously_chosen_recording is not None and previously_chosen_recording not in all_recordings:
            update_settings(lambda s: s.update(recording_filename=None))
            previously_chosen_recording = None

        chosen_recording = request.args.get("recording")
        chosen_map = request.args.get("map")

        # Fallback to the chosen recording from settings, otherwise select the first map available and the first recording from it
        if chosen_recording is None and chosen_map is None:
            chosen_recording = previously_chosen_recording

        if (
             chosen_map is None
             and chosen_recording is not None
             and chosen_recording.count("_") >= 1
        ):
            # guaranteed to be valid map because we check that the previously chosen recording is available,
            # otherwise this might be invalid, in which case a redirect will occur and remove the recording parameter
            chosen_map = chosen_recording.split("_", 1)[0]

        if chosen_map is None and len(map_names) > 0:
            chosen_map = map_names[0]

        if len(map_names) > 0 and chosen_map not in map_names:
            return redirect(url_for("recordings"))

        map_recordings = None
        if chosen_map is not None:
            map_recordings = recordings_by_map.get(chosen_map)
        if map_recordings is not None:
            map_recordings = sorted(map_recordings, reverse=True)

        # Automatically select the previously chosen recording if it is for the selected map
        if (
            chosen_recording is None
            and map_recordings is not None
            and previously_chosen_recording is not None
            and previously_chosen_recording.count("_") >= 1
            and previously_chosen_recording.split("_", 1)[0] == chosen_map
        ):
            chosen_recording = previously_chosen_recording

        if (
            chosen_recording is None
            and map_recordings is not None
            and len(map_recordings) > 0
        ):
            chosen_recording = map_recordings[0]

        if map_recordings is not None and chosen_recording not in map_recordings:
            return redirect(url_for("recordings", map=chosen_map))
        elif map_recordings is None and chosen_recording is not None:
            update_settings(lambda s: s.update(recording_filename=None))
            return redirect(url_for("recordings"))

        if request.method == "POST":
            update_settings(lambda s: s.update(recording_filename=chosen_recording))

            logging.info(f"Set chosen recording to {chosen_recording}")
            return redirect(url_for("recordings", **request.args))

        screenshot_name = None
        if chosen_recording is not None:
            screenshot_name = chosen_recording.removesuffix(".json") + ".jpeg"

        return render_template(
            "recordings.html",
            maps=map_names,
            chosen_map=chosen_map,
            map_recordings=map_recordings,
            chosen_recording=chosen_recording,
            screenshot_name=screenshot_name,
        )

    t = threading.Thread(target=lambda: app.run(host="localhost", port=port), daemon=True)
    t.start()

    return t
