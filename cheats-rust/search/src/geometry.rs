use std::{
    f64::consts::PI,
    ops::{Div, Mul, Neg, Sub},
};
use std::hash::{Hash, Hasher};

use pyo3::{pyclass, pymethods};
use serde::{Deserialize, Serialize};

#[derive(Copy, Clone, Debug)]
#[pyclass]
pub struct Pointf {
    pub x: f64,
    pub y: f64,
}

#[pymethods]
impl Pointf {
    #[new]
    pub fn new(x: f64, y: f64) -> Self {
        Pointf { x, y }
    }
}

impl Pointf {
    pub fn unit_vector(&self) -> Pointf {
        *self / self.len()
    }

    pub fn angle(&self, other: &Pointf) -> f64 {
        let dot = self.unit_vector() * other.unit_vector();
        180.0 - f64::acos(f64::min(f64::max(dot, -1.0), 1.0)) * 180.0 / PI
    }

    pub fn len(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    pub fn manhattan_len(&self) -> f64 {
        self.x.abs() + self.y.abs()
    }

    pub fn ortho(&self) -> Pointf {
        Pointf {
            x: -self.y,
            y: self.x,
        }
    }
}

impl Sub for Pointf {
    type Output = Pointf;

    fn sub(self, other: Pointf) -> Pointf {
        Pointf {
            x: self.x - other.x,
            y: self.y - other.y,
        }
    }
}

impl Neg for Pointf {
    type Output = Pointf;

    fn neg(self) -> Pointf {
        Pointf {
            x: -self.x,
            y: -self.y,
        }
    }
}

impl Mul<f64> for Pointf {
    type Output = Pointf;

    fn mul(self, rhs: f64) -> Pointf {
        Pointf {
            x: self.x * rhs,
            y: self.y * rhs,
        }
    }
}

impl Mul<Pointf> for Pointf {
    type Output = f64;

    fn mul(self, rhs: Pointf) -> f64 {
        self.x * rhs.x + self.y * rhs.y
    }
}

impl Div<f64> for Pointf {
    type Output = Pointf;

    fn div(self, rhs: f64) -> Pointf {
        Pointf {
            x: self.x / rhs,
            y: self.y / rhs,
        }
    }
}

#[pyclass]
#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
pub struct Rectangle {
    pub x1: f64,
    pub x2: f64,
    pub y1: f64,
    pub y2: f64,
}

#[pymethods]
impl Rectangle {
    #[new]
    pub fn new(x1: f64, x2: f64, y1: f64, y2: f64) -> Self {
        Rectangle {
            x1: rround::round(x1, 2),
            x2: rround::round(x2, 2),
            y1: rround::round(y1, 2),
            y2: rround::round(y2, 2),
        }
    }

    pub fn collides(&self, other: &Rectangle) -> bool {
        self.x1 <= other.x2
            && self.x2 >= other.x1
            && self.y1 <= other.y2
            && self.y2 >= other.y1
    }

    pub fn get_mpv(&self, other: &Rectangle) -> Pointf {
        let pvs = vec![
            Pointf { x: self.x2 - other.x1, y: 0.0 },
            Pointf { x: self.x1 - other.x2, y: 0.0 },
            Pointf { x: 0.0, y: self.y2 - other.y1 },
            Pointf { x: 0.0, y: self.y1 - other.y2 },
        ];
        pvs
            .into_iter()
            .min_by(|a, b| a.manhattan_len().partial_cmp(&b.manhattan_len()).unwrap())
            .unwrap()
    }

    pub fn has_common_edge(&self, other: &Rectangle) -> bool {
        if self.x1 == other.x1 && self.x2 == other.x2 {
            return self.y1 == other.y2 || self.y2 == other.y1;
        }
        if self.y1 == other.y1 && self.y2 == other.y2 {
            return self.x1 == other.x2 || self.x2 == other.x1;
        }
        false
    }

    pub fn expand(&self, amount: f64) -> Rectangle {
        Rectangle {
            x1: self.x1 - amount,
            x2: self.x2 + amount,
            y1: self.y1 - amount,
            y2: self.y2 + amount,
        }
    }

    pub fn offset(&self, dx: f64, dy: f64) -> Rectangle {
        Rectangle {
            x1: self.x1 + dx,
            x2: self.x2 + dx,
            y1: self.y1 + dy,
            y2: self.y2 + dy,
        }
    }
}

impl Rectangle {
    pub fn rounded(self) -> Rectangle {
        Rectangle {
            x1: rround::round(self.x1, 2),
            x2: rround::round(self.x2, 2),
            y1: rround::round(self.y1, 2),
            y2: rround::round(self.y2, 2),
        }
    }
}

impl Hash for Rectangle {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.x1.to_le_bytes().hash(state);
        self.x2.to_le_bytes().hash(state);
        self.y1.to_le_bytes().hash(state);
        self.y2.to_le_bytes().hash(state);
    }
}

impl PartialEq for Rectangle {
    fn eq(&self, other: &Self) -> bool {
        self.x1 == other.x1 && self.x2 == other.x2 && self.y1 == other.y1 && self.y2 == other.y2
    }
}

impl Eq for Rectangle {}