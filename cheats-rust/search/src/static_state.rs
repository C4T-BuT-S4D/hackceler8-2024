use pyo3::{pyclass, pymethods};
use serde::{Deserialize, Serialize};

use crate::{env_modifier::EnvModifier, geometry::Pointf, hitbox::Hitbox, objects::ObjectType};

#[pyclass]
#[derive(Clone, Serialize, Deserialize)]
pub struct StaticState {
    pub objects: Vec<(Hitbox, ObjectType)>,
    pub deadly: Vec<Hitbox>,
    pub proj: Vec<Hitbox>,
    pub proj_v: Vec<Pointf>,
    pub environments: Vec<EnvModifier>,
}

#[pymethods]
impl StaticState {
    #[new]
    pub fn new(objects: Vec<(Hitbox, ObjectType, Pointf)>, environments: Vec<EnvModifier>) -> Self {
        let mut deadly = Vec::new();
        let mut proj = Vec::new();
        let mut proj_v = Vec::new();
        let mut other_objects = Vec::new();
        for (hitbox, t, v) in objects {
            match t {
                ObjectType::Ouch | ObjectType::SpikeOuch | ObjectType::Portal | ObjectType::Warp  => {
                    deadly.push(hitbox);
                }
                ObjectType::Projectile => {
                    proj.push(hitbox);
                    proj_v.push(v);
                }
                _ => {
                    other_objects.push((hitbox, t));
                }
            }
        }
        StaticState {
            objects: other_objects,
            deadly,
            proj,
            proj_v,
            environments,
        }
    }
    pub fn step_deadly(&self) -> Self {
        let mut copy = self.clone();
        for (hitbox, vel) in copy.proj.iter_mut().zip(copy.proj_v.iter()) {
            hitbox.update(hitbox.rect.offset(vel.x, vel.y));
        }
        copy
    }
}
