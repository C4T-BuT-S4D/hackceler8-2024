#![feature(let_chains)]

use encoding::{
    deserialize_settings, deserialize_state, deserialize_static_state, serialize_settings,
    serialize_state, serialize_static_state,
};
use pyo3::prelude::*;

use dodge::dodge_search;
use env_modifier::EnvModifier;
use geometry::{Pointf, Rectangle};
use hitbox::Hitbox;
use moves::{Direction, Move};
use objects::ObjectType;
use physics::{get_transition, PhysState};
use player::PlayerState;
use rround::init_thresholds;
use settings::{GameMode, PhysicsSettings, SearchSettings};

use crate::astar::astar_search;
use crate::static_state::StaticState;

pub mod astar;
pub mod dodge;
pub mod encoding;
pub mod env_modifier;
pub mod geometry;
pub mod hitbox;
pub mod moves;
pub mod objects;
pub mod physics;
pub mod player;
pub mod polygon;
pub mod settings;
pub mod static_state;

#[pymodule]
fn search(m: &Bound<'_, PyModule>) -> PyResult<()> {
    init_thresholds();
    m.add_class::<Pointf>()?;
    m.add_class::<Hitbox>()?;
    m.add_class::<PlayerState>()?;
    m.add_class::<StaticState>()?;
    m.add_class::<PhysState>()?;
    m.add_class::<Move>()?;
    m.add_class::<SearchSettings>()?;
    m.add_class::<PhysicsSettings>()?;
    m.add_class::<GameMode>()?;
    m.add_class::<ObjectType>()?;
    m.add_class::<Direction>()?;
    m.add_class::<EnvModifier>()?;
    m.add_class::<Rectangle>()?;
    m.add_function(wrap_pyfunction!(astar_search, m)?)?;
    m.add_function(wrap_pyfunction!(get_transition, m)?)?;

    m.add_function(wrap_pyfunction!(dodge_search, m)?)?;

    m.add_function(wrap_pyfunction!(serialize_state, m)?)?;
    m.add_function(wrap_pyfunction!(deserialize_state, m)?)?;
    m.add_function(wrap_pyfunction!(serialize_settings, m)?)?;
    m.add_function(wrap_pyfunction!(deserialize_settings, m)?)?;
    m.add_function(wrap_pyfunction!(serialize_static_state, m)?)?;
    m.add_function(wrap_pyfunction!(deserialize_static_state, m)?)?;

    Ok(())
}
