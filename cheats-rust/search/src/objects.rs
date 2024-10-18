use pyo3::pyclass;
use serde::{Deserialize, Serialize};

use crate::geometry::Pointf;

#[pyclass(eq)]
#[derive(PartialEq, Debug, Clone, Copy, Serialize, Deserialize)]
pub enum ObjectType {
    Wall(),
    Ouch(),
    SpikeOuch(),
    Portal(),
    Warp(),
    Projectile(Pointf),
    ConstantDamage(f64),
}
