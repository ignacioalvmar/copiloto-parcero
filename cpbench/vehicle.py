"""Headless vehicle model for Copiloto Parcero.

Replaces the PromptDrive simulator during benchmarking. It keeps the 31
CAR-bench ``VehicleState`` fields that WorlDrive exposes plus a few extra
fields (media, phone, driving) so every one of the 44 registry tools has a
deterministic effect. Tool semantics follow WorlDrive's
``frontend/src/utils/agentTools.ts`` mappers; results follow the CAR-bench
shape ``{"status": "SUCCESS" | "FAILURE", ...}``.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_HERE, "data")
_TOOLS_PATH = os.environ.get("CPBENCH_TOOLS", os.path.join(DATA_DIR, "tools.json"))


def load_tools(path: Optional[str] = None) -> Dict[str, Any]:
    with open(path or _TOOLS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


_TOOLS = load_tools()
TOOLS_BY_NAME: Dict[str, Dict[str, Any]] = {
    t["function"]["name"]: t for t in _TOOLS["tools"]
}
VEHICLE_FIELDS: Dict[str, Dict[str, Any]] = _TOOLS["vehicle_fields"]


def openai_tools() -> List[Dict[str, Any]]:
    """The 44 tools in OpenAI function-calling format (no x_ metadata)."""
    return [{"type": "function", "function": t["function"]} for t in _TOOLS["tools"]]


def reads_state(name: str) -> bool:
    t = TOOLS_BY_NAME.get(name)
    return bool(t and t.get("x_reads_state"))


def requires_confirmation(name: str) -> bool:
    t = TOOLS_BY_NAME.get(name)
    return bool(t and t.get("x_requires_confirmation"))


# Extra, non-registry state the headless model needs. Keys starting with an
# underscore are situation text injected into {{vehicle_context}} only.
EXTRA_DEFAULTS: Dict[str, Any] = {
    "autonomous_mode": False,
    "cruise_control_enabled": False,
    "cruise_speed_kmh": None,
    "speed_kmh": 48,
    "navigation_destination": None,
    "music_playing": False,
    "music_track": "Radio local",
    "music_volume": 4,
    "phone_call_active": False,
    "phone_call_contact": None,
    "contacts": ["Mamá", "Camilo", "Oficina", "Dra. Rojas"],
    "seats_occupancy": {"DRIVER": True, "PASSENGER": False,
                        "DRIVER_REAR": False, "PASSENGER_REAR": False},
    "car_color": "gris",
    "temperature_inside_c": 23.0,
    "temperature_outside_c": 19.0,
    "weather": "despejado",
    "time_of_day": "día",
    "speed_limit_kmh": 50,
    "_situation": "",
}

WINDOW_FIELDS = {
    "DRIVER": "window_driver_position",
    "PASSENGER": "window_passenger_position",
    "DRIVER_REAR": "window_driver_rear_position",
    "PASSENGER_REAR": "window_passenger_rear_position",
}
READING_FIELDS = {
    "DRIVER": "reading_light_driver",
    "PASSENGER": "reading_light_passenger",
    "DRIVER_REAR": "reading_light_driver_rear",
    "PASSENGER_REAR": "reading_light_passenger_rear",
}


def default_state() -> Dict[str, Any]:
    state: Dict[str, Any] = {}
    for key, spec in VEHICLE_FIELDS.items():
        state[key] = copy.deepcopy(spec.get("default"))
    state.update(copy.deepcopy(EXTRA_DEFAULTS))
    return state


def make_state(context_init: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    state = default_state()
    for key, value in (context_init or {}).items():
        state[key] = copy.deepcopy(value)
    return state


def vehicle_context_text(state: Dict[str, Any]) -> str:
    """Human-readable context that replaces {{vehicle_context}}.

    Mirrors what WorlDrive injects: the public vehicle fields plus the
    situation line. Kept compact so it costs few tokens.
    """
    public = {k: v for k, v in state.items() if k in VEHICLE_FIELDS}
    extra = {
        "modo_autonomo": state["autonomous_mode"],
        "crucero": {"activo": state["cruise_control_enabled"],
                    "velocidad_kmh": state["cruise_speed_kmh"]},
        "velocidad_actual_kmh": state["speed_kmh"],
        "limite_velocidad_kmh": state["speed_limit_kmh"],
        "destino_navegacion": state["navigation_destination"],
        "musica": {"reproduciendo": state["music_playing"],
                   "pista": state["music_track"], "volumen": state["music_volume"]},
        "llamada_activa": state["phone_call_active"],
        "clima_exterior": state["weather"],
        "momento_del_dia": state["time_of_day"],
        "temperatura_exterior_c": state["temperature_outside_c"],
    }
    lines = [json.dumps(public, ensure_ascii=False), json.dumps(extra, ensure_ascii=False)]
    if state.get("_situation"):
        lines.append("Situación: " + str(state["_situation"]))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Argument validation (same rules as WorlDrive's validate_kwargs)
# --------------------------------------------------------------------------

def _validate_args(name: str, args: Dict[str, Any]) -> List[str]:
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        return [f"unknown tool {name}"]
    schema = tool["function"]["parameters"]
    props = schema.get("properties", {})
    errors: List[str] = []
    if not isinstance(args, dict):
        return ["arguments must be an object"]
    for req in schema.get("required", []):
        if req not in args:
            errors.append(f"missing required argument '{req}'")
    for key, value in args.items():
        if key not in props:
            errors.append(f"unexpected argument '{key}'")
            continue
        spec = props[key]
        typ = spec.get("type")
        if typ == "boolean":
            if not isinstance(value, bool):
                errors.append(f"'{key}' must be a boolean")
        elif typ == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"'{key}' must be a number")
                continue
            if "minimum" in spec and value < spec["minimum"]:
                errors.append(f"'{key}' must be >= {spec['minimum']}")
            if "maximum" in spec and value > spec["maximum"]:
                errors.append(f"'{key}' must be <= {spec['maximum']}")
            step = spec.get("multipleOf")
            if step and abs((value / step) - round(value / step)) > 1e-6:
                errors.append(f"'{key}' must be a multiple of {step}")
        elif typ == "string":
            if not isinstance(value, str):
                errors.append(f"'{key}' must be a string")
            elif "enum" in spec and value not in spec["enum"]:
                errors.append(f"'{key}' must be one of {spec['enum']}")
    return errors


# --------------------------------------------------------------------------
# Executor
# --------------------------------------------------------------------------

def _ok(**payload: Any) -> Dict[str, Any]:
    out = {"status": "SUCCESS"}
    out.update(payload)
    return out


def _fail(message: str) -> Dict[str, Any]:
    return {"status": "FAILURE", "message": message}


def execute(name: str, args: Dict[str, Any], state: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Apply one tool call to ``state`` in place.

    Returns ``(result, ok)``. ``ok`` is False for validation failures and
    unknown tools, exactly like a failed facade call in WorlDrive.
    """
    args = args or {}
    errors = _validate_args(name, args)
    if errors:
        return _fail("; ".join(errors)), False

    s = state
    # ---- climate -------------------------------------------------------
    if name == "set_climate_temperature":
        zone = args["zone"]
        temp = float(args["temperature"])
        if zone in ("DRIVER", "ALL_ZONES"):
            s["climate_temperature_driver"] = temp
        if zone in ("PASSENGER", "ALL_ZONES"):
            s["climate_temperature_passenger"] = temp
        return _ok(zone=zone, temperature=temp), True
    if name == "set_fan_speed":
        s["fan_speed"] = int(args["level"])
        return _ok(level=s["fan_speed"]), True
    if name == "set_seat_heating":
        field = "seat_heating_driver" if args["seat"] == "DRIVER" else "seat_heating_passenger"
        s[field] = int(args["level"])
        return _ok(seat=args["seat"], level=s[field]), True
    if name == "set_steering_wheel_heating":
        s["steering_wheel_heating"] = int(args["level"])
        return _ok(level=s["steering_wheel_heating"]), True
    if name == "set_air_conditioning":
        s["air_conditioning"] = bool(args["on"])
        return _ok(on=s["air_conditioning"]), True
    if name == "set_air_circulation":
        s["air_circulation"] = args["mode"]
        return _ok(mode=args["mode"]), True
    if name == "set_fan_airflow_direction":
        s["fan_airflow_direction"] = args["direction"]
        return _ok(direction=args["direction"]), True
    if name == "set_window_defrost":
        on = bool(args["on"])
        if args["window"] in ("FRONT", "ALL"):
            s["window_front_defrost"] = on
        if args["window"] in ("REAR", "ALL"):
            s["window_rear_defrost"] = on
        return _ok(window=args["window"], on=on), True
    # ---- openings ------------------------------------------------------
    if name == "open_close_window":
        pct = int(round(float(args["percentage"])))
        targets = list(WINDOW_FIELDS.values()) if args["window"] == "ALL" else [WINDOW_FIELDS[args["window"]]]
        for f in targets:
            s[f] = pct
        return _ok(window=args["window"], percentage=pct), True
    if name == "open_close_sunroof":
        s["sunroof_position"] = int(round(float(args["percentage"])))
        return _ok(percentage=s["sunroof_position"]), True
    if name == "open_close_sunshade":
        s["sunshade_position"] = int(round(float(args["percentage"])))
        return _ok(percentage=s["sunshade_position"]), True
    if name == "open_close_trunk_door":
        s["trunk_door_position"] = "open" if args["open_close"] == "OPEN" else "closed"
        return _ok(position=s["trunk_door_position"]), True
    # ---- lighting ------------------------------------------------------
    if name == "set_ambient_lights":
        s["ambient_light"] = args["color"]
        return _ok(color=args["color"]), True
    if name == "set_reading_light":
        s[READING_FIELDS[args["seat"]]] = bool(args["on"])
        return _ok(seat=args["seat"], on=bool(args["on"])), True
    if name == "set_fog_lights":
        s["fog_lights"] = bool(args["on"])
        return _ok(on=s["fog_lights"]), True
    if name == "set_head_lights_low_beams":
        s["head_lights_low_beams"] = bool(args["on"])
        return _ok(on=s["head_lights_low_beams"]), True
    if name == "set_head_lights_high_beams":
        s["head_lights_high_beams"] = bool(args["on"])
        return _ok(on=s["head_lights_high_beams"]), True
    # ---- getters -------------------------------------------------------
    if name == "get_climate_settings":
        keys = ["climate_temperature_driver", "climate_temperature_passenger", "fan_speed",
                "fan_airflow_direction", "air_conditioning", "air_circulation",
                "window_front_defrost", "window_rear_defrost"]
        return _ok(**{k: s[k] for k in keys}), True
    if name == "get_temperature_inside_car":
        return _ok(temperature_celsius=s["temperature_inside_c"]), True
    if name == "get_exterior_lights_status":
        return _ok(fog_lights=s["fog_lights"], head_lights_low_beams=s["head_lights_low_beams"],
                   head_lights_high_beams=s["head_lights_high_beams"]), True
    if name == "get_seat_heating_level":
        return _ok(seat_heating_driver=s["seat_heating_driver"],
                   seat_heating_passenger=s["seat_heating_passenger"]), True
    if name == "get_steering_wheel_heating_level":
        return _ok(steering_wheel_heating=s["steering_wheel_heating"]), True
    if name == "get_ambient_light_status_and_color":
        return _ok(ambient_light=s["ambient_light"], on=s["ambient_light"] != "OFF"), True
    if name == "get_reading_lights_status":
        return _ok(**{f: s[f] for f in READING_FIELDS.values()}), True
    if name == "get_vehicle_window_positions":
        return _ok(**{f: s[f] for f in WINDOW_FIELDS.values()}), True
    if name == "get_sunroof_and_sunshade_position":
        return _ok(sunroof_position=s["sunroof_position"], sunshade_position=s["sunshade_position"]), True
    if name == "get_trunk_door_position":
        return _ok(trunk_door_position=s["trunk_door_position"]), True
    if name == "get_seats_occupancy":
        return _ok(**s["seats_occupancy"]), True
    if name == "get_car_color":
        return _ok(color=s["car_color"]), True
    # ---- media ---------------------------------------------------------
    if name == "play_music":
        s["music_playing"] = True
        if args.get("track"):
            s["music_track"] = args["track"]
        return _ok(playing=True, track=s["music_track"]), True
    if name == "pause_music":
        s["music_playing"] = False
        return _ok(playing=False), True
    if name == "resume_music":
        s["music_playing"] = True
        return _ok(playing=True), True
    if name == "next_track":
        s["music_track"] = "Siguiente pista"
        s["music_playing"] = True
        return _ok(track=s["music_track"]), True
    if name == "previous_track":
        s["music_track"] = "Pista anterior"
        s["music_playing"] = True
        return _ok(track=s["music_track"]), True
    if name == "set_music_volume":
        s["music_volume"] = int(args["level"])
        return _ok(level=s["music_volume"]), True
    if name == "get_music_status":
        return _ok(playing=s["music_playing"], track=s["music_track"], volume=s["music_volume"]), True
    # ---- phone ---------------------------------------------------------
    if name == "get_contacts":
        return _ok(contacts=list(s["contacts"])), True
    if name == "call_phone_by_contact":
        wanted = str(args["name"]).strip().lower()
        matches = [c for c in s["contacts"] if wanted and (wanted in c.lower() or c.lower() in wanted)]
        if len(matches) != 1:
            return _fail("no unique contact matches '%s' (matches: %s)" % (args["name"], matches)), False
        s["phone_call_active"] = True
        s["phone_call_contact"] = matches[0]
        s["phone_numbers_called"] = list(s.get("phone_numbers_called") or []) + [matches[0]]
        return _ok(calling=matches[0]), True
    if name == "end_phone_call":
        s["phone_call_active"] = False
        s["phone_call_contact"] = None
        return _ok(call_active=False), True
    # ---- driving -------------------------------------------------------
    if name == "set_autonomous_mode":
        s["autonomous_mode"] = bool(args["on"])
        return _ok(on=s["autonomous_mode"]), True
    if name == "set_cruise_control":
        s["cruise_control_enabled"] = bool(args["enabled"])
        if "speed_kmh" in args:
            s["cruise_speed_kmh"] = float(args["speed_kmh"])
        if not s["cruise_control_enabled"]:
            s["cruise_speed_kmh"] = None
        return _ok(enabled=s["cruise_control_enabled"], speed_kmh=s["cruise_speed_kmh"]), True
    if name == "get_driving_status":
        return _ok(autonomous_mode=s["autonomous_mode"], cruise_control_enabled=s["cruise_control_enabled"],
                   cruise_speed_kmh=s["cruise_speed_kmh"], speed_kmh=s["speed_kmh"],
                   speed_limit_kmh=s["speed_limit_kmh"]), True
    # ---- navigation ----------------------------------------------------
    if name == "set_navigation_destination":
        dest = str(args["destination_name"]).strip()
        if not dest:
            return _fail("destination_name is empty"), False
        s["navigation_active"] = True
        s["navigation_destination"] = dest
        return _ok(destination=dest, route_started=True), True
    if name == "cancel_navigation":
        s["navigation_active"] = False
        s["navigation_destination"] = None
        return _ok(navigation_active=False), True

    return _fail(f"tool {name} has no executor"), False
