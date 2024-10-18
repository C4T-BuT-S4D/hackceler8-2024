use hashbrown::HashSet;
use pyo3::prelude::*;
use rayon::prelude::*;

use crate::{
    astar::{apply_transition, transitions},
    moves::{Action, Move},
    physics::PhysState,
    settings::SearchSettings,
    static_state::StaticState,
};

const MAXDEPTH: usize = 25usize;

struct Context<'a> {
    seen: &'a mut [HashSet<PhysState>],
    settings: &'a SearchSettings,
    static_states: &'a [StaticState],
    acts: &'a [Action],
}

impl<'a> Context<'a> {
    fn dfs(&mut self, depth: usize, state: &PhysState) -> bool {
        if depth == MAXDEPTH {
            return true;
        }
        if !self.seen[depth].insert(*state) {
            return false;
        }
        for (_, to) in transitions(
            self.settings,
            &state,
            &self.static_states[depth + 1],
            &self.acts,
        ) {
            if self.dfs(depth + 1, &to) {
                return true;
            }
        }
        false
    }
}

fn is_fatal(
    acts: &[Action],
    settings: &SearchSettings,
    initial_state: PhysState,
    static_states: &[StaticState],
) -> bool {
    let mut vec = vec![HashSet::<PhysState>::new(); MAXDEPTH];
    let mut ctx = Context {
        seen: &mut vec,
        settings,
        static_states,
        acts: acts,
    };
    !ctx.dfs(0, &initial_state)
}

#[pyfunction]
pub fn dodge_search(
    settings: SearchSettings,
    initial_state: PhysState,
    static_state: StaticState,
    cur_move: Move,
    shift_pressed: bool,
) -> (Move, bool) {
    let mut static_states = vec![static_state.step_deadly()];
    for _ in 0..MAXDEPTH {
        static_states.push(static_states.last().unwrap().step_deadly())
    }
    let acts = Action::all_gm(settings.mode);
    let cur_act = Action {
        mov: cur_move,
        shift: shift_pressed,
    };
    let next = apply_transition(&settings, initial_state, &static_states[0], cur_act);
    if !next.player.dead && !is_fatal(&acts, &settings, next, &static_states) {
        return (cur_move, shift_pressed);
    }
    let mut valid: Vec<_> = acts
        .par_iter()
        .filter(|&&act| {
            if act == cur_act {
                return false;
            }
            let next = apply_transition(&settings, initial_state, &static_states[0], act);
            return !next.player.dead && !is_fatal(&acts, &settings, next, &static_states);
        })
        .collect();
    valid.sort_by_key(|act| act.mov.is_up());
    return valid
        .first()
        .map(|opt| (opt.mov, opt.shift))
        .unwrap_or((cur_move, shift_pressed));
}
