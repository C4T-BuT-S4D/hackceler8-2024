use pyo3::{pyclass, pymethods};
use serde::{Deserialize, Serialize};

use crate::{env_modifier::EnvModifier, hitbox::Hitbox, objects::ObjectType};

#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct StaticState {
    pub objects: Vec<(Hitbox, ObjectType)>,
    pub deadly: Vec<Hitbox>,
    pub environments: Vec<EnvModifier>,
}

#[pymethods]
impl StaticState {
    #[new]
    pub fn new(objects: Vec<(Hitbox, ObjectType)>, environments: Vec<EnvModifier>) -> Self {
        let mut deadly = Vec::new();
        let mut other_objects = Vec::new();
        for (hitbox, t) in objects {
            match t {
                ObjectType::Ouch | ObjectType::SpikeOuch | ObjectType::Portal | ObjectType::Warp => {
                    deadly.push(hitbox);
                }
                _ => {
                    other_objects.push((hitbox, t));
                }
            }
        }
        StaticState {
            objects: other_objects,
            deadly,
            environments,
        }
    }
}
