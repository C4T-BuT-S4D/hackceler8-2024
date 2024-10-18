use core::hash::Hash;
use std::hash::Hasher;

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use crate::env_modifier::EnvModifier;
use crate::player::PlayerState;
use crate::settings::SearchSettings;
use crate::{
    geometry::Pointf,
    hitbox::Hitbox,
    moves::{Action, Direction, Move},
    settings::{GameMode, PhysicsSettings},
    static_state::StaticState,
};

pub const TICK_S: f64 = 1.0 / 60.0;
pub const PLAYER_JUMP_SPEED: f64 = 5.5;
pub const PLAYER_MOVEMENT_SPEED: f64 = 2.3;
pub const GRAVITY_CONSTANT: f64 = 0.1;

#[pyclass]
#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct PhysState {
    pub player: PlayerState,
    pub was_step_up_before: bool,
    pub gravity: f64,
    settings: PhysicsSettings,
    active_modifier: usize,
}

#[pymethods]
impl PhysState {
    #[new]
    pub fn new(player: PlayerState, settings: PhysicsSettings, state: &StaticState) -> Self {
        let mut ps = PhysState {
            player,
            settings,
            gravity: GRAVITY_CONSTANT,
            // Default to generic modifier.
            active_modifier: 0,
            was_step_up_before: false,
        };

        ps.detect_env_mod(state);
        ps
    }
}

impl PhysState {
    pub fn tick(
        &mut self,
        act: Action,
        state: &StaticState,
        _search_settings: &SearchSettings,
    ) {
        self.player_tick(state, act);

        // projectiles are checked before the player's position is updated
        for proj in &state.proj {
            if proj.collides(&self.player.get_hitbox()) {
                self.player.dead = true;
                return;
            }
        }

        // Player is the only moving object we have.
        self.player.update_position();
        self.align_edges(state);

        for deadly in &state.deadly {
            if deadly.collides(&self.player.get_hitbox()) {
                self.player.dead = true;
                return;
            }
        }

        self.detect_env_mod(state);

        if self.player.in_the_air {
            self.player.vy -= self.gravity;
        }

        self.was_step_up_before = act.mov.is_up();
    }

    pub fn close_enough(&self, target_state: &PhysState, precision: f64) -> bool {
        f64::abs(self.player.x - target_state.player.x) <= precision
            && f64::abs(self.player.y - target_state.player.y) <= precision
    }
}

// Env modifiers
impl PhysState {
    fn detect_env_mod(&mut self, state: &StaticState) {
        for (i, modifier) in state.environments.iter().skip(1).enumerate() {
            if modifier.hitbox.collides(&self.player.get_hitbox()) {
                if self.active_modifier != i {
                    self.active_modifier = i;
                    self.apply_modifier(modifier);
                }
                return;
            }
        }

        self.active_modifier = 0;
        self.apply_modifier(&state.environments[0]);
    }

    fn apply_modifier(&mut self, modifier: &EnvModifier) {
        self.gravity = GRAVITY_CONSTANT * modifier.gravity;
        self.player.base_vx = PLAYER_MOVEMENT_SPEED * modifier.walk_speed;
        self.player.base_vy = PLAYER_JUMP_SPEED * modifier.jump_speed;
        self.player.jump_override = modifier.jump_override;
    }
}

// Align player edges with other objects
impl PhysState {
    fn align_edges(&mut self, state: &StaticState) {
        let (collisions_x, collisions_y) = self.get_collisions_list(state, &self.player.get_hitbox());
        if collisions_x.is_empty() && collisions_y.is_empty() {
            self.player.in_the_air = true;
            return;
        }

        for collision in collisions_x {
            self.align_x_edge(collision);
        }

        let (_, collisions_y) = self.get_collisions_list(state, &self.player.get_hitbox());
        for collision in collisions_y {
            self.align_y_edge(collision);
        }
    }

    fn align_x_edge(&mut self, collision: Collision) {
        if rround::round(collision.mpv.x, 2) as i32 == 0 {
            return;
        }
        self.player.vx = 0.0;

        if collision.mpv.x < 0.0 {
            self.player.move_by(collision.hitbox.get_leftmost_point() - self.player.get_hitbox().get_rightmost_point(), 0.0);
        } else {
            self.player.move_by(collision.hitbox.get_rightmost_point() - self.player.get_hitbox().get_leftmost_point(), 0.0);
        }
    }

    fn align_y_edge(&mut self, collision: Collision) {
        if rround::round(collision.mpv.y, 2) as i32 == 0 {
            return;
        }

        self.player.vy = 0.0;

        if collision.mpv.y > 0.0 {
            self.player.move_by(0.0, collision.hitbox.get_highest_point() - self.player.get_hitbox().get_lowest_point());
            self.player.in_the_air = false;
        } else {
            self.player.move_by(0.0, collision.hitbox.get_lowest_point() - self.player.get_hitbox().get_highest_point());
        }
    }
}

// Modify player-related state
impl PhysState {
    fn player_reset_can_jump(&mut self, state: &StaticState) {
        if self.settings.mode == GameMode::Scroller {
            self.player.can_jump = true;
            return;
        }

        self.player.can_jump = self.player.prev_y == self.player.y;
        // self.player.move_by(0.0, -1.0);
        // self.player.can_jump = self.player_can_jump(state, &self.player.get_hitbox());
        // self.player.move_by(0.0, 1.0);
    }

    fn player_tick(&mut self, state: &StaticState, act: Action) {
        self.player_update_movement(state, act);
        self.player_update_stamina(act.shift);
    }

    fn player_update_stamina(&mut self, shift_pressed: bool) {
        if self.player.running || shift_pressed {
            return;
        }
        self.player.stamina = (self.player.stamina + 0.5).min(100.0);
    }

    fn player_update_movement(
        &mut self,
        state: &StaticState,
        act: Action,
    ) {
        self.player.vx = 0.0;
        if self.settings.mode == GameMode::Scroller {
            self.player.vy = 0.0;
        }

        self.player.running = false;

        let sprinting = act.shift && self.player.stamina > 0.0;

        if act.mov.is_right() {
            self.player_change_direction(state, Direction::E, sprinting);
        }

        if act.mov.is_left() {
            self.player_change_direction(state, Direction::W, sprinting);
        }

        if !self.was_step_up_before && act.mov.is_up() {
            self.player_change_direction(state, Direction::N, sprinting);
        }

        if self.settings.mode == GameMode::Scroller && act.mov.is_down() {
            self.player_change_direction(state, Direction::S, sprinting);
        }
    }

    fn player_change_direction(&mut self, state: &StaticState, direction: Direction, sprinting: bool) {
        let mut speed_multiplier = 1.0;
        if (direction == Direction::E || direction == Direction::W) && sprinting {
            speed_multiplier = self.player.speed_multiplier;
            self.player.running = true;
            self.player.stamina = (self.player.stamina - 0.5).max(0.0);
        }

        match direction {
            Direction::E => {
                self.player.vx = self.player.base_vx * speed_multiplier;
            }
            Direction::W => {
                self.player.vx = -self.player.base_vx * speed_multiplier;
            }
            Direction::N => {
                if self.settings.mode == GameMode::Scroller {
                    self.player.vy = self.player.base_vx * speed_multiplier;
                    return;
                }

                self.player_reset_can_jump(state);
                if !self.player.can_jump && !self.player.jump_override {
                    return;
                }
                self.player.vy = self.player.base_vy * speed_multiplier;
                self.player.in_the_air = true;
            }
            Direction::S => {
                if self.settings.mode == GameMode::Scroller {
                    self.player.vy = -self.player.base_vx * speed_multiplier;
                }
            }
        }
    }
}

impl PhysState {
    fn get_collisions_list(&self, state: &StaticState, player: &Hitbox) -> (Vec<Collision>, Vec<Collision>) {
        let mut collisions_x = Vec::new();
        let mut collisions_y = Vec::new();

        for (o1, _) in &state.objects {
            if o1.collides(player) {
                let mpv = o1.get_mpv(player);
                if rround::round(mpv.x, 2) as i32 == 0 {
                    collisions_y.push(Collision {
                        hitbox: *o1,
                        mpv,
                    });
                } else if rround::round(mpv.y, 2) as i32 == 0 {
                    collisions_x.push(Collision {
                        hitbox: *o1,
                        mpv,
                    });
                }
            }
        }

        (collisions_x, collisions_y)
    }

    fn player_can_jump(&self, state: &StaticState, player: &Hitbox) -> bool {
        for (o1, _) in &state.objects {
            if o1.collides(player) {
                let mpv = o1.get_mpv(player);
                if rround::round(mpv.x, 2) as i32 == 0 && mpv.y > 0.0 {
                    return true;
                }
            }
        }
        false
    }
}

struct Collision {
    hitbox: Hitbox,
    mpv: Pointf,
}

// Implementations for simple geometry
impl PhysState {
    fn simple_player_x(&self) -> f64 {
        (self.player.x * 10.0).round() / 10.0
    }

    fn simple_player_y(&self) -> f64 {
        (self.player.y * 10.0).round() / 10.0
    }

    fn simple_player_vy(&self) -> f64 {
        (self.player.vy * 1.0).round() / 1.0
    }
}

impl PartialEq for PhysState {
    fn eq(&self, other: &Self) -> bool {
        if self.settings.simple_geometry {
            if self.simple_player_x() != other.simple_player_x() {
                return false;
            }
            if self.simple_player_y() != other.simple_player_y() {
                return false;
            }
        } else {
            if self.player.x != other.player.x {
                return false;
            }
            if self.player.y != other.player.y {
                return false;
            }
        }

        if self.settings.mode == GameMode::Platformer {
            if self.settings.simple_geometry {
                if self.simple_player_vy() != other.simple_player_vy() {
                    return false;
                }
            } else if self.player.vy != other.player.vy {
                return false;
            }
        }

        // if self.player.stamina != other.player.stamina {
        //     return false;
        // }

        if self.was_step_up_before != other.was_step_up_before {
            return false;
        }

        true
    }
}

impl Eq for PhysState {}

impl Hash for PhysState {
    fn hash<H: Hasher>(&self, state: &mut H) {
        if self.settings.simple_geometry {
            state.write(&self.simple_player_x().to_le_bytes());
            state.write(&self.simple_player_y().to_le_bytes());
        } else {
            state.write(&self.player.x.to_le_bytes());
            state.write(&self.player.y.to_le_bytes());
        }
        if self.settings.mode == GameMode::Platformer {
            if self.settings.simple_geometry {
                state.write(&self.simple_player_vy().to_le_bytes());
            } else {
                state.write(&self.player.vy.to_le_bytes());
            }
        }

        // state.write(&self.player.stamina.to_le_bytes());
        state.write(&[self.was_step_up_before as u8]);
    }
}

#[pyfunction]
pub fn get_transition(
    settings: SearchSettings,
    static_state: StaticState,
    mut state: PhysState,
    next_move: Move,
    shift_pressed: bool,
) -> PlayerState {
    let act = Action { mov: next_move, shift: shift_pressed };
    state.tick(act, &static_state, &settings);
    state.player
}
