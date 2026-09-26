#!/usr/bin/env python3
"""Generate publication figures using Python Diagrams and PlantUML."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from diagrams import Cluster, Diagram
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import SQS
from diagrams.aws.security import Cognito
from diagrams.generic.compute import Rack
from diagrams.onprem.identity import ActiveDirectory
from diagrams.onprem.monitoring import Prometheus


def generate_python_diagram(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / "iam_storage_datacenter_architecture"

    with Diagram(
        "Cross-Cloud IAM and Storage Reliability Control Plane",
        filename=str(filename),
        show=False,
        outformat="png",
    ):
        with Cluster("Enterprise Identity Fabric"):
            hris = ActiveDirectory("HRIS/IdM")
            idp = Cognito("Primary IdP")

        with Cluster("Revocation Event Plane"):
            ingress = Lambda("Signed Event Ingress")
            queue = SQS("Ordered Revocation Queue")
            worker = Lambda("Token Drift Reconciler")

        with Cluster("Datacenter Runtime"):
            storage = Rack("NVMe-oF Tier")
            thermal = Prometheus("GPU Thermal Telemetry")

        hris >> ingress >> queue >> worker >> idp
        worker >> storage
        thermal >> worker

    return filename.with_suffix(".png")


def write_plantuml(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    puml_path = output_dir / "iam_storage_datacenter_architecture.puml"
    puml_content = """@startuml
skinparam shadowing false
skinparam linetype ortho

package "Identity Fabric" {
  [HRIS / IAM Source] as HRIS
  [Primary IdP + Token Introspection] as IDP
}

package "Event Revocation Plane" {
  [Signed Event Ingress] as ING
  [Ordered Revocation Queue] as Q
  [Drift Reconciliation Worker] as W
}

package "Datacenter Runtime" {
  [NVMe-oF Tier Controller] as NVME
  [GPU Thermal Telemetry] as GPU
}

HRIS --> ING
ING --> Q
Q --> W
W --> IDP
W --> NVME : Access path policy updates
GPU --> W : thermal events + policy constraints
@enduml
"""
    puml_path.write_text(puml_content, encoding="utf-8")
    return puml_path


def try_render_plantuml(puml_path: Path) -> None:
    plantuml = ["plantuml", str(puml_path)]
    try:
        subprocess.run(plantuml, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print("PlantUML binary not found; .puml file generated only.")
    except subprocess.CalledProcessError as exc:
        print(f"PlantUML rendering failed: {exc.stderr.strip()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate architecture diagrams for paper")
    parser.add_argument(
        "--output-dir",
        default="/home/runner/work/vCenter_Scripts/vCenter_Scripts/output/figures",
        help="directory for generated assets",
    )
    parser.add_argument(
        "--render-plantuml",
        action="store_true",
        help="attempt to render .puml via local plantuml command",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)

    png = generate_python_diagram(out_dir)
    puml = write_plantuml(out_dir)

    if args.render_plantuml:
        try_render_plantuml(puml)

    print(f"Generated: {png}")
    print(f"Generated: {puml}")


if __name__ == "__main__":
    main()
