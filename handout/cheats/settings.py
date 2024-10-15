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

    draw_lines = BooleanField(
        default=False,
        label="Draw lines to items",
    )

    track_objects = StringField(
        default="",
        label="Track objects",
        description="Comma-separated list of objects to track",
    )


class PathfindingSettings(Form):
    title = "Pathfinding"

    timeout = IntegerField(
        default=5,
        label="Timeout",
        description="Timeout for pathfinding in seconds",
    )

    validate_transitions = BooleanField(
        default=False,
        label="Validate transitions",
    )

    always_shift = BooleanField(
        default=True,
        label="Always shift",
        description="Always shift when pathfinding",
    )

    disable_shift = BooleanField(
        default=False,
        label="Disable shift",
        description="Disable shift when pathfinding",
    )

    allowed_moves = StringField(
        default="",
        label="Allowed moves",
        description="Comma-separated list of moves to allow",
    )

    heuristic_weight = FloatField(
        default=1.0,
        label="Heuristic weight",
        description="Weight of heuristic in A*",
    )

    simple_geometry = BooleanField(
        default=False,
        label="Simple geometry",
        description="Use simple geometry for pathfinding",
    )

    state_batch_size = IntegerField(
        default=16384,
        label="State batch size",
        description="Number of states to process in batch",
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
