use core::hash::Hash;
use std::hash::Hasher;

use pyo3::{pyclass, pymethods};

use crate::geometry::{Pointf, Rectangle};

#[pyclass]
#[derive(Clone, Copy, Debug)]
pub struct Hitbox {
    pub rect: Rectangle,
}

impl PartialEq for Hitbox {
    fn eq(&self, other: &Self) -> bool {
        self.rect == other.rect
    }
}

impl Hash for Hitbox {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.rect.hash(state);
    }
}

#[pymethods]
impl Hitbox {
    #[new]
    pub fn new(rect: Rectangle) -> Self {
        Hitbox { rect }
    }

    pub fn update(&mut self, rect: Rectangle) {
        self.rect = rect;
    }

    pub fn collides(&self, other: &Hitbox) -> bool {
        self.rect.collides(&other.rect)
    } 

    pub fn get_mpv(&self, other: &Hitbox) -> Pointf {
        self.rect.get_mpv(&other.rect)
    }

    pub fn get_leftmost_point(&self) -> f64 {
        self.rect.x1
    }

    pub fn get_rightmost_point(&self) -> f64 {
        self.rect.x2
    }

    pub fn get_highest_point(&self) -> f64 {
        self.rect.y2
    }

    pub fn get_lowest_point(&self) -> f64 {
        self.rect.y1
    }
}

impl Hitbox {
    pub fn get_rect(&self) -> Rectangle {
        self.rect.clone()
    }
}
