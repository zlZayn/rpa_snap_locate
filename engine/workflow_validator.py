import logging

logger = logging.getLogger("rpa_snap_locate.workflow_validator")

_VALID_EVENT_TYPES = {"mouse_down", "mouse_up", "screenshot"}
_VALID_BUTTONS = {"left", "right", "middle"}


class ValidationError(ValueError):
    pass


def validate_v5_events(events: list[dict]) -> None:
    if not isinstance(events, list):
        raise ValidationError("events must be a list")
    if not events:
        raise ValidationError("events list must not be empty")

    down_events: dict[int, dict] = {}
    up_indices: set[int] = set()
    seen_indices: set[int] = set()
    paired_downs: set[int] = set()
    open_down_by_button: dict[str, int] = {}

    for i, event in enumerate(events):
        _validate_event_structure(event, i)
        idx = event["index"]
        typ = event["type"]

        if idx in seen_indices:
            raise ValidationError(f"duplicate event index {idx}")
        seen_indices.add(idx)

        if i > 0:
            prev = events[i - 1]
            prev_key = (prev.get("offset_ns", 0), prev["index"])
            cur_key = (event["offset_ns"], idx)
            if cur_key < prev_key:
                raise ValidationError(
                    f"events not sorted by (offset_ns, index) at position {i}: "
                    f"offset_ns={event['offset_ns']}, index={idx} "
                    f"after offset_ns={prev['offset_ns']}, index={prev['index']}"
                )

        if typ == "screenshot":
            if "region" not in event:
                raise ValidationError(
                    f"screenshot event {idx} must have a region"
                )

        elif typ == "mouse_down":
            if "position_from_event" in event:
                raise ValidationError(
                    f"mouse_down event {idx} must not have position_from_event"
                )
            if "method" not in event:
                raise ValidationError(f"mouse_down event {idx} must have a method")
            if "norm_x" not in event or "norm_y" not in event:
                raise ValidationError(
                    f"mouse_down event {idx} must have norm_x and norm_y"
                )
            if "window_title" not in event:
                raise ValidationError(f"mouse_down event {idx} must have window_title")
            button = event["button"]
            if button in open_down_by_button:
                raise ValidationError(
                    f"mouse button {button} pressed again before release; "
                    f"open mouse_down event {open_down_by_button[button]}"
                )
            down_events[idx] = event
            open_down_by_button[button] = idx

        elif typ == "mouse_up":
            if "method" in event:
                raise ValidationError(f"mouse_up event {idx} must not have method")
            if "norm_x" in event or "norm_y" in event:
                raise ValidationError(
                    f"mouse_up event {idx} must not have norm_x or norm_y"
                )
            if "position_from_event" not in event:
                raise ValidationError(
                    f"mouse_up event {idx} must have position_from_event"
                )
            down_idx = event["position_from_event"]
            if not isinstance(down_idx, int):
                raise ValidationError(
                    f"mouse_up event {idx} has invalid position_from_event"
                )
            if down_idx not in down_events:
                raise ValidationError(
                    f"position_from_event references non-existent mouse_down "
                    f"or a later event: {down_idx}"
                )
            down_event = down_events[down_idx]
            if event["button"] != down_event["button"]:
                raise ValidationError(
                    f"mouse_up event {idx} button {event['button']} does not match "
                    f"mouse_down event {down_idx} button {down_event['button']}"
                )
            if down_idx in paired_downs:
                raise ValidationError(
                    f"mouse_down event {down_idx} has more than one mouse_up"
                )
            if open_down_by_button.get(event["button"]) != down_idx:
                raise ValidationError(
                    f"mouse_up event {idx} does not close the active "
                    f"mouse_down for button {event['button']}"
                )
            paired_downs.add(down_idx)
            open_down_by_button.pop(event["button"])
            up_indices.add(idx)

    if open_down_by_button:
        raise ValidationError(
            "mouse_down events without matching mouse_up: "
            f"{sorted(open_down_by_button.values())}"
        )

    if events[0]["offset_ns"] != 0:
        raise ValidationError("first input event must have offset_ns 0")

    screenshot_count = sum(1 for e in events if e["type"] == "screenshot")
    logger.info(
        "v5 validation passed: %d events (%d down, %d up, %d screenshot)",
        len(events),
        len(down_events),
        len(up_indices),
        screenshot_count,
    )


def _validate_event_structure(event: dict, position: int) -> None:
    if not isinstance(event, dict):
        raise ValidationError(f"event at position {position} is not a dict")

    for field in ("index", "type", "offset_ns"):
        if field not in event:
            raise ValidationError(
                f"event at position {position} missing required field '{field}'"
            )

    if not isinstance(event["index"], int) or event["index"] < 1:
        raise ValidationError(
            f"event at position {position} has invalid index: {event['index']}"
        )

    if event["type"] not in _VALID_EVENT_TYPES:
        raise ValidationError(
            f"event at position {position} has invalid type: {event['type']}"
        )

    if event["type"] == "screenshot":
        if "button" in event:
            raise ValidationError(
                f"screenshot event at position {position} must not have button"
            )
    else:
        if "button" not in event:
            raise ValidationError(
                f"event at position {position} missing required field 'button'"
            )
        if event["button"] not in _VALID_BUTTONS:
            raise ValidationError(
                f"event at position {position} has invalid button: {event['button']}"
            )

    if not isinstance(event["offset_ns"], int) or event["offset_ns"] < 0:
        raise ValidationError(
            f"event at position {position} has invalid offset_ns: {event['offset_ns']}"
        )
