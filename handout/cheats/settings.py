import json
import logging
import os
from copy import deepcopy
from threading import RLock
from typing import Callable, TypedDict

from wtforms import BooleanField
from wtforms import FloatField
from wtforms import Form
from wtforms import IntegerField
from wtforms import StringField

from cheats.lib.macro import Macro

class ExtraSettings(Form):
    title = "Extra"

    slow_ticks_count = IntegerField(
        default=1,
        label="Slow ticks count",
        description="Number of ticks to emulate in slow_ticks_mode",
    )

    dodge = BooleanField(
        default=True,
        label="Dodge projectiles",
    )

    semirun_100 = BooleanField(
        default=True,
        label="Semi-run at stamina 100",
        description="Automatically toggle sprinting",
    )

    auto_recording_interval = IntegerField(
        default=5,
        label="Auto recording interval",
        description="Interval between auto recordings in seconds",
    )

    cancel_applying_ticks_on_key_pressed = BooleanField(
        default=True,
        label="Cancel applying ticks on key pressed",
        description="Cancel applying ticks on key pressed",
    )

    fast_replay = BooleanField(
        default=False,
        label="Fast replay",
        description="Enable it only for standalone",
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

    allow_damage = BooleanField(
        default=False,
        label="Allow damage",
        description="Allow taking damage",
    )

    damage_optimization_level = IntegerField(
        default=0,
        label="Damage optimization level",
        description="Number of times to optimize damage",
    )

    damage_optimization_timeout = IntegerField(
        default=1,
        label="Damage optimization timeout",
        description="Timeout for damage optimization iteration",
    )

    draw_pathfinding_center_points = BooleanField(
        default=True,
        label="Draw pathfinding center points",
    )


class SettingsDict(TypedDict):
    slow_ticks_count: int
    semirun_100: bool
    auto_recording_interval: int
    object_hitbox: int
    draw_names: bool
    draw_hitboxes: bool
    draw_lines: bool
    track_objects: str
    timeout: int
    validate_transitions: bool
    always_shift: bool
    disable_shift: bool
    allowed_moves: str
    heuristic_weight: float
    simple_geometry: bool
    state_batch_size: int
    recording_filename: str
    macros: list[Macro]
    cancel_applying_ticks_on_key_pressed: bool
    fast_replay: bool
    exact_track_objects: set[str]
    allow_damage: bool
    damage_optimization_level: int
    damage_optimization_timeout: int
    draw_pathfinding_center_points: bool


settings_forms = [ExtraSettings, RenderingSettings, PathfindingSettings]

__lock: RLock = RLock()
__settings: SettingsDict = {
    "recording_filename": None,
    "macros": [Macro(name=f"Macro {i + 1}", keys="", force_keys=False) for i in range(9)],
    "exact_track_objects": set() # Enabled via overview
}


def init_settings():
    # initialize default settings from forms
    forms = [form() for form in settings_forms]
    data = get_settings()
    for form in forms:
        data.update(**deepcopy(form.data))

    # load saved macros
    try:
        with open(os.path.join(os.path.dirname(__file__), "macros.json")) as f:
            macros = json.load(f)
        macros = [Macro(**json.loads(m)) for m in macros]
        # merge only those macros which exist instead of overwriting
        for i, macro in enumerate(macros):
            data["macros"][i] = macro
    except FileNotFoundError:
        pass
    except Exception as e:
        logging.warning(f"Failed to load macros from macros.json: {e}")

    # load saved recording filename
    try:
        with open(os.path.join(os.path.dirname(__file__), "recording_filename.txt")) as f:
            data["recording_filename"] = f.read().strip()
    except FileNotFoundError:
        pass
    except Exception as e:
        logging.warning(f"Failed to load recording filename from recording_filename.txt: {e}")

    logging.info(f"Initial settings: {data}")
    update_settings(lambda s: s.update(**data))


def get_settings() -> SettingsDict:
    with __lock:
        return deepcopy(__settings)


def update_settings(upd: Callable[[SettingsDict], None]):
    with __lock:
        upd(__settings)
