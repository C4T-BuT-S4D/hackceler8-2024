use pyo3::prelude::*;

use crate::geometry::Pointf;

#[pyclass]
#[derive(Clone, Debug)]
pub struct Polygon {
    pub outline: Vec<Pointf>,

    pub vectors: Vec<Pointf>,
    angles: Vec<f64>,

    pub center: Pointf,
    pub highest_point: f64,
    pub lowest_point: f64,
    pub rightmost_point: f64,
    pub leftmost_point: f64,
}

#[pymethods]
impl Polygon {
    #[new]
    pub fn new(outline: Vec<Pointf>) -> Self {
        let mut polygon = Polygon {
            outline,
            vectors: vec![],
            angles: vec![],

            center: Pointf { x: 0.0, y: 0.0 },
            highest_point: 0.0,
            lowest_point: 0.0,
            rightmost_point: 0.0,
            leftmost_point: 0.0,
        };
        polygon.init();
        polygon
    }
}

impl Polygon {
    fn init(&mut self) {
        self.get_vectors();
        self.get_angles();
        self.is_convex();
        self.cache_points();
    }

    fn get_vectors(&mut self) {
        self.vectors.clear();
        for i in 0..self.outline.len() {
            self.vectors
                .push(self.outline[(i + 1) % self.outline.len()] - self.outline[i]);
        }
    }

    fn get_angles(&mut self) {
        self.angles.clear();
        for i in 0..self.vectors.len() {
            self.angles
                .push(self.vectors[i].angle(&self.vectors[(i + 1) % self.vectors.len()]));
        }
    }

    fn is_convex(&self) {
        for &angle in &self.angles {
            assert!(angle < 180.0);
        }
    }

    fn cache_points(&mut self) {
        self.lowest_point = f64::INFINITY;
        self.highest_point = f64::NEG_INFINITY;
        self.leftmost_point = f64::INFINITY;
        self.rightmost_point = f64::NEG_INFINITY;

        let mut center_x = 0.0;
        let mut center_y = 0.0;

        for point in &self.outline {
            self.lowest_point = f64::min(self.lowest_point, point.y);
            self.highest_point = f64::max(self.highest_point, point.y);
            self.leftmost_point = f64::min(self.leftmost_point, point.x);
            self.rightmost_point = f64::max(self.rightmost_point, point.x);

            center_x += point.x;
            center_y += point.y;
        }
        self.center = Pointf {
            x: center_x / self.outline.len() as f64,
            y: center_y / self.outline.len() as f64,
        };
    }
}

impl PartialEq for Polygon {
    fn eq(&self, other: &Self) -> bool {
        self.outline.len() == other.outline.len()
            && self
                .outline
                .iter()
                .zip(other.outline.iter())
                .all(|(a, b)| a.x == b.x && a.y == b.y)
    }
}
