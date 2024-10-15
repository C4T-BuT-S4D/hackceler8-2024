use pyo3::pyclass;
use serde::{Deserialize, Serialize};

#[pyclass(eq)]
#[derive(PartialEq, Eq, Debug, Clone, Copy, Serialize, Deserialize)]
pub enum ObjectType {
    Wall,
    Spike,
    Portal,
}
