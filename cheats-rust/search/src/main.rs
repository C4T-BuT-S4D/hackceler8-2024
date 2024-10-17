use std::{env::args, path::PathBuf};

use rround::init_thresholds;
use search::{
    astar::astar_search,
    encoding::{deserialize_settings, deserialize_state, deserialize_static_state},
};

fn main() {
    init_thresholds();
    let base_dir = PathBuf::from(args().nth(1).unwrap());
    let settings_path = base_dir.join("settings.json");
    let initial_state_path = base_dir.join("initial_state.json");
    let target_state_path = base_dir.join("target_state.json");
    let static_state_path = base_dir.join("static_state.json");

    let settings_str = std::fs::read_to_string(settings_path).unwrap();
    let initial_state_str = std::fs::read_to_string(initial_state_path).unwrap();
    let target_state_str = std::fs::read_to_string(target_state_path).unwrap();
    let static_state_str = std::fs::read_to_string(static_state_path).unwrap();

    let mut settings = deserialize_settings(&settings_str);
    let initial_state = deserialize_state(&initial_state_str);
    let target_state = deserialize_state(&target_state_str);
    let static_state = deserialize_static_state(&static_state_str);

    //settings.timeout = 10000;
    settings.timeout = 5;
    settings.state_batch_size = 16384;
    settings.always_shift = true;
    settings.simple_geometry = true;

    let path = astar_search(settings, initial_state, target_state, static_state);
    println!("{:?}", path.unwrap_or_default().len());
}
