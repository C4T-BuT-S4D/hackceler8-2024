use pyo3::{pyclass, pymethods};
use serde::{Deserialize, Serialize};

use crate::hitbox::Hitbox;

#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnvModifier {
    pub hitbox: Hitbox,
    pub name: String,
    pub jump_speed: f64,
    pub walk_speed: f64,
    pub gravity: f64,
    pub jump_override: bool,
}

#[pymethods]
impl EnvModifier {
    #[new]
    pub fn new(
        hitbox: Hitbox,
        name: String,
        jump_speed: f64,
        walk_speed: f64,
        gravity: f64,
        jump_override: bool,
    ) -> Self {
        EnvModifier {
            hitbox,
            name,
            jump_speed,
            walk_speed,
            gravity,
            jump_override,
        }
    }
}