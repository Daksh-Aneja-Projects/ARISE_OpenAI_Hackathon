"""
Diagram Generator — generates architecture diagrams from solution data.
Produces Mermaid diagram syntax that can be rendered client-side.
"""

from typing import Any, Dict


def generate_architecture_diagram(solution_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a Mermaid architecture diagram from solution package data."""
    sol_pkg = solution_data.get("solution_package", solution_data)
    arch = sol_pkg.get("architecture", {})
    layers = arch.get("layers", [])
    integrations = sol_pkg.get("integration_landscape", {}).get("integrations", [])

    # Build Mermaid flowchart
    lines = ["graph TB"]
    lines.append('    subgraph "Solution Architecture"')

    for i, layer in enumerate(layers):
        layer_id = f"L{i}"
        layer_name = layer.get("name", f"Layer {i}")
        lines.append(f'    subgraph {layer_id}["{layer_name}"]')
        for j, comp in enumerate(layer.get("components", [])):
            comp_id = f"L{i}C{j}"
            lines.append(f'        {comp_id}["{comp}"]')
        lines.append("    end")

    # Connect layers
    for i in range(len(layers) - 1):
        lines.append(f"    L{i} --> L{i + 1}")

    lines.append("    end")

    # Add integrations
    if integrations:
        lines.append('    subgraph EXT["External Systems"]')
        for k, integ in enumerate(integrations[:6]):
            ext_id = f"EXT{k}"
            lines.append(f'        {ext_id}["{integ.get("target", f"System {k}")}"]')
        lines.append("    end")
        if layers:
            lines.append(f"    L{len(layers) - 1} <--> EXT")

    mermaid_code = "\n".join(lines)

    return {
        "status": "success",
        "mermaid_code": mermaid_code,
        "diagram_type": "architecture",
        "layers_count": len(layers),
        "integrations_count": len(integrations),
    }


def generate_timeline_diagram(scope_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a Mermaid Gantt chart from scope data."""
    scope_pkg = scope_data.get("scope_package", scope_data)
    wbs = scope_pkg.get("work_breakdown_structure", [])

    lines = ["gantt"]
    lines.append("    title Project Timeline")
    lines.append("    dateFormat YYYY-MM-DD")
    lines.append("    axisFormat %b %Y")

    for phase in wbs:
        phase_name = phase.get("phase", "Phase")
        lines.append(f"    section {phase_name}")
        for wp in phase.get("work_packages", []):
            wp_name = wp.get("name", "Work Package")
            effort = wp.get("estimated_effort_days", 10)
            lines.append(f"        {wp_name} : {effort}d")

    return {
        "status": "success",
        "mermaid_code": "\n".join(lines),
        "diagram_type": "gantt",
        "phases_count": len(wbs),
    }
