use pyo3::pyclass;

#[pyclass(eq)]
#[derive(PartialEq, Eq, Debug, Clone, Copy)]
pub enum ObjectType {
    Wall,
    Spike,
    Portal,
}
