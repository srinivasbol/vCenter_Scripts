from diagrams import Diagram, Cluster, Edge
from diagrams.generic.blank import Blank

OUTPUT_DIR = "output/figures"
GRAPH_ATTR = {
    "fontsize": "18",
    "bgcolor": "white",
    "splines": "spline",
    "pad": "0.5",
    "nodesep": "0.6",
    "ranksep": "0.8",
}


def iam_revocation_flow() -> None:
    with Diagram(
        "iam_revocation_propagation",
        direction="LR",
        show=False,
        filename=f"{OUTPUT_DIR}/iam_revocation_propagation",
        outformat=["png", "pdf"],
        graph_attr=GRAPH_ATTR,
    ):
        soc = Blank("SOC Analyst")
        idp = Blank("Identity Provider\n(Okta/AAD)")
        event_bus = Blank("Revocation Event Bus")

        with Cluster("Policy and Session Plane"):
            pep = Blank("Policy Enforcement Points")
            api_gw = Blank("API Gateway")
            token_cache = Blank("Auth Token Cache")

        with Cluster("Downstream Systems"):
            workloads = Blank("Workloads & Services")
            siem = Blank("SIEM / Forensics")

        soc >> Edge(label="Disable account + rotate secrets") >> idp
        idp >> Edge(label="signed revocation event") >> event_bus
        event_bus >> Edge(label="fan-out (<3s)") >> pep
        event_bus >> Edge(label="cache invalidation") >> token_cache
        pep >> Edge(label="deny + quarantine") >> api_gw
        token_cache >> Edge(label="miss then re-auth") >> api_gw
        api_gw >> Edge(label="terminated sessions") >> workloads
        event_bus >> Edge(label="immutable evidence") >> siem


def nvme_tiering_failover() -> None:
    with Diagram(
        "nvme_tiering_failover",
        direction="LR",
        show=False,
        filename=f"{OUTPUT_DIR}/nvme_tiering_failover",
        outformat=["png", "pdf"],
        graph_attr=GRAPH_ATTR,
    ):
        app = Blank("Auth + Metadata Services")

        with Cluster("Primary Storage Domain"):
            tier0 = Blank("Tier-0 NVMe\n(write journal)")
            tier1 = Blank("Tier-1 SSD\nhot index")
            control = Blank("Storage Control Plane")

        with Cluster("Secondary Storage Domain"):
            standby0 = Blank("Standby Tier-0")
            standby1 = Blank("Standby Tier-1")
            witness = Blank("Quorum Witness")

        app >> Edge(label="R/W I/O") >> tier0
        tier0 >> Edge(label="demote cold blocks") >> tier1
        control >> Edge(label="replication + health") >> tier0
        control >> Edge(label="replication + health") >> tier1

        tier0 >> Edge(label="sync replication", color="darkgreen") >> standby0
        tier1 >> Edge(label="async delta", style="dashed") >> standby1
        control >> Edge(label="fencing") >> witness
        witness >> Edge(label="promote on fault\nRTO < 60s") >> standby0
        witness >> Edge(label="promote + remap") >> standby1


def gpu_thermal_loop() -> None:
    with Diagram(
        "gpu_thermal_control_loop",
        direction="TB",
        show=False,
        filename=f"{OUTPUT_DIR}/gpu_thermal_control_loop",
        outformat=["png", "pdf"],
        graph_attr=GRAPH_ATTR,
    ):
        sensors = Blank("On-die thermal sensors")
        telemetry = Blank("Telemetry Stream")
        controller = Blank("Thermal Controller\n(PID + policy)")

        with Cluster("Actuators"):
            dvfs = Blank("DVFS governor")
            fan = Blank("Fan / coolant control")
            scheduler = Blank("Inference scheduler")

        auth_cache = Blank("Auth cache\nlatency monitor")
        sla = Blank("SLO guardrail engine")

        sensors >> Edge(label="temperature, hotspot") >> telemetry
        telemetry >> Edge(label="1s sampling") >> controller
        controller >> Edge(label="throttle bins") >> dvfs
        controller >> Edge(label="cooling setpoints") >> fan
        controller >> Edge(label="shed/shift jobs") >> scheduler
        scheduler >> Edge(label="queue pressure") >> auth_cache
        auth_cache >> Edge(label="p95 miss + RTT") >> sla
        sla >> Edge(label="override policy") >> controller


def cross_domain_architecture() -> None:
    with Diagram(
        "cross_domain_integration",
        direction="LR",
        show=False,
        filename=f"{OUTPUT_DIR}/cross_domain_integration",
        outformat=["png", "pdf"],
        graph_attr=GRAPH_ATTR,
    ):
        with Cluster("Identity Domain"):
            idp = Blank("IdP + Risk Engine")
            session_plane = Blank("Session Revocation Plane")

        with Cluster("Storage Domain"):
            storage_ctrl = Blank("Tiering + Failover Controller")
            nvme = Blank("NVMe-oF Fabric")

        with Cluster("Accelerator Domain"):
            gpu_ctrl = Blank("GPU Thermal Controller")
            batch = Blank("Inference / ETL Workloads")

        with Cluster("Resilience Domain"):
            orchestrator = Blank("Cross-domain Orchestrator")
            policy = Blank("Policy + Runbook Engine")
            observability = Blank("Observability + Postmortem Data Lake")

        idp >> Edge(label="revocation intents") >> session_plane
        session_plane >> Edge(label="priority incident signal") >> orchestrator
        storage_ctrl >> Edge(label="degraded IO events") >> orchestrator
        gpu_ctrl >> Edge(label="thermal alerts") >> orchestrator

        orchestrator >> Edge(label="gating policy") >> policy
        policy >> Edge(label="safe-mode directives") >> session_plane
        policy >> Edge(label="freeze promotions") >> storage_ctrl
        policy >> Edge(label="job shedding") >> gpu_ctrl

        storage_ctrl >> nvme
        gpu_ctrl >> batch
        orchestrator >> Edge(label="timeline + evidence") >> observability
        session_plane >> Edge(label="audit") >> observability
        storage_ctrl >> Edge(label="replication metrics") >> observability
        gpu_ctrl >> Edge(label="power/thermal metrics") >> observability


def main() -> None:
    iam_revocation_flow()
    nvme_tiering_failover()
    gpu_thermal_loop()
    cross_domain_architecture()


if __name__ == "__main__":
    main()
