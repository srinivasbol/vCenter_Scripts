from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server
from diagrams.onprem.network import Nginx
from diagrams.onprem.security import Vault
from diagrams.programming.flowchart import Decision
from diagrams.programming.language import Python
from pathlib import Path
import subprocess


OUTPUT_DIR = Path(__file__).resolve().parent
REQUIRED_PNGS = (
    "zero_trust_reference_architecture.png",
    "iam_ai_agent_lifecycle.png",
    "iam_detection_engineering_pipeline.png",
    "cross_cloud_federation_risk_controls.png",
    "incident_response_playbook_flow.png",
    "token_compromise_response_flow.png",
)


def output_file(name: str) -> str:
    return str(OUTPUT_DIR / name)


def build_zero_trust_reference_architecture() -> None:
    with Diagram(
        "Zero Trust Reference Architecture for IAM Operations",
        filename=output_file("zero_trust_reference_architecture"),
        show=False,
        direction="LR",
    ):
        with Cluster("Access Plane"):
            workforce = Users("Workforce Users")
            third_party = Users("Partners")
            agents = Python("AI Agents")
            workloads = Server("Workloads")

        with Cluster("Identity Control Plane"):
            idp = Server("IdP + Federation")
            risk_engine = Decision("Risk Scoring")
            policy = Nginx("Policy Decision")
            vault = Vault("Secrets + Keys")

        with Cluster("Enforcement Plane"):
            pep = Nginx("Policy Enforcement")
            pam = Server("JIT/PAM")
            telemetry = Server("IAM Telemetry")
            soc = Server("SOC + SOAR")

        for subject in (workforce, third_party, agents, workloads):
            subject >> Edge(label="AuthN/AuthZ") >> pep

        pep >> idp
        idp >> risk_engine >> policy >> pep
        vault >> idp
        pep >> pam
        pep >> telemetry >> soc


def build_ai_agent_lifecycle_architecture() -> None:
    with Diagram(
        "AI Agent Identity Lifecycle Architecture",
        filename=output_file("iam_ai_agent_lifecycle"),
        show=False,
        direction="TB",
    ):
        registry = Server("Agent Registry")
        attestation = Decision("Runtime Attestation")
        issuer = Server("OIDC Token Service")
        policy = Nginx("Authorization Policy")
        runtime = Python("Agent Runtime")
        target_api = Server("Enterprise APIs")
        monitor = Server("Behavioral Analytics")
        revocation = Server("Credential Revocation")

        registry >> Edge(label="Provision") >> issuer
        runtime >> Edge(label="Proof of workload identity") >> attestation >> issuer
        issuer >> Edge(label="Scoped short-lived tokens") >> runtime
        runtime >> policy >> target_api
        runtime >> monitor
        monitor >> Edge(label="Anomaly") >> revocation
        revocation >> issuer


def build_detection_engineering_architecture() -> None:
    with Diagram(
        "IAM Detection Engineering Pipeline",
        filename=output_file("iam_detection_engineering_pipeline"),
        show=False,
        direction="LR",
    ):
        sources = Server("IdP/API/Cloud Audit Logs")
        stream = Server("Streaming + ETL")
        detections = Decision("Detection Rules + ML")
        cases = Server("Case Management")
        response = Server("SOAR Playbooks")
        metrics = Server("SLO Dashboard")

        sources >> stream >> detections
        detections >> Edge(label="High confidence") >> response
        detections >> Edge(label="Investigate") >> cases
        response >> metrics
        cases >> metrics


def build_cross_cloud_federation_architecture() -> None:
    with Diagram(
        "Cross-Cloud Federation Control Architecture",
        filename=output_file("cross_cloud_federation_risk_controls"),
        show=False,
        direction="LR",
    ):
        corporate_idp = Server("Corporate IdP")
        broker = Nginx("Federation Broker")

        with Cluster("Cloud A"):
            cloud_a_sts = Server("STS Role Assumption")
            cloud_a_workloads = Server("Prod Workloads")

        with Cluster("Cloud B"):
            cloud_b_sts = Server("Workload Identity Pool")
            cloud_b_workloads = Server("Data/ML Services")

        with Cluster("Shared Controls"):
            key_mgmt = Vault("Signing Key Mgmt")
            posture = Decision("Continuous Verification")
            soc = Server("SOC Monitoring")

        corporate_idp >> broker
        broker >> cloud_a_sts >> cloud_a_workloads
        broker >> cloud_b_sts >> cloud_b_workloads
        key_mgmt >> corporate_idp
        cloud_a_sts >> posture
        cloud_b_sts >> posture
        posture >> soc


def render_sequence_diagrams() -> None:
    for source in (
        OUTPUT_DIR / "incident_response_playbook_flow.puml",
        OUTPUT_DIR / "token_compromise_response_flow.puml",
    ):
        subprocess.run(["plantuml", "-tpng", str(source)], check=True)


def verify_expected_outputs() -> None:
    missing = [name for name in REQUIRED_PNGS if not (OUTPUT_DIR / name).is_file()]
    if missing:
        raise RuntimeError(f"Missing generated figure(s): {', '.join(missing)}")


if __name__ == "__main__":
    build_zero_trust_reference_architecture()
    build_ai_agent_lifecycle_architecture()
    build_detection_engineering_architecture()
    build_cross_cloud_federation_architecture()
    render_sequence_diagrams()
    verify_expected_outputs()
