use pyo3::pyclass;
use serde::{Deserialize, Serialize};

use crate::settings::{GameMode, SearchSettings};

#[pyclass(eq)]
#[derive(PartialEq, Eq, Debug, Copy, Clone, Hash, Serialize, Deserialize)]
pub enum Move {
    NONE,
    A,
    D,
    W,
    WA,
    WD,
    S,
    SA,
    SD,
}

impl Move {
    pub fn all_gm(gamemode: GameMode) -> Vec<Move> {
        static DIRECTIONS_SCROLLER: [Move; 9] = [
            Move::NONE,
            Move::A,
            Move::D,
            Move::W,
            Move::WA,
            Move::WD,
            Move::S,
            Move::SA,
            Move::SD,
        ];

        static DIRECTIONS_PLATFORMER: [Move; 6] =
            [Move::NONE, Move::A, Move::D, Move::W, Move::WA, Move::WD];

        match gamemode {
            GameMode::Scroller => DIRECTIONS_SCROLLER.into(),
            GameMode::Platformer => DIRECTIONS_PLATFORMER.into(),
        }
    }

    pub fn all(settings: &SearchSettings) -> Vec<Move> {
        if !settings.allowed_moves.is_empty() {
            return settings.allowed_moves.clone();
        }
        Self::all_gm(settings.mode)
    }

    pub fn is_only_vertical(&self) -> bool {
        *self == Move::NONE || *self == Move::S || *self == Move::W
    }

    pub fn is_left(&self) -> bool {
        *self == Move::A || *self == Move::WA || *self == Move::SA
    }

    pub fn is_right(&self) -> bool {
        *self == Move::D || *self == Move::WD || *self == Move::SD
    }

    pub fn is_up(&self) -> bool {
        *self == Move::W || *self == Move::WA || *self == Move::WD
    }

    pub fn is_down(&self) -> bool {
        *self == Move::S || *self == Move::SA || *self == Move::SD
    }
}

#[pyclass(eq)]
#[derive(PartialEq, Eq, Debug, Copy, Clone, Hash, Serialize, Deserialize)]
pub struct Action {
    pub mov: Move,
    pub shift: bool,
}

impl Action {
    pub fn all_gm(gamemode: GameMode) -> Vec<Action> {
        let mut acts = vec![];
        for mov in Move::all_gm(gamemode) {
            for shift in [true, false] {
                acts.push(Action { mov, shift });
            }
        }
        return acts;
    }
}

#[pyclass(eq)]
#[derive(PartialEq, Eq, Debug, Copy, Clone, Hash, Serialize, Deserialize)]
pub enum Direction {
    N,
    S,
    E,
    W,
}
