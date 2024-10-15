use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use crate::geometry::{Pointf, Rectangle};
use crate::hitbox::Hitbox;
use crate::moves::Direction;

#[pyclass]
#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct PlayerState {
    #[pyo3(get, set)]
    pub x: f64,
    #[pyo3(get, set)]
    pub y: f64,

    #[pyo3(get, set)]
    pub vx: f64,
    #[pyo3(get, set)]
    pub vy: f64,

    #[pyo3(get, set)]
    pub base_vx: f64,
    #[pyo3(get, set)]
    pub base_vy: f64,

    #[pyo3(get, set)]
    pub jump_override: bool,
    #[pyo3(get, set)]
    pub direction: Direction,
    #[pyo3(get, set)]
    pub in_the_air: bool,
    #[pyo3(get, set)]
    pub can_jump: bool,
    #[pyo3(get, set)]
    pub running: bool,
    #[pyo3(get, set)]
    pub dead: bool,

    #[pyo3(get, set)]
    pub speed_multiplier: f64,
    #[pyo3(get, set)]
    pub jump_multiplier: f64,

    #[pyo3(get, set)]
    pub stamina: f64,

    #[pyo3(get, set)]
    pub rect: Rectangle,
}

#[pymethods]
impl PlayerState {
    #[new]
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        x: f64,
        y: f64,
        
        vx: f64,
        vy: f64,
        
        base_vx: f64,
        base_vy: f64,

        jump_override: bool,
        direction: Direction,
        in_the_air: bool,
        can_jump: bool,
        running: bool,
        stamina: f64,

        speed_multiplier: f64,
        jump_multiplier: f64,
    ) -> Self {
        PlayerState {
            x,
            y,
            vx,
            vy,
            base_vx,
            base_vy,
            jump_override,
            direction,
            in_the_air,
            can_jump,
            running,
            dead: false,
            stamina,
            speed_multiplier,
            jump_multiplier,
            rect: Rectangle::new(x - 24.0, x + 24.0, y - 26.0, y + 20.0),
        }
    }
}

impl PlayerState {
    pub fn center(&self) -> Pointf {
        Pointf {
            x: self.x,
            y: self.y,
        }
    }

    pub fn move_by(&mut self, dx: f64, dy: f64) {
        self.x = rround::round(self.x + dx, 2);
        self.y = rround::round(self.y + dy, 2);
        self.rect = self.rect.offset(dx, dy).rounded();
    }

    pub fn get_hitbox(&self) -> Hitbox {
        Hitbox::new(self.rect)
    }

    pub fn update_position(&mut self) {
        if self.vx != 0.0 || self.vy != 0.0 {
            self.move_by(self.vx, self.vy);
        }
    }
}
