"""Five extra tools for Part 1, run 4.

Paste these into week-03/demos/03-mcp-server-minimal/server.py, next to the
existing tool, and restart the server. Adjust the decorator name to whatever
the demo uses (`@mcp.tool()` in the usual FastMCP style).

The bodies return canned strings on purpose. The descriptions are deliberately
realistic and wordy, because the docstring is what becomes the tool description
in the registry, and the registry is what you are measuring. A tool with a
one-word docstring would not cost what a real tool costs.
"""


@mcp.tool()  # noqa: F821 - `mcp` comes from the demo's server.py
def get_warehouse_map(zone: str) -> str:
    """Return the aisle-by-aisle layout of one warehouse zone.

    Gives the physical map of a storage zone: aisle identifiers, rack heights in
    centimetres, the number of pallet positions per rack, floor-load limits, and
    which aisles are reachable by which robot chassis. Use this before planning
    any route or placement task, since a zone that looks empty in inventory may
    still be unreachable for a given chassis. Zones are named like "A", "B3" or
    "COLD-2"; pass the identifier exactly as it appears on the site plan.
    """
    return "Zone A: aisles A1-A8, rack height 420cm, 12 pallet positions/rack."


@mcp.tool()  # noqa: F821
def open_support_ticket(summary: str, severity: str, component: str) -> str:
    """Open a support ticket against a deployed robot or fleet component.

    Creates a ticket in the field-service queue and returns its identifier.
    Severity must be one of "low", "normal", "high" or "critical"; critical
    pages the on-call engineer immediately, so reserve it for a stopped line or
    a safety event. The component should name the failing subsystem (for example
    "drive", "lidar", "gripper", "charger") so the ticket routes to the right
    team without a triage pass. Include what was observed in the summary, not
    what you think caused it.
    """
    return "Ticket ACME-4417 created."


@mcp.tool()  # noqa: F821
def check_battery_health(serial: str) -> str:
    """Report the battery health of one robot by serial number.

    Returns the pack's current state of charge, its state of health as a
    percentage of original capacity, cycle count, the highest cell temperature
    seen in the last 24 hours, and the date of the last full calibration
    discharge. A state of health below 80 percent means the pack is due for
    replacement and the robot should not be scheduled for a full shift. Serial
    numbers are printed on the chassis plate and look like "PP-2291".
    """
    return "PP-2291: SoC 62%, SoH 91%, 418 cycles, max cell temp 41C."


@mcp.tool()  # noqa: F821
def schedule_maintenance(serial: str, date: str, task: str) -> str:
    """Book a maintenance slot for one robot.

    Reserves a bay and an engineer for the named task on the given date, and
    returns the booking reference along with the expected downtime. Dates are
    ISO-8601 (YYYY-MM-DD). Booking a robot that already has an open slot on that
    date replaces the earlier booking rather than adding a second one. Common
    tasks are "battery-swap", "lidar-calibration", "gripper-service" and
    "annual-inspection"; anything else is queued for manual triage.
    """
    return "Booking MNT-0083 confirmed, estimated downtime 3h."


@mcp.tool()  # noqa: F821
def list_firmware_versions(model: str) -> str:
    """List the firmware versions available for an Acme Robotics model.

    Returns every published firmware build for the model, newest first, with its
    version string, release date, release channel ("stable", "beta" or
    "recalled"), and a short note on what changed. Recalled builds are listed so
    that a fleet can be audited for them; never install one. Model names match
    the spec sheet exactly, for example "Pallet Pup" or "Crate Collie".
    """
    return "2.7.1 stable (2026-04-02); 2.7.0 recalled; 2.6.4 stable."
