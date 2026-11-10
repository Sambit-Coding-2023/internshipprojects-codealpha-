"""Unit tests for the pure logic in the ML engine (no model needed)."""
import numpy as np

from backend.ml.engine import (estimate_light_state, estimate_speed_kmh,
                               helmet_present, light_is_red, segments_cross)


def test_segments_cross():
    assert segments_cross((0, 0), (10, 0), (5, -5), (5, 5)) is True
    assert segments_cross((0, 0), (10, 0), (5, 1), (5, 3)) is False
    assert segments_cross((0, 0), (10, 0), (20, 0), (20, 5)) is False
    assert segments_cross((0, 5), (10, 5), (10, 0), (10, 10)) is True  # endpoint touch


def test_light_clock_red_start():
    cyc = {"red_seconds": 7, "green_seconds": 7, "initial": "red"}
    assert light_is_red(0, cyc) is True
    assert light_is_red(6.9, cyc) is True
    assert light_is_red(7.1, cyc) is False
    assert light_is_red(13.9, cyc) is False
    assert light_is_red(14.1, cyc) is True


def test_light_clock_green_start():
    cyc = {"red_seconds": 7, "green_seconds": 7, "initial": "green"}
    assert light_is_red(0, cyc) is False
    assert light_is_red(7.1, cyc) is True
    assert light_is_red(14.1, cyc) is False


def test_light_clock_no_cycle_is_red():
    assert light_is_red(100, None) is True


def test_estimate_speed_kmh():
    # 10 px/frame, 1 px = 1 m, 25 fps -> 10 m/frame -> 250 m/s -> 900 km/h
    assert abs(estimate_speed_kmh((0, 0), (10, 0), 1.0, 25.0) - 900.0) < 1e-6
    assert estimate_speed_kmh((5, 5), (5, 5), 1.0, 25.0) == 0.0


def test_estimate_light_state():
    red = np.zeros((60, 30, 3), np.uint8)
    red[20:40, 10:20] = (40, 40, 230)      # saturated red patch (BGR)
    assert estimate_light_state(red, (0, 0, 30, 60)) == "red"
    green = np.zeros((60, 30, 3), np.uint8)
    green[20:40, 10:20] = (40, 220, 40)    # saturated green patch (BGR)
    assert estimate_light_state(green, (0, 0, 30, 60)) == "green"
    dark = np.zeros((60, 30, 3), np.uint8)
    assert estimate_light_state(dark, (0, 0, 30, 60)) == "unknown"


def test_helmet_present_colour_heuristic():
    # solid saturated dome (helmet-like) -> True
    helmet = np.zeros((20, 20, 3), np.uint8)
    helmet[:] = (30, 30, 220)  # saturated red in BGR
    assert helmet_present(helmet) is True
    # pale skin-like block (low saturation) -> False
    skin = np.zeros((20, 20, 3), np.uint8)
    skin[:] = (150, 170, 190)
    assert helmet_present(skin) is False
