use crate::{physics::PhysState, settings::SearchSettings, static_state::StaticState};
use pyo3::prelude::*;

#[pyfunction]
pub fn serialize_state(state: &PhysState) -> String {
    serde_json::to_string(state).expect("Failed to serialize state")
}

#[pyfunction]
pub fn deserialize_state(state: &str) -> PhysState {
    serde_json::from_str(state).expect("Failed to deserialize state")
}

#[pyfunction]
pub fn serialize_settings(settings: &SearchSettings) -> String {
    serde_json::to_string(settings).expect("Failed to serialize settings")
}

#[pyfunction]
pub fn deserialize_settings(settings: &str) -> SearchSettings {
    serde_json::from_str(settings).expect("Failed to deserialize settings")
}

#[pyfunction]
pub fn serialize_static_state(static_state: &StaticState) -> String {
    serde_json::to_string(static_state).expect("Failed to serialize static state")
}

#[pyfunction]
pub fn deserialize_static_state(static_state: &str) -> StaticState {
    serde_json::from_str(static_state).expect("Failed to deserialize static state")
}
