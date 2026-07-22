from __future__ import annotations

import uuid


PIN_PITCH = 2.54
SUPPORTED_GENERATORS = {
    "connector_1xn_pin_vertical",
    "connector_1xn_socket_vertical",
    "connector_jst_xh_vertical",
}


def generator_template_fields(generator: str) -> list[str]:
    if generator in SUPPORTED_GENERATORS:
        return ["pins"]
    return []


def generate_snippet(generator: str, values: dict[str, str]) -> str:
    pins = int(values.get("pins", "4"))
    pins_2 = f"{pins:02d}"
    if generator == "connector_1xn_pin_vertical":
        return generate_connector_1xn(kind="pin", pins=pins)
    if generator == "connector_1xn_socket_vertical":
        return generate_connector_1xn(kind="socket", pins=pins)
    if generator == "connector_jst_xh_vertical":
        if pins < 2:
            raise ValueError("JST XH connectors must have at least 2 pins.")
        footprint = f"Connector_JST:JST_XH_B{pins}B-XH-A_1x{pins_2}_P2.50mm_Vertical"
        return generate_connector_1xn(kind="pin", pins=pins, footprint=footprint)
    raise ValueError(f"Unsupported generator: {generator}")


def generate_connector_1xn(kind: str, pins: int, footprint: str = "") -> str:
    if pins < 1:
        raise ValueError("pins must be positive")

    pins_2 = f"{pins:02d}"
    if kind == "pin":
        suffix = "Pin"
        footprint = footprint or f"Connector_PinHeader_2.54mm:PinHeader_1x{pins_2}_P2.54mm_Vertical"
    elif kind == "socket":
        suffix = "Socket"
        footprint = footprint or f"Connector_PinSocket_2.54mm:PinSocket_1x{pins_2}_P2.54mm_Vertical"
    else:
        raise ValueError(f"Unsupported connector kind: {kind}")

    lib_id = f"Connector:Conn_01x{pins_2}_{suffix}"
    symbol_name = f"Conn_01x{pins_2}_{suffix}"
    top_y = ((pins - 1) // 2) * PIN_PITCH
    bottom_y = top_y - ((pins - 1) * PIN_PITCH)
    ref_y = top_y + PIN_PITCH
    value_y = bottom_y - PIN_PITCH
    instance_ref_y = -(top_y + (2 * PIN_PITCH))
    instance_value_y = -(top_y + PIN_PITCH)

    lines: list[str] = [
        "(lib_symbols",
        f'\t(symbol "{lib_id}"',
        "\t\t(pin_names",
        "\t\t\t(offset 1.016)",
        "\t\t\t(hide yes)",
        "\t\t)",
        "\t\t(exclude_from_sim no)",
        "\t\t(in_bom yes)",
        "\t\t(on_board yes)",
    ]
    lines.extend(property_block(2, "Reference", "J", 0, ref_y, hidden=False))
    lines.extend(property_block(2, "Value", symbol_name, 0, value_y, hidden=False))
    lines.extend(property_block(2, "Footprint", "", 0, 0, hidden=True))
    lines.extend(property_block(2, "Datasheet", "~", 0, 0, hidden=True))
    lines.extend(
        property_block(
            2,
            "Description",
            f"Generic connector, single row, 01x{pins_2}, script generated",
            0,
            0,
            hidden=True,
        )
    )
    lines.extend(property_block(2, "ki_locked", "", 0, 0, hidden=False))
    lines.extend(property_block(2, "ki_keywords", "connector", 0, 0, hidden=True))
    lines.extend(property_block(2, "ki_fp_filters", "Connector*:*_1x??_*", 0, 0, hidden=True))
    lines.append(f'\t\t(symbol "{symbol_name}_1_1"')

    for index in range(1, pins + 1):
        y = pin_y(index, pins)
        if kind == "pin":
            lines.extend(male_graphics(y))
        else:
            lines.extend(socket_graphics(y))

    for index in range(1, pins + 1):
        y = pin_y(index, pins)
        lines.extend(pin_block(kind, index, y))

    lines.extend([
        "\t\t)",
        "\t\t(embedded_fonts no)",
        "\t)",
        ")",
        "(symbol",
        f'\t(lib_id "{lib_id}")',
        "\t(at 0 0 0)",
        "\t(unit 1)",
        "\t(exclude_from_sim no)",
        "\t(in_bom yes)",
        "\t(on_board yes)",
        "\t(dnp no)",
        "\t(fields_autoplaced yes)",
        f'\t(uuid "{uuid.uuid4()}")',
    ])
    lines.extend(property_block(1, "Reference", "J?", 0.635, instance_ref_y, hidden=False))
    lines.extend(property_block(1, "Value", symbol_name, 0.635, instance_value_y, hidden=False))
    lines.extend(property_block(1, "Footprint", footprint, 0, 0, hidden=True))
    lines.extend(property_block(1, "Datasheet", "~", 0, 0, hidden=True))
    lines.extend(
        property_block(
            1,
            "Description",
            f"Generic connector, single row, 01x{pins_2}, script generated",
            0,
            0,
            hidden=True,
        )
    )
    for index in range(1, pins + 1):
        lines.extend([
            f'\t(pin "{index}"',
            f'\t\t(uuid "{uuid.uuid4()}")',
            "\t)",
        ])
    lines.extend([
        "\t(instances",
        "\t\t(project \"\"",
        "\t\t\t(path \"\"",
        "\t\t\t\t(reference \"J?\")",
        "\t\t\t\t(unit 1)",
        "\t\t\t)",
        "\t\t)",
        "\t)",
        ")",
        "",
    ])
    return "\n".join(lines)


def pin_y(index: int, pins: int) -> float:
    top_y = ((pins - 1) // 2) * PIN_PITCH
    return top_y - ((index - 1) * PIN_PITCH)


def male_graphics(y: float) -> list[str]:
    return [
        "\t\t\t(rectangle",
        f"\t\t\t\t(start 0.8636 {fmt(y + 0.127)})",
        f"\t\t\t\t(end 0 {fmt(y - 0.127)})",
        "\t\t\t\t(stroke (width 0.1524) (type default))",
        "\t\t\t\t(fill (type outline))",
        "\t\t\t)",
        "\t\t\t(polyline",
        "\t\t\t\t(pts",
        f"\t\t\t\t\t(xy 1.27 {fmt(y)}) (xy 0.8636 {fmt(y)})",
        "\t\t\t\t)",
        "\t\t\t\t(stroke (width 0.1524) (type default))",
        "\t\t\t\t(fill (type none))",
        "\t\t\t)",
    ]


def socket_graphics(y: float) -> list[str]:
    return [
        "\t\t\t(polyline",
        "\t\t\t\t(pts",
        f"\t\t\t\t\t(xy -1.27 {fmt(y)}) (xy -0.508 {fmt(y)})",
        "\t\t\t\t)",
        "\t\t\t\t(stroke (width 0.1524) (type default))",
        "\t\t\t\t(fill (type none))",
        "\t\t\t)",
        "\t\t\t(arc",
        f"\t\t\t\t(start 0 {fmt(y - 0.508)})",
        f"\t\t\t\t(mid -0.5058 {fmt(y)})",
        f"\t\t\t\t(end 0 {fmt(y + 0.508)})",
        "\t\t\t\t(stroke (width 0.1524) (type default))",
        "\t\t\t\t(fill (type none))",
        "\t\t\t)",
    ]


def pin_block(kind: str, index: int, y: float) -> list[str]:
    x = 5.08 if kind == "pin" else -5.08
    rotation = 180 if kind == "pin" else 0
    return [
        "\t\t\t(pin passive line",
        f"\t\t\t\t(at {fmt(x)} {fmt(y)} {rotation})",
        "\t\t\t\t(length 3.81)",
        f'\t\t\t\t(name "Pin_{index}"',
        "\t\t\t\t\t(effects",
        "\t\t\t\t\t\t(font (size 1.27 1.27))",
        "\t\t\t\t\t)",
        "\t\t\t\t)",
        f'\t\t\t\t(number "{index}"',
        "\t\t\t\t\t(effects",
        "\t\t\t\t\t\t(font (size 1.27 1.27))",
        "\t\t\t\t\t)",
        "\t\t\t\t)",
        "\t\t\t)",
    ]


def property_block(indent: int, name: str, value: str, x: float, y: float, hidden: bool) -> list[str]:
    tab = "\t" * indent
    lines = [
        f'{tab}(property "{name}" "{value}"',
        f"{tab}\t(at {fmt(x)} {fmt(y)} 0)",
        f"{tab}\t(effects",
        f"{tab}\t\t(font (size 1.27 1.27))",
    ]
    if hidden:
        lines.append(f"{tab}\t\t(hide yes)")
    lines.extend([
        f"{tab}\t)",
        f"{tab})",
    ])
    return lines


def fmt(value: float) -> str:
    if abs(value) < 0.0001:
        return "0"
    return f"{value:.4f}".rstrip("0").rstrip(".")
