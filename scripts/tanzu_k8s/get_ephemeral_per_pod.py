#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys

def format_bytes(size_bytes):
    if not size_bytes or size_bytes == 0:
        return "0B"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f}{units[i]}"

def get_nodes(target_node=None):
    cmd = ["kubectl", "get", "nodes", "-o", "jsonpath={.items[*].metadata.name}"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    all_nodes = res.stdout.split()

    if target_node:
        # Filter nodes by exact or partial match
        filtered_nodes = [n for n in all_nodes if target_node.lower() in n.lower()]
        if not filtered_nodes:
            print(f"Error: No nodes matched filter '{target_node}'", file=sys.stderr)
            sys.exit(1)
        return filtered_nodes

    return all_nodes

def get_pod_storage(node_name):
    cmd = ["kubectl", "get", "--raw", f"/api/v1/nodes/{node_name}/proxy/stats/summary"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return []
    
    pod_metrics = []
    try:
        data = json.loads(res.stdout)
        pods = data.get("pods", [])
        for pod in pods:
            pod_ref = pod.get("podRef", {})
            namespace = pod_ref.get("namespace", "unknown")
            pod_name = pod_ref.get("name", "unknown")
            
            # Extract ephemeral storage usage
            ephemeral = pod.get("ephemeral-storage", {})
            used_bytes = ephemeral.get("usedBytes", 0)

            pod_metrics.append({
                "node": node_name,
                "namespace": namespace,
                "pod": pod_name,
                "used": format_bytes(used_bytes),
                "used_raw": used_bytes
            })
    except json.JSONDecodeError:
        pass
        
    return pod_metrics

def main():
    parser = argparse.ArgumentParser(description="Report ephemeral storage usage by pod across Kubernetes nodes.")
    parser.add_argument(
        "-n", "--node",
        dest="target_node",
        help="Filter pods by node name (supports exact or partial node name matching)",
        type=str,
        default=None
    )
    args = parser.parse_args()

    try:
        nodes = get_nodes(args.target_node)
    except Exception as e:
        print(f"Error getting node list: {e}", file=sys.stderr)
        sys.exit(1)

    all_metrics = []

    # 1. Collect metrics from target nodes
    for node in nodes:
        metrics = get_pod_storage(node)
        all_metrics.extend(metrics)

    if not all_metrics:
        print("No pod metrics found.")
        sys.exit(0)

    # 2. Sort order: Node Name -> Namespace -> Pod Name (case-insensitive)
    all_metrics.sort(
        key=lambda x: (
            x["node"].lower(),
            x["namespace"].lower(),
            x["pod"].lower()
        )
    )

    # 3. Calculate max widths dynamically
    headers = {"node": "NODE", "namespace": "NAMESPACE", "pod": "POD", "used": "USED"}
    padding = 3

    node_width = max(len(headers["node"]), max(len(x["node"]) for x in all_metrics)) + padding
    ns_width = max(len(headers["namespace"]), max(len(x["namespace"]) for x in all_metrics)) + padding
    pod_width = max(len(headers["pod"]), max(len(x["pod"]) for x in all_metrics)) + padding
    used_width = max(len(headers["used"]), max(len(x["used"]) for x in all_metrics))

    printf_fmt = f"{{:<{node_width}}} {{:<{ns_width}}} {{:<{pod_width}}} {{:<{used_width}}}"

    # 4. Print headers and separator line
    header_line = printf_fmt.format(headers["node"], headers["namespace"], headers["pod"], headers["used"])
    print(header_line)
    print("-" * len(header_line))

    # 5. Print sorted metrics
    for item in all_metrics:
        print(printf_fmt.format(item["node"], item["namespace"], item["pod"], item["used"]))

if __name__ == "__main__":
    main()