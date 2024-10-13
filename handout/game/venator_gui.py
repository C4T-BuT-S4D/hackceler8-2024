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
from cheats.lib.tick_data import TickData

SCREEN_TITLE = "Hackceler8-24"

class Hackceler8(gfx.Window):
    window_size = (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
    title = SCREEN_TITLE

    def __init__(self, net=None, **kwargs):
        super().__init__(**kwargs)
        self.heart = gfx.GuiImage.load(self, "resources/objects/heart.png")
        self.star = gfx.GuiImage.load(self, "resources/objects/star.png")
        self.stamina = gfx.GuiImage.load(self, "resources/objects/stamina.png")

        self.boss_bg = None

        self.net = net
        self.game: Optional[Venator] = None

        self.main_layer = gfx.CombinedLayer()

        self.camera = gfx.Camera(self.window_size[0], self.window_size[1], constants.DEFAULT_SCALE)
        self.gui_camera = gfx.Camera(self.window_size[0], self.window_size[1], constants.DEFAULT_SCALE)  # For screen space stationary objects.

        # Load the game immediately in standalone mode.
        if constants.STANDALONE:
            self.loading_screen_timer = 0

        # cheats settings

        self.render_gui = True # needed to skip rendering the GUI for screenshots

        self.ticks_to_apply: list[TickData] = []

        self.draws: list[float] = []

        self.single_tick_mode = False

    def setup_game(self):
        self.game = Venator(self.net, is_server=False)

    # Do not resize anything. This way the regular camera will scale, and gui is drawn separately anyway.
    def on_resize(self, width, height):
        pass

    def _center_camera_to_player(self):
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
        if self.game is None:
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

        self._draw_debug_ui()

        self.gui_camera.update()
        self.gui_camera.use()

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
            self.game.screen_fader.draw(scale=constants.DEFAULT_SCALE)

    def tick(self, _delta_time: float):
        if self.game is None:
            if self.loading_screen_timer > 0:
                self.loading_screen_timer -= 1
                return
            self.setup_game()

        if not self.single_tick_mode:
            self.tick_once()

    def on_key_press(self, symbol: int, modifiers: int):
        k = Keys.from_ui(symbol)

        if k == Keys.N and modifiers.ctrl:
            self.camera.set_scale(self.camera.scale + 1)
            return
        
        if k == Keys.M and modifiers.ctrl:
            self.camera.set_scale(self.camera.scale - 1)
            return
        
        if k == Keys.EQUAL:
            self.single_tick_mode = not self.single_tick_mode
            logging.info(f"single tick mode: {self.single_tick_mode}")
            return

        if k == Keys.BACKSPACE:
            self.tick_once()
            return
        
        if symbol == self.wnd.keys.F2:
            self.full_screenshot()
            return
        
        if symbol == self.wnd.keys.F3:
            self.prerender_maps()
            return

        if k:
            self.game.raw_pressed_keys.add(k)

    def on_key_release(self, symbol: int, _modifiers: int):
        if self.game is None:
            return
        k = Keys.from_ui(symbol)
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
        keys_to_restore = None
        if self.ticks_to_apply:
            tick_to_apply = self.ticks_to_apply.pop(0)
            keys_to_restore = self.game.raw_pressed_keys.copy()

            if tick_to_apply.force_keys:
                self.game.raw_pressed_keys = set(getattr(Keys, k) for k in tick_to_apply.keys)
            else:
                self.game.raw_pressed_keys |= set(getattr(Keys, k) for k in tick_to_apply.keys)

        self.game.tick()
        self._update_boss_bg()
        self._center_camera_to_player()

        if keys_to_restore:
            self.game.raw_pressed_keys = keys_to_restore

    def _record_draw(self):
        now = time.time()
        self.draws.append(now)
        while self.draws and now - self.draws[0] > 3:
            self.draws.pop(0)

    def _draw_debug_ui(self):
        objs = []
        for o in (
            self.game.objects +
            self.game.stateful_objects +
            self.game.projectile_system.weapons +
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
                case _:
                    logging.warning(f"skipped object {o.nametype}")

            if color:
                objs.append(gfx.lrtb_rectangle_outline(
                    o.x1,
                    o.x2,
                    o.y2,
                    o.y1,
                    color,
                    border=3,
                ))

                if (modifier := getattr(o, "modifier", None)) and modifier.min_distance > 0:
                    dist = modifier.min_distance
                    objs.append(gfx.lrtb_rectangle_outline(
                        o.x1 - dist,
                        o.x2 + dist,
                        o.y2 + dist,
                        o.y1 - dist,
                        (255, 255, 0, 255),
                    ))

                if o.nametype not in {"Wall"}:
                    text = f"{o.nametype}"
                    if name := getattr(o, "name", None):
                        text += f" | {name}"
                    if health := getattr(o, "health", None):
                        text += f" | {health:.02f}"

                    x = (o.x1 - self.camera.position.x) / self.camera.scale
                    y = (self.camera.position.y - o.y2) / self.camera.scale -15
                    if x >= 0 and y <= 0 and x <= self.camera.viewport_width and y >= -self.camera.viewport_height:
                        gfx.draw_txt(f"debug_{o.nametype}_{o.x1}_{o.y1}", gfx.FONT_PIXEL[8], text,
                                 x, y, color=color)

                # if cheats_settings["draw_lines"]:
                #     if o.nametype == "Item":
                #         line_color = getattr(
                #             arcade.color, (o.color or "").upper(), None
                #         )
                #         if line_color is None:
                #             logging.debug(
                #                 f"failed to get line color for item of color {o.color}, will use the default color"
                #             )
                #             line_color = color

                #         arcade.draw_line(
                #             start_x=self.game.player.x,
                #             start_y=self.game.player.y,
                #             end_x=abs(rect.x1() + rect.x2()) / 2,
                #             end_y=abs(rect.y1() + rect.y2()) / 2,
                #             color=line_color,
                #             line_width=2,
                #         )

                #     if o.nametype == "Portal":
                #         arcade.draw_line(
                #             start_x=o.x,
                #             start_y=o.y,
                #             end_x=o.dest.x,
                #             end_y=o.dest.y,
                #             color=arcade.color.PURPLE,
                #             line_width=2,
                #         )
                    # render lines to something else as well
        self.main_layer.add_many(objs)
        self.main_layer.draw(); self.main_layer.clear()

    def full_screenshot(self, dir="screenshots", format="jpeg"):
        w, h = (
            self.game.tiled_map.map_size_pixels.width,
            self.game.tiled_map.map_size_pixels.height,
        )

        original_camera = self.camera
        original_fbo = self.ctx.fbo

        # create a custom framebuffer with the same size as the map to keep the aspect ratio and quality
        fbo = self.ctx.framebuffer(
            color_attachments=[self.ctx.texture(size=(w, h), components=4)],
        )
        fbo.use()
        self.ctx.fbo = fbo

        # camera viewport needs to be set to the full size for the whole map to be visible
        self.camera = gfx.Camera(w, h)

        # simulate a fake frame, no tick should happen
        self.render_gui = False
        self.render(0, 0)
        self.render_gui = True

        from PIL import Image
        image = Image.frombytes(
            "RGB",
            (
                fbo.viewport[2] - fbo.viewport[0],
                fbo.viewport[3] - fbo.viewport[1],
            ),
            fbo.read(viewport=fbo.viewport, alignment=1),
        )
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

        path = os.path.join(dir, f"{self.game.current_map}.{format}")
        if not os.path.exists(dir):
            os.makedirs(dir)
        image.save(path, format)
        logging.info(f"Saved screenshot of map \"{self.game.current_map}\" to \"{path}\"")

        self.camera = original_camera
        self.ctx.fbo = original_fbo

    def prerender_maps(self):
        for map in self.game.maps_dict:
            self.game.load_map(map)
            self.full_screenshot(format="png")
        self.game.load_map("base")
