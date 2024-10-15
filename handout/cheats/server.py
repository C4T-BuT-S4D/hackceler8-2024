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

    t = threading.Thread(target=lambda: app.run(host="localhost", port=port))
    t.start()

    return t
