import json
import logging
import os
import threading
from copy import deepcopy

from flask import Flask, request, redirect, url_for, render_template, send_from_directory

from cheats.settings import get_settings, update_settings, settings_forms

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

    @app.route("/", methods=["GET", "POST"])
    def index():
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
            return redirect(url_for("index"))

        return render_template("index.html", forms=forms)

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

    t = threading.Thread(target=lambda: app.run(host="localhost", port=port))
    t.start()

    return t
