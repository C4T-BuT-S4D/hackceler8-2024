import json
import logging
import os
from copy import deepcopy
from threading import RLock
from typing import Callable

from wtforms import BooleanField
from wtforms import FloatField
from wtforms import Form
from wtforms import IntegerField
from wtforms import StringField

class ExtraSettings(Form):
    title = "Extra"

    slow_ticks_count = IntegerField(
        default=1,
        label="Slow ticks count",
        description="Number of ticks to emulate in slow_ticks_mode",
    )


class RenderingSettings(Form):
    title = "Rendering"

    object_hitbox = IntegerField(
        default=3,
        label="Object hitbox width",
        description="Width of object hitbox in pixels",
    )

    draw_names = BooleanField(
        default=False,
        label="Draw object names",
    )

    draw_hitboxes = BooleanField(
        default=True,
        label="Draw object hitboxes",
    )


class PathfindingSettings(Form):
    title = "Pathfinding"

    timeout = IntegerField(
        default=5,
        label="Timeout",
    )

settings_forms = [ExtraSettings, RenderingSettings, PathfindingSettings]

__lock: RLock = RLock()
__settings: dict = {
    "recording_filename": None,
}


def init_settings():
    forms = [form() for form in settings_forms]
    data = get_settings()
    for form in forms:
        data.update(**deepcopy(form.data))
    logging.info(f"Initial settings: {data}")
    update_settings(lambda s: s.update(**data))


def get_settings() -> dict:
    with __lock:
        return deepcopy(__settings)


def update_settings(upd: Callable[[dict], None]):
    with __lock:
        upd(__settings)
