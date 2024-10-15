#![feature(float_next_up_down)]

const PY_LONG_SHIFT: i32 = 30;

pub fn round(x: f64, ndigits: i32) -> f64 {
    if ndigits == 0 {
        return round_with_none(x) as f64;
    }
    let ndigits = ndigits as usize;
    format!("{x:.ndigits$}", x = x, ndigits = ndigits)
        .parse()
        .unwrap()
}

fn i64_from_double(x: f64) -> i64 {
    let neg = false;
    if x.is_nan() {
        panic!("converting nan to i64");
    }

    if !x.is_finite() {
        panic!("converting nan to i64");
    }

    let mut res = 0i64;

    let (mut frac, expo) = libm::frexp(x);

    let ndig = (expo - 1) / PY_LONG_SHIFT + 1;

    frac = libm::ldexp(frac, (expo - 1) % PY_LONG_SHIFT + 1);

    //println!("{} {}", frac, ndig);
    for i in (0..ndig).rev() {
        let bits = frac as i32;
        res |= (bits as i64) << ((PY_LONG_SHIFT * i) as i64);
        frac -= f64::from(bits);
        frac = libm::ldexp(frac, PY_LONG_SHIFT);
    }

    if neg {
        res = -res;
    }
    res
}

fn round_with_none(x: f64) -> i64 {
    let mut rounded = libm::round(x);
    if (x - rounded).abs() == 0.5 {
        /* halfway case: round to even */
        rounded = 2.0 * libm::round(x / 2.0);
    }
    i64_from_double(rounded)
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::prelude::*;
    use rand::{Rng, SeedableRng};

    #[test]
    fn test_round() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| -> PyResult<()> {
            let builtins = PyModule::import_bound(py, "builtins")?;
            let round_func = builtins.getattr("round")?;
            let result: f64 = round_func.call1((1.5,))?.extract()?;
            assert_eq!(result, 2.0);
            Ok(())
        }).unwrap();
    }

    #[test]
    fn test_round_large() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| -> PyResult<()> {
            let builtins = PyModule::import_bound(py, "builtins")?;
            let round_func = builtins.getattr("round")?;

            // create random generator in rust, seed with 1337
            let mut rng = rand::rngs::StdRng::seed_from_u64(1337);

            // Generate 100 random numbers between 0 and 1000000
            for _ in 0..1000000 {
                let x = rng.gen_range(-1000000.0..1000000.0);
                let ndigits = rng.gen_range(0..10);
                let result: f64 = round_func.call1((x, ndigits))?.extract()?;
                let expected = round(x, ndigits);
                assert_eq!(result, expected);
            }
            Ok(())
        }).unwrap();
    }

    #[test]
    fn test_corner_cases() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| -> PyResult<()> {
            let builtins = PyModule::import_bound(py, "builtins")?;
            let round_func = builtins.getattr("round")?;

            for i in -100..=100 {
                let x = 0.01 * i as f64;

                for ndigits in 0..10 {
                    let result: f64 = round_func.call1((x, ndigits))?.extract()?;
                    let expected = round(x, ndigits);
                    assert_eq!(result, expected);

                    let x_up = x.next_up();
                    let x_down = x.next_down();

                    let result_up: f64 = round_func.call1((x_up, ndigits))?.extract()?;
                    let result_down: f64 = round_func.call1((x_down, ndigits))?.extract()?;

                    let expected_up = round(x_up, ndigits);
                    let expected_down = round(x_down, ndigits);

                    assert_eq!(result_up, expected_up);
                    assert_eq!(result_down, expected_down);
                }
            }


            Ok(())
        }).unwrap();
    }
}
