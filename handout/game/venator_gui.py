# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import Optional
import imgui
import os
import moderngl_window as mglw

from game import constants
from game.engine import gfx
from game.engine.keys import Keys
from game.venator import Venator
from game.components.boss.bg import BossBG

# cheats imports
import time
import secrets
from copy import deepcopy
from cheats.settings import get_settings, update_settings
from cheats.state import update_state, State, MapFlag, MapObject
from cheats.lib.tick_data import TickData
from moderngl_window.context.base import KeyModifiers
from game.engine.generics import GenericObject
import search

SCREEN_TITLE = "Hackceler8-24"

class Hackceler8(gfx.Window):
    window_size = (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
    title = SCREEN_TITLE

    def __init__(self, net=None, is_prerender=False, **kwargs):
        super().__init__(**kwargs)
        self.heart = gfx.GuiImage.load(self, "resources/objects/heart.png")
        self.star = gfx.GuiImage.load(self, "resources/objects/star.png")
        self.stamina = gfx.GuiImage.load(self, "resources/objects/stamina.png")

        self.boss_bg = None

        self.net = net
        self.game: Optional[Venator] = None

        self.main_layer = gfx.CombinedLayer()

        self.camera = gfx.Camera(self.window_size[0], self.window_size[1], constants.DEFAULT_SCALE)
        self.gui_camera = gfx.Camera(self.window_size[0], self.window_size[1])  # For screen space stationary objects.

        # Load the game immediately instead of the original 10 seconds
        self.loading_screen_timer = 0

        # cheats settings
        self.render_gui = True # needed to skip rendering the GUI for screenshots
        self.debug_labels_font_size = 8 # modified for full-size screenshots
        self.ticks_to_apply: list[TickData] = []
        self.draws: list[float] = []
        self.single_tick_mode = False
        self.last_save = 0
        self.recording_enabled = False
        self.screenshot_recordings = []
        self.is_prerender = is_prerender
        self.playing_recording = False
        self.auto_shoot = False

        # map item name to map name
        self.object_map_mapping: dict[str, str] = {}
        self.map_connections: dict[str, list[str]] = {}
        self.map_warps: dict[(str, str), (int, int)] = {}
        self.object_links: list[tuple[str, GenericObject]] = []

        self.paths_built_for: Optional[str] = None
        self.object_paths: dict[str, list[str]] = {}

        self.map_overview_mode = False
        self.map_overview_keys_pressed: set[Keys] = set()

        self.debug_objects: dict[str, list[gfx.ShapeDrawParams]] = {}

        self.projected_width = 0
        self.projected_height = 0

    def setup_game(self):
        self.game = Venator(self.net, is_server=False)

        self._save_overview_state()
        self._build_object_map_mapping()

    # Do not resize anything. This way the regular camera will scale, and gui is drawn separately anyway.
    def on_resize(self, width, height):
        logging.info(f'on resize {width=} {height=}')
        self.projected_width = width
        self.projected_height = height

    def _center_camera_to_player(self):
        if not self.game.ready or not self.game.map_loaded:
            return

        screen_center_x = self.game.player.x - (self.camera.viewport_width / 2)
        screen_center_y = self.game.player.y - (self.camera.viewport_height / 2)

        # Commented by pomo to enable viewing the entire map

        # Don't let camera travel past 0
        # screen_center_x = max(screen_center_x, 0)
        # screen_center_y = max(screen_center_y, 0)

        # additional controls to avoid showing around the map
        # max_screen_center_x = (
        #         self.game.tiled_map.map_size_pixels.width - self.camera.viewport_width
        # )
        # max_screen_center_y = (
        #         self.game.tiled_map.map_size_pixels.height - self.camera.viewport_height
        # )
        # screen_center_x = min(screen_center_x, max_screen_center_x)
        # screen_center_y = min(screen_center_y, max_screen_center_y)

        player_centered = screen_center_x, screen_center_y
        self.camera.move_to(player_centered)

    def draw(self):
        cheats_settings = get_settings() # retrieve cheats settings only once per draw

        if self.game is None or not self.game.ready or not self.game.map_loaded:
            mglw.ContextRefs.WINDOW.set_icon(os.path.abspath("resources/character/32bit/main32.PNG"))
            self.wnd.ctx.clear(color=(0, 0.5, 0, 1))
            gfx.draw_txt("loading", gfx.FONT_PIXEL[60], "Loading game...",
                         240, constants.SCREEN_HEIGHT/2 - 30, color=(164/255, 198/255, 57/255))
            return
        self.wnd.ctx.clear(color=(0, 0, 0, 1))

        if self.game.arcade_system is not None:
            self.game.arcade_system.draw()
            if self.game.screen_fader is not None:
                self.game.screen_fader.draw()
            # Arcade system covers the entire screen.
            return

        self._record_draw()

        self.camera.update()
        self.camera.use()

        gfx.DEFAULT_ATLAS.maybe_build()
        if self.boss_bg is not None:
            self.boss_bg.draw()
        else:
            if self.game.prerender is None:
                self.game.scene.draw()
            else:
                self.game.prerender.draw_all_cached()

        self.main_layer.add_many(o.get_draw_info() for o in self.game.tiled_map.env_tiles)
        self.main_layer.draw(); self.main_layer.clear()

        self.main_layer.add_many(o.get_draw_info() for o in self.game.objects if not o.render_above_player)
        self.main_layer.draw(); self.main_layer.clear()

        if self.game.painting_system is not None:
            self.game.painting_system.draw()

        self.game.projectile_system.draw()

        if self.game.player is not None:
            p = self.game.player.get_draw_info()
            self.main_layer.add_many(p)
            self.main_layer.draw()
            self.main_layer.clear()

        self.main_layer.add_many(o.get_draw_info() for o in self.game.objects if o.render_above_player)
        self.main_layer.draw(); self.main_layer.clear()

        self._draw_debug_ui(cheats_settings)

        self.gui_camera.update()
        self.gui_camera.use()

        if not self.render_gui:
            return

        if self.game.boss is not None:
            self.game.boss.draw_gui()

        if self._white_text():
            imgui.push_style_color(imgui.COLOR_TEXT, 1,1,1,1)
        else:
            imgui.push_style_color(imgui.COLOR_TEXT, 0,0,0,1)

        gfx.draw_img("health", self.heart, 30, -80)
        gfx.draw_txt("health", gfx.FONT_PIXEL[30], ":%.02f" % self.game.player.health,
                     90, -75)
        gfx.draw_img("stars", self.star, -190, -80)
        gfx.draw_txt("stars", gfx.FONT_PIXEL[30], ":%.d" % self.game.match_flags.stars(),
                     -130, -75)
        gfx.draw_img("stamina", self.stamina, -180, -140)
        gfx.draw_txt("stamina", gfx.FONT_PIXEL[30], ":%.d" % self.game.player.stamina,
                     -130, -140)
        imgui.pop_style_color()  # COLOR_TEXT

        gfx.draw_txt("ticks", gfx.FONT_PIXEL[30], "T %.d" % self.game.tics,
                     10, 10)

        if len(self.draws) > 1:
            gfx.draw_txt("fps", gfx.FONT_PIXEL[30], "F %.02f" % (len(self.draws) / (self.draws[-1] - self.draws[0])),
                        10, 40)

        if self.game.cheating_detected:
            txt = "   OUT OF SYNC\nCHEATING DETECTED"
            gfx.draw_txt("cheating_detected", gfx.FONT_PIXEL[30], txt,
                         400, constants.SCREEN_HEIGHT/2 - 40, color=(1, 0, 0))
            return

        if self.game.player.dead:
            gfx.draw_txt("youdied", gfx.FONT_PIXEL[60], "You died ):",
                         350, constants.SCREEN_HEIGHT/2 - 70, color=(1, 0, 0))

        if self.game.won:
            if self._white_text():
                imgui.push_style_color(imgui.COLOR_TEXT, 1,1,1,1)
            else:
                imgui.push_style_color(imgui.COLOR_TEXT, 0,0,0,1)

            y = 270
            if self.game.current_map.endswith("_boss"):
                y = 460
                gfx.draw_txt("won_1", gfx.FONT_PIXEL[30], "Thank you for freeing me!", 300, 100)
            gfx.draw_txt("won_2", gfx.FONT_PIXEL[30], "Congratulations, you beat the game!", 130, y)
            imgui.pop_style_color()  # COLOR_TEXT

        if self.game.display_inventory:
            self.game.inventory.draw()

        if self.game.textbox is not None:
            self.game.textbox.draw()

    def draw_fader(self):
        if self.game is None:
            return
        if self.game.screen_fader is not None:
            self.game.screen_fader.draw(scale=self.camera.scale)

    def tick(self, _delta_time: float):
        if self.game is None:
            if self.loading_screen_timer > 0:
                self.loading_screen_timer -= 1
                return
            self.setup_game()

        if self.map_overview_mode:
            self._tick_map_overview()
            return

        if self.playing_recording and len(self.ticks_to_apply) == 0:
            self.single_tick_mode = True
            self.playing_recording = False

        if not self.single_tick_mode and not self.map_overview_mode:
            self.tick_once()
            if get_settings()["fast_replay"]:
                while len(self.ticks_to_apply) > 0:
                    self.tick_once()

    def render(self, time: float, frame_time: float):
        super().render(time, frame_time)

        if len(self.screenshot_recordings) > 0:
            import threading
            image = self.get_screenshot_image()
            while len(self.screenshot_recordings) > 0:
                format = "jpeg"
                path = self.screenshot_recordings.pop(0) + "." + format
                threading.Thread(target=lambda: self.save_screenshot_image(image, path, format)).start()

        # Perform prerender after game is setup and ready
        if self.is_prerender and self.game and self.game.tics > 60:
            self.is_prerender = False # Avoid infinite recursion
            update_settings(lambda s: s.update(draw_names=True))
            self.prerender_maps()
            self.wnd.close()

    def on_key_press(self, symbol: int, modifiers: KeyModifiers):
        k = Keys.from_ui(symbol)

        if k in {
            Keys.NUMBER_1,
            Keys.NUMBER_2,
            Keys.NUMBER_3,
            Keys.NUMBER_4,
            Keys.NUMBER_5,
            Keys.NUMBER_6,
            Keys.NUMBER_7,
            Keys.NUMBER_8,
            Keys.NUMBER_9,
        } and modifiers.alt:
            macros = get_settings()["macros"]

            macro_index = ord(k.value[0]) - ord(Keys.NUMBER_1.value[0])
            if macro_index < 0 or macro_index >= len(macros):
                logging.error(f'bad macro index "{macro_index}"')
                return

            try:
                macro = eval(macros[macro_index].keys)
            except Exception as e:
                logging.error(f'bad macro "{macros[macro_index].name}" (eval error): {e}')
                return

            if not isinstance(macro, list):
                logging.error(f'bad macro "{macros[macro_index].name}" (eval result is not a list): "{macro}"')
                return

            macro_ticks = []
            for macro_tick in macro:
                tick_keys = set()
                text_input = None
                if isinstance(macro_tick, str):
                    for key in macro_tick:
                        key_v = Keys.from_serialized(key)
                        if not key_v:
                            logging.error(f'bad macro (not key) "{key}"')
                            return
                        tick_keys.add(key_v)
                elif isinstance(macro_tick, dict):
                    tick_keys = set(macro_tick.get("keys", []))
                    text_input = macro_tick.get("text_input")
                else:
                    logging.error(f'bad macro (not str or dict) "{macro_tick}"')
                    return
                macro_ticks.append(TickData(keys=list(tick_keys), force_keys=False, text_input=text_input))

            logging.info(f'applying macro "{macros[macro_index].name}"')
            self.ticks_to_apply.extend(macro_ticks)
            return

        if k == Keys.N and modifiers.ctrl:
            center = self.camera.center()
            self.camera.set_scale(self.camera.scale + 1)
            self.camera.center_on(center[0], center[1])
            return
        
        if k == Keys.J and modifiers.ctrl:
            self.auto_shoot = not self.auto_shoot
            logging.info(f"auto shoot: {self.auto_shoot}")
            return

        if k == Keys.M and modifiers.ctrl:
            center = self.camera.center()
            self.camera.set_scale(self.camera.scale - 1)
            self.camera.center_on(center[0], center[1])
            return
        
        if k == Keys.O and modifiers.ctrl:
            self.map_overview_mode = not self.map_overview_mode
            logging.info(f"map overview mode: {self.map_overview_mode}")

            if not self.map_overview_mode:
                self.map_overview_keys_pressed.clear()
                self._center_camera_to_player()

            return
        
        if k == Keys.EQUAL:
            self.single_tick_mode = not self.single_tick_mode
            logging.info(f"single tick mode: {self.single_tick_mode}")
            return

        if k == Keys.BACKSPACE:
            for _ in range(get_settings()["slow_ticks_count"]):
                self.tick_once()
            return
        
        if k == Keys.R and modifiers.ctrl:
            if self.recording_enabled:
                self.save_recording(suffix='end-recording')
                self.stop_recording()
                return
            
            self.start_recording()
            self.ticks_to_apply.append(TickData(keys=[Keys.R], force_keys=True))
            return
        
        if k == Keys.L and modifiers.ctrl:
            self.stop_recording()
            self.start_recording()
            self.load_recording()
            return
        
        if k == Keys.S and modifiers.ctrl:
            self.save_recording(suffix='manual')
            return

        if symbol == self.wnd.keys.F1 and modifiers.shift:
            self.screenshot()
            return
        
        if symbol == self.wnd.keys.F2 and modifiers.shift:
            self.full_screenshot()
            return
        
        if symbol == self.wnd.keys.F3 and modifiers.shift:
            self.prerender_maps()
            return
        
        cancel_applying_ticks_on_key_pressed = get_settings()["cancel_applying_ticks_on_key_pressed"]

        if self.game == None:
            return

        if self.map_overview_mode:
            if k in {Keys.W, Keys.A, Keys.S, Keys.D}:
                self.map_overview_keys_pressed.add(k)
            return

        if k:
            self.game.raw_pressed_keys.add(k)
            if cancel_applying_ticks_on_key_pressed:
                self.ticks_to_apply = []
                self.playing_recording = False

    def on_key_release(self, symbol: int, _modifiers: int):
        if self.game is None:
            return

        k = Keys.from_ui(symbol)

        if self.map_overview_mode:
            self.map_overview_keys_pressed.discard(k)
            return

        if k in self.game.raw_pressed_keys:
            self.game.raw_pressed_keys.remove(k)

    def _update_boss_bg(self):

        if self.boss_bg is None:
            if (self.game.current_map.endswith("_boss")
                and self.game.screen_fader is not None
                and not self.game.screen_fader.fade_in):
                self.boss_bg = BossBG()
        else:
            if (not self.game.current_map.endswith("_boss")
                and self.game.screen_fader is not None
                and not self.game.screen_fader.fade_in):
                self.boss_bg = None
        if self.boss_bg is not None:
            if "dialogue" in self.game.current_map:
                self.boss_bg.is_dialogue = True
            elif "fighting" in self.game.current_map:
                self.boss_bg.is_dialogue = False
            self.boss_bg.tick()

    def _white_text(self):
        if self.game.current_map.endswith("_boss") and self.boss_bg is not None:
            return self.boss_bg.white_text()
        return self.game.current_map != "cloud"

    # Cheats added functions

    def tick_once(self):
        cheats_settings = get_settings()

        keys_to_restore = self.game.raw_pressed_keys.copy()
        forced_tick = False
        if self.ticks_to_apply:
            forced_tick = True
            tick_to_apply = self.ticks_to_apply.pop(0)

            if tick_to_apply.force_keys:
                self.game.raw_pressed_keys = set(k for k in tick_to_apply.keys)
            else:
                self.game.raw_pressed_keys |= set(k for k in tick_to_apply.keys)

            if tick_to_apply.text_input is not None:
                self.game.textbox.text_input.text = tick_to_apply.text_input
                self.game.textbox.text_input.force_text = tick_to_apply.text_input

        # Automatic semi-sprinting and stamina management
        if (player := self.game.player) and not forced_tick:
            walk_keys = {Keys.A, Keys.D} | ({Keys.W, Keys.S} if player.scroller_mode else set())
            if player.stamina == 0 or not self.game.raw_pressed_keys & walk_keys:
                self.game.raw_pressed_keys.discard(Keys.LSHIFT)
            if cheats_settings["semirun_100"]:
                if player.stamina == 100:
                    self.game.raw_pressed_keys.add(Keys.LSHIFT)
            if self.auto_shoot and not Keys.SPACE in self.game.prev_pressed_keys:
                need_shoot = False
                for weap in player.weapons:
                    if weap.equipped and weap.cool_down_timer == 0:
                        need_shoot = True
                        break
                if need_shoot:
                    self.game.raw_pressed_keys.add(Keys.SPACE)

        if self.recording_enabled and time.time() - self.last_save > cheats_settings["auto_recording_interval"]:
            self.save_recording(suffix='auto')

        move = None
        # VALIDATE TRANSITIONS + DODGE
        if self.game != None and self.game.physics_engine != None:
            settings, state, static_state = self._dump_rust_state(enable_portals=False, enable_proj=True)
            keys = self.game.raw_pressed_keys.copy()
            if Keys.W in keys and Keys.W in self.game.prev_pressed_keys:
                keys.remove(Keys.W)

            if Keys.LSHIFT in keys:
                shift = True
                keys.remove(Keys.LSHIFT)
            else:
                shift = False
            keys &= {Keys.W, Keys.A, Keys.S, Keys.D}
            if keys == {Keys.W} or keys == {Keys.W, Keys.A, Keys.D}:
                move = search.Move.W
            elif keys == {Keys.A}:
                move = search.Move.A
            elif keys == {Keys.D}:
                move = search.Move.D
            elif keys == {Keys.W, Keys.A}:
                move = search.Move.WA
            elif keys == {Keys.W, Keys.D}:
                move = search.Move.WD
            elif keys == {Keys.S}:
                move = search.Move.S
            elif keys == {Keys.S, Keys.A}:
                move = search.Move.SA
            elif keys == {Keys.S, Keys.D}:
                move = search.Move.SD
            elif keys == set() or keys == {Keys.A, Keys.D}:
                move = search.Move.NONE
            else:
                logging.warning(f"unexpected move {keys}")
                move = None

            if cheats_settings['validate_transitions'] and move is not None:
                expected = search.get_transition(
                    settings, static_state, state, move, shift
                )
            # DODGES
            if cheats_settings['dodge'] and move is not None and not forced_tick:
                ret = search.dodge_search(settings, state, static_state, move, shift)
                if ret != (move, shift):
                    print('DODGE VIA', (move, shift), 'TO', ret)
                    self.game.raw_pressed_keys = set(search_move_to_keys(ret[0], ret[1]))

        saved_map = self.game.current_map
        was_player_dead = self.game.player and self.game.player.dead
        self.game.tick()

        if cheats_settings["validate_transitions"] and move is not None:    
            attrs = [
                ("x", "x"), 
                ("y", "y"), 
                ("x_speed", "vx"), 
                ("y_speed", "vy"), 
                ("base_x_speed", "base_vx"), 
                ("base_y_speed", "base_vy"),
                ("jump_override", "jump_override"),
                # ("direction", "direction"),
                ("in_the_air", "in_the_air"),
                ("can_jump", "can_jump"),
                ("stamina", "stamina"),
                ("speed_multiplier", "speed_multiplier"),
                ("jump_multiplier", "jump_multiplier"),
            ]
            vals = [
                (getattr(self.game.player, k1), getattr(expected, k2))
                for k1, k2 in attrs
            ]
            if not all(x == y for x, y in vals):
                print(f"{self.game.tics=} incorrect transition:")
                for (k1, _), (v1, v2) in zip(attrs, vals):
                    print(k1, "predicted", v2, "got", v1, f'({v1 == v2=})')
                print()

        if self.recording_enabled:
            if self.game.current_map != saved_map:
                self.save_recording(current_map=saved_map, suffix='map-change')
            elif self.game.player and self.game.player.dead and not was_player_dead:
                self.save_recording(suffix='death')
        self._update_boss_bg()
        self._center_camera_to_player()

        self.game.raw_pressed_keys = keys_to_restore

    def _record_draw(self):
        now = time.time()
        self.draws.append(now)
        while self.draws and now - self.draws[0] > 3:
            self.draws.pop(0)

    def _draw_debug_ui(self, cheats_settings: dict):
        # Build item paths for the current map.
        self._build_object_paths()

        objs = []

        for o in (
            self.game.objects +
            self.game.stateful_objects +
            self.game.projectile_system.weapons +
            self.game.physics_engine.env_tiles +
            [self.game.player]
        ):
            color = None
            match o.nametype:
                case "Wall":
                    color = (255, 0, 0, 255)
                case "NPC":
                    color = (0, 255, 0, 255)
                case "Player":
                    color = (255, 165, 0, 255)
                case "Item":
                    color = (255, 255, 255, 255)
                case "Portal":
                    color = (0, 0, 255, 255)
                case "Enemy":
                    color = (255, 0, 0, 255)
                case "Weapon":
                    color = (255, 215, 0, 255)
                case "ArcadeBox":
                    color = (0, 255, 255, 255)
                case "KeyGate":
                    color = (0, 255, 0, 255)
                case "BossGate":
                    color = (255, 0, 255, 255)
                case "warp":
                    color = (255, 165, 0, 255)
                case "Fire":
                    color = (255, 0, 0, 255)
                case "Ouch":
                    color = (255, 255, 0, 255)
                case "Portal":
                    color = (0, 0, 255, 255)
                case "Element":
                    # olive green
                    color = (107, 142, 35, 255)
                case _:
                    logging.warning(f"skipped object {o.nametype}")

            if color:
                if cheats_settings["draw_hitboxes"]:
                    # don't draw portal hitboxes, they are already outlined
                    if o.nametype != "Portal":
                        objs.append(gfx.lrtb_rectangle_outline(
                            o.x1,
                            o.x2,
                            o.y2,
                            o.y1,
                            color,
                            border=cheats_settings["object_hitbox"],
                        ))
                    else:
                        # draw line to o.dest
                        objs.append(gfx.line(o.x, o.y, o.dest.x, o.dest.y, color))

                    # melee is handled using the HealthDamage modifier, but we want to display the melee range separately
                    if o.nametype == "Enemy" and o.can_melee:
                        dist = o.melee_range
                        objs.append(gfx.lrtb_rectangle_outline(
                            o.x - dist,
                            o.x + dist,
                            o.y + dist,
                            o.y - dist,
                            (255, 100, 0, 255),
                            border=cheats_settings["object_hitbox"]
                        ))

                        # this is hardcoded in code, update it if changed
                        modifier_dist = 80
                        objs.append(gfx.circle_outline(
                            o.x,
                            o.y,
                            modifier_dist,
                            (255, 255, 0, 255),
                            border_width=cheats_settings["object_hitbox"]
                        ))
                    elif (modifier := getattr(o, "modifier", None)) and (min_dist := getattr(modifier, "min_distance", None)) and min_dist > 0:
                        objs.append(gfx.circle_outline(
                            o.x,
                            o.y,
                            min_dist,
                            (255, 255, 0, 255),
                            border_width=cheats_settings["object_hitbox"]
                        ))

                    if o.nametype == "Player":
                        # Draw a point at the player's position
                        objs.append(gfx.lrtb_rectangle_outline(
                            self.game.player.x,
                            self.game.player.x,
                            self.game.player.y,
                            self.game.player.y,
                            color,
                            border=cheats_settings["object_hitbox"]
                        ))

                if cheats_settings["draw_names"] and o.nametype not in {"Wall"}:
                    text = f"{o.nametype}"
                    if o.nametype == "warp":
                        text += f" to {o.map_name}"
                    if name := getattr(o, "name", None):
                        text += f" | {name}"
                    if (health := getattr(o, "health", None)) and o.nametype not in {
                        "warp", "Element", "Portal", "Weapon", "ArcadeBox", "KeyGate", "BossGate",
                        "Ouch", "Fire", "Item", "NPC",
                    }:
                        text += f" | {health:.02f}"
                    if o.nametype == "Enemy" and o.can_shoot:
                        text += f" | st={o.shoot_timer}"
                    if o.nametype == "Element":
                        text += f" | js={o.modifier.jump_speed} g={o.modifier.gravity} ws={o.modifier.walk_speed} jo={o.modifier.jump_override}"

                    x = (o.x1 - self.camera.position.x) / self.camera.scale
                    y = (self.camera.position.y - o.y2) / self.camera.scale - self.debug_labels_font_size * 2
                    if x >= 0 and y <= 0 and x <= self.camera.viewport_width and y >= -self.camera.viewport_height:
                        gfx.draw_txt(f"debug_{o.nametype}_{o.x1}_{o.y1}", gfx.FONT_PIXEL[self.debug_labels_font_size], text,
                                 x, y, color=color)
                        
                if cheats_settings["draw_lines"] and o.nametype in {"Item"}:
                    if o.nametype == "Item":
                        objs.append(gfx.line(self.game.player.x, self.game.player.y, o.x, o.y, color))

        if cheats_settings["track_objects"]:
            tracked_objects = list(map(lambda x: x.strip().lower(), cheats_settings["track_objects"].split(",")))
            for obj_key, obj in self.object_links:
                if not any(obj_key.endswith(tracked_obj) for tracked_obj in tracked_objects):
                    continue
                map_name = self.object_map_mapping[obj_key]
                if map_name == self.game.current_map:
                    objs.append(gfx.line(self.game.player.x, self.game.player.y, obj.x, obj.y, color))
                elif self.game.current_map in self.object_paths[obj_key]:
                    cur_idx = self.object_paths[obj_key].index(self.game.current_map)
                    next_map_name = self.object_paths[obj_key][cur_idx + 1]
                    if (map_name, next_map_name) in self.map_warps:
                        x, y = self.map_warps[(self.game.current_map, next_map_name)]
                        objs.append(gfx.line(self.game.player.x, self.game.player.y, x, y, color))

        if self.recording_enabled:
            pos = list(self.camera.position)
            objs.append(gfx.circle_filled(int(pos[0]) + 650, int(pos[1]) + 120, 30, (255, 0, 0, 255)))

        objs.extend(self.debug_objects.values())
        self.main_layer.add_many(objs)
        self.main_layer.draw(); self.main_layer.clear()

    def _tick_map_overview(self):
        if not self.map_overview_keys_pressed:
            return

        if Keys.W in self.map_overview_keys_pressed:
            self.camera.position.y += 10
        if Keys.A in self.map_overview_keys_pressed:
            self.camera.position.x -= 10
        if Keys.S in self.map_overview_keys_pressed:
            self.camera.position.y -= 10
        if Keys.D in self.map_overview_keys_pressed:
            self.camera.position.x += 10

    def full_screenshot(self, dir="./screenshots", format="jpeg", name: str = None):
        # Precalc the "interesting" area to be displayed in the screenshot
        # by finding the furthest objects in all directions
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        for o in self.game.objects + self.game.stateful_objects:
            min_x = min(min_x, o.x1)
            min_y = min(min_y, o.y1)
            max_x = max(max_x, o.x2)
            max_y = max(max_y, o.y2)

        PADDING = 100
        min_x -= PADDING
        min_y -= PADDING
        max_x += PADDING
        max_y += PADDING

        w, h = max_x - min_x, max_y - min_y

        # commented to use the calculated area instead of the whole map
        # w, h = (
        #     self.game.tiled_map.map_size_pixels.width,
        #     self.game.tiled_map.map_size_pixels.height,
        # )

        ## Save original window rendering state
        original_size = self.wnd.size
        original_buffer_size = self.wnd.buffer_size
        original_viewport = self.wnd.viewport
        original_constants = constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
        original_debug_labels_font_size = self.debug_labels_font_size
        original_camera = self.camera
        original_fbo = self.ctx.fbo

        # Step 1. create a custom framebuffer with the same size as the map to keep the aspect ratio and quality
        fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture(size=(w, h), components=4)],
        )
        fbo.use()
        self.ctx.fbo = fbo

        # Step 2. Set camera with viewport equal to the full size for the whole map to be visible
        self.camera = gfx.Camera(w, h)
        self.camera.move_to((min_x, min_y))

        # Step 3. Update all rendering-related window constants to appear as if the window shows the whole map
        self.wnd._width, self.wnd._height = w, h
        self.wnd._buffer_width, self.wnd._buffer_height = w, h
        self.wnd._viewport = (0, 0, w, h)
        constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT = w, h
        self.resize(w, h)
        self.debug_labels_font_size = 15

        # Step 4. Simulate a fake frame, no tick should happen. Save the screenshot using data from the custom framebuffer.
        self.render_gui = False
        self.render(0, 0)
        self.render(0, 0) # render twice to fix imgui not rendering the text on newly loaded maps
        self.render_gui = True

        path = os.path.join(dir, f"full_{self.game.current_map}_{int(time.time())}.{format}")
        if name is not None:
            path = os.path.join(dir, f"{name}.{format}")
        self._save_screenshot(path, format)
        logging.info(f"Saved full screenshot of map \"{self.game.current_map}\" to \"{path}\"")

        ## Restore original window rendering state
        self.camera = original_camera
        self.ctx.fbo = original_fbo
        self.wnd._width, self.wnd._height = original_size
        self.wnd._buffer_width, self.wnd._buffer_height = original_buffer_size
        self.wnd._viewport = original_viewport
        constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT = original_constants
        self.resize(*original_size)
        self.debug_labels_font_size = original_debug_labels_font_size

    def screenshot(self, dir: str = "./screenshots", format: str = "jpeg"):
        # simulate a fake frame, no tick should happen
        self.render(0, 0)
        path = os.path.join(dir, f"screenshot_{self.game.current_map}_{int(time.time())}.{format}")
        self._save_screenshot(path, format)
        logging.info(f"Saved screenshot on map \"{self.game.current_map}\" to \"{path}\"")

    def get_screenshot_image(self):
        from PIL import Image
        image = Image.frombytes(
            "RGB",
            (
                self.ctx.fbo.viewport[2] - self.ctx.fbo.viewport[0],
                self.ctx.fbo.viewport[3] - self.ctx.fbo.viewport[1],
            ),
            self.ctx.fbo.read(viewport=self.ctx.fbo.viewport, alignment=1),
        )
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        return image

    def _save_screenshot(self, path: str, format: str):
        image = self.get_screenshot_image()
        self.save_screenshot_image(image, path, format)

    def save_screenshot_image(self, image, path: str, format: str):
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        image.save(path, format)
        
    def prerender_maps(self):
        for map in self.game.maps_dict:
            self.game.load_map(map)
            self.full_screenshot(dir="./screenshots/prerender", name=self.game.current_map)
        self.game.load_map("base")

    def load_recording(self):
        import json
        filename = get_settings()["recording_filename"]
        if filename is None:
            logging.warning("No recording chosen in settings")
            return

        recordings_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "cheats",
            "recordings",
        )
        path = os.path.join(recordings_dir, filename)

        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception as e:
            import traceback
            logging.error(f"failed to load recording: {e}\n{traceback.format_exc()}")
            return

        self.ticks_to_apply = [
            TickData(
                keys=list(map(Keys.from_serialized, tick.get("raw_keys", []))),
                text_input=tick.get("text_input", None),
                force_keys=True,
            )
            for tick in data
        ]
        self.playing_recording = True

    def save_recording(self, current_map: str | None = None, suffix: str = ''):
        import json
        import datetime
        if current_map is None:
            current_map = self.game.current_map

        recordings_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "cheats",
            "recordings",
        )
        os.makedirs(recordings_dir, exist_ok=True)

        savename = (
            f"{current_map}_{datetime.datetime.now().isoformat()}_{self.game.tics:05}"
        )
        if suffix:
            savename += f"_{suffix}"

        with open(os.path.join(recordings_dir, f"{savename}.json"), "w") as f:
            json.dump(self.game.current_recording, f, indent=2)

        self.screenshot_recordings.append(os.path.join(recordings_dir, savename))
        self.last_save = time.time()

    def start_recording(self):
        self.recording_enabled = True
        self.last_save = time.time()
        self._reset_recording()

    def stop_recording(self):
        self.recording_enabled = False
        self._reset_recording()

    def _reset_recording(self):
        self.game.current_recording = []

    def _save_overview_state(self):
        flagdict = {}
        for flag in self.game.match_flags.flags:
            flagdict[flag.fullname] = flag.stars

        flags: list[MapFlag] = []
        coins: list[MapObject] = []
        npcs: list[MapObject] = []
        items: list[MapObject] = []
        warps: list[MapObject] = []

        for map_name, map_attrs in self.game.maps_dict.items():
            for o in map_attrs.tiled_map.objects:
                if o.nametype == "warp":
                    warps.append(MapObject(map_name, o))

                if not o.name:
                    continue
                if o.name.startswith("coin_"):
                    coins.append(MapObject(map_name, o))
                elif o.name in flagdict:
                    flags.append(MapFlag(map_name, o, flagdict[o.name]))
                elif o.nametype == "NPC":
                    npcs.append(MapObject(map_name, o))
                elif o.nametype == "Item":
                    items.append(MapObject(map_name, o))

        flags.sort(key=lambda x: x.mapname)
        coins.sort(key=lambda x: x.mapname)
        npcs.sort(key=lambda x: x.mapname)
        items.sort(key=lambda x: x.mapname)
        warps.sort(key=lambda x: x.mapname)

        update_state(lambda s: deepcopy(State(flags=flags, coins=coins, npcs=npcs, items=items, warps=warps)))

    def _build_object_map_mapping(self):
        self.object_map_mapping = {}

        # map -> list of connected maps
        for map_name, map_attrs in self.game.maps_dict.items():
            self.map_connections[map_name] = set()
            for obj in map_attrs.tiled_map.objects + map_attrs.tiled_map.stateful_objects:
                if obj.nametype == "warp":
                    self.map_connections[map_name].add(obj.map_name)
                    self.map_warps[(map_name, obj.map_name)] = (obj.x, obj.y)
                if obj.nametype in {
                    "Item",
                    "NPC",
                    "Enemy",
                    "warp",
                }:
                    obj_key = f'{map_name}_{obj.nametype}_{obj.name}'.lower()
                    self.object_map_mapping[obj_key] = map_name
                    self.object_links.append((obj_key, obj))

    def _build_object_paths(self):
        if self.paths_built_for == self.game.current_map:
            return
        
        if self.game.current_map is None:
            self.paths_built_for = None
            self.object_paths = {}
            return

        # bfs
        print('start bfs', self.game.current_map, self.map_connections)
        q = [self.game.current_map]
        prev = {}
        while q:
            map_name = q.pop(0)
            for neighbor in self.map_connections[map_name]:
                if neighbor not in prev and neighbor != map_name:
                    prev[neighbor] = map_name
                    q.append(neighbor)
        
        print('bfs done', prev)

        for obj_key, map_name in self.object_map_mapping.items():
            path = [map_name]
            while map_name := prev.get(map_name, None):
                path.append(map_name)
            path.reverse()
            self.object_paths[obj_key] = path

        print('object paths', self.object_paths)

        self.paths_built_for = self.game.current_map

    def _dump_rust_state(self, enable_portals: bool, enable_proj: bool):
        mode = None
        player = self.game.player
        mode = search.GameMode.Platformer

        cheat_settings = get_settings()
        allowed_moves = []
        if cheat_settings["allowed_moves"].lower() not in {"", "all"}:
            moves = cheat_settings["allowed_moves"].upper().split(",")
            for move in moves:
                allowed_moves.append(getattr(search.Move, move))

        settings = search.SearchSettings(
            mode=mode,
            timeout=cheat_settings["timeout"],
            always_shift=cheat_settings["always_shift"],
            disable_shift=cheat_settings["disable_shift"],
            allowed_moves=allowed_moves,
            heuristic_weight=cheat_settings["heuristic_weight"],
            simple_geometry=cheat_settings["simple_geometry"],
            state_batch_size=cheat_settings["state_batch_size"],
        )
        zero_point = search.Pointf(0.0, 0.0)
        static_objects = [
            (
                search.Hitbox(
                    search.Rectangle(o.x1, o.x2, o.y1, o.y2),
                ),
                search.ObjectType.Wall,
                zero_point
            )
            for o in (
                self.game.objects + 
                self.game.stateful_objects
            )
            if (
                o.nametype == "Wall" or 
                (o.nametype == "Enemy" and o.name == "block_enemy" and not o.dead)
            )
        ]

        deadly_objects_type = {
            "Ouch": search.ObjectType.Ouch,
            "SpikeOuch": search.ObjectType.SpikeOuch,
            "Projectile": search.ObjectType.Projectile,
        } | ({
            "warp": search.ObjectType.Warp,
            "Portal": search.ObjectType.Portal,
            } if enable_portals else {})

        static_objects += [
            (
                search.Hitbox(
                    search.Rectangle(o.x1, o.x2, o.y1, o.y2),
                ),
                deadly_objects_type[o.nametype],
                zero_point
            )
            for o in self.game.objects + self.game.stateful_objects
            if o.nametype in deadly_objects_type
        ]

        if enable_proj:
            projs = [
                (
                    search.Hitbox(
                        search.Rectangle(o.x1, o.x2, o.y1, o.y2),
                    ),
                    deadly_objects_type[o.nametype],
                    search.Pointf(getattr(o, 'x_speed', 0), getattr(o, 'y_speed', 0))
                )
                for o in self.game.projectile_system.active_projectiles
                if o.nametype in deadly_objects_type
            ]
            static_objects += projs


        environments = [
            search.EnvModifier(
                hitbox=search.Hitbox(
                    search.Rectangle(o.x1, o.x2, o.y1, o.y2),
                ),
                name=o.modifier.name,
                jump_speed=o.modifier.jump_speed,
                walk_speed=o.modifier.walk_speed,
                gravity=o.modifier.gravity,
                jump_override=o.modifier.jump_override,
            )
            for o in self.game.physics_engine.env_tiles
        ]

        # Add generic env to fallback to.
        environments = [
            search.EnvModifier(
                hitbox=search.Hitbox(
                    search.Rectangle(0, 0, 0, 0),
                ),
                name="generic",
                jump_speed=1.0,
                walk_speed=1.0,
                gravity=1.0,
                jump_override=False,
            )
        ] + environments

        player_direction = None
        match player.direction:
            case player.DIR_N:
                player_direction = search.Direction.N
            case player.DIR_E:
                player_direction = search.Direction.E
            case player.DIR_S:
                player_direction = search.Direction.S
            case player.DIR_W:
                player_direction = search.Direction.W

        static_state = search.StaticState(
            objects=static_objects,
            environments=environments,
        )

        initial_state = search.PhysState(
            player=search.PlayerState(
                x=player.x,
                y=player.y,

                vx=player.x_speed,
                vy=player.y_speed,
                base_vx=player.base_x_speed,
                base_vy=player.base_y_speed,

                jump_override=player.jump_override,
                direction=player_direction,
                in_the_air=player.in_the_air,
                can_jump=player.can_jump,
                running=player.running,
                stamina=player.stamina,

                speed_multiplier=player.speed_multiplier,
                jump_multiplier=player.jump_multiplier,
            ),
            settings=settings.physics_settings(),
            state=static_state,
        )
        return settings, initial_state, static_state

    def mouse_press_event(self, x, y, button):
        super().mouse_press_event(x, y, button)
        
        if button != 1:
            return
        
        if self.game is None:
            return

        border_x = (self.projected_width - self.wnd.viewport_width) / 2
        border_y = (self.projected_height - self.wnd.viewport_height) / 2

        x_ratio = (x * self.wnd.pixel_ratio - border_x) / self.wnd.viewport_width
        y_ratio = (y * self.wnd.pixel_ratio - border_y) / self.wnd.viewport_height

        projected_x = x * self.wnd.pixel_ratio
        projected_y = y * self.wnd.pixel_ratio

        logging.info("mouse pressed at (%s, %s), projected: (%s, %s), border: (%s, %s)", 
                     x, y, 
                     projected_x, projected_y, 
                     border_x, border_y)

        if projected_x < border_x or projected_x > self.projected_width - border_x:
            logging.warn(
                "click is outside of projected area (X): projected(%s, %s), border(%s, %s)", 
                projected_x, projected_y, 
                border_x, border_y,
            )
            return

        if projected_y < border_y or projected_y > self.projected_height - border_y:
            logging.warn(
                "click is outside of projected area (Y): projected(%s, %s), border(%s, %s)", 
                projected_x, projected_y, 
                border_x, border_y,
            )
            return

        target_x = x_ratio * self.camera.viewport_width + self.camera.position.x
        target_y = (self.camera.viewport_height - y_ratio * self.camera.viewport_height) + self.camera.position.y

        player = self.game.player
        logging.info(
            "mouse pressed at (%s, %s), player pos: (%s, %s), target: (%s, %s), projected: (%s, %s), window: (%s, %s), viewport: (%s, %s)",
            x,
            y,
            player.x,
            player.y,
            target_x,
            target_y,
            self.projected_width,
            self.projected_height,
            self.wnd.width,
            self.wnd.height,
            self.wnd.viewport_width,
            self.wnd.viewport_height,
        )

        settings, initial_state, static_state = self._dump_rust_state(enable_portals=True, enable_proj=False)

        target_state = search.PhysState(
            player=search.PlayerState(
                x=target_x,
                y=target_y,

                vx=player.x_speed,
                vy=player.y_speed,
                base_vx=player.base_x_speed,
                base_vy=player.base_y_speed,

                jump_override=player.jump_override,
                direction=search.Direction.N,
                in_the_air=player.in_the_air,
                can_jump=player.can_jump,
                running=player.running,
                stamina=player.stamina,

                speed_multiplier=player.speed_multiplier,
                jump_multiplier=player.jump_multiplier,
            ),
            settings=settings.physics_settings(),
            state=static_state,
        )

        path = search.astar_search(
            settings=settings,
            initial_state=initial_state,
            target_state=target_state,
            static_state=static_state,
        )
        if not path:
            logging.warning("Path not found")

            tmp_dir = os.path.join("/tmp", secrets.token_urlsafe(16))
            os.makedirs(tmp_dir)
            settings_path = os.path.join(tmp_dir, "settings.json")
            initial_state_path = os.path.join(tmp_dir, "initial_state.json")
            target_state_path = os.path.join(tmp_dir, "target_state.json")
            static_state_path = os.path.join(tmp_dir, "static_state.json")

            with open(settings_path, "w") as f:
                f.write(search.serialize_settings(settings))
            with open(initial_state_path, "w") as f:
                f.write(search.serialize_state(initial_state))
            with open(target_state_path, "w") as f:
                f.write( search.serialize_state(target_state))
            with open(static_state_path, "w") as f:
                f.write(search.serialize_static_state(static_state))

            logging.warning(f"Path not found, saved to {tmp_dir}")

        else:
            self.ticks_to_apply = []
            self.playing_recording = False
            for move, shift, state in path:

                self.ticks_to_apply.append(
                    TickData(
                        force_keys=True,
                        keys=search_move_to_keys(move, shift)
                    )
                )

            print("path found", [x[:2] for x in path])

def search_move_to_keys(move, shift):
    moves = set()
    match move:
        case search.Move.W:
            moves = {Keys.W}
        case search.Move.A:
            moves = {Keys.A}
        case search.Move.D:
            moves = {Keys.D}
        case search.Move.WA:
            moves = {Keys.W, Keys.A}
        case search.Move.WD:
            moves = {Keys.W, Keys.D}
        case search.Move.S:
            moves = {Keys.S}
        case search.Move.SA:
            moves = {Keys.S, Keys.A}
        case search.Move.SD:
            moves = {Keys.S, Keys.D}
        case search.Move.NONE:
            moves = set()
        case _:
            print("unknown move", move)
            return []

    if shift:
        moves.add(Keys.LSHIFT)
    return list(moves)
