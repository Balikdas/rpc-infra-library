#!/usr/bin/env bash
set -euo pipefail

# Check for required CLI tools
for cmd in kubectl jq numfmt; do
  if ! command -v "$cmd" &> /dev/null; then
    echo "Error: Required command '$cmd' is not installed." >&2
    exit 1
  fi
done

printf "%-30s %-12s %-12s %-12s %-8s\n" "NODE" "USED" "AVAILABLE" "CAPACITY" "USAGE%"
printf "%s\n" "--------------------------------------------------------------------------------"

# Fetch node names
nodes=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

for node in $nodes; do
  # Query Kubelet summary endpoint through the API server proxy
  stats=$(kubectl get --raw "/api/v1/nodes/${node}/proxy/stats/summary" 2>/dev/null || true)

  if [[ -z "$stats" ]]; then
    printf "%-30s %-12s %-12s %-12s %-8s\n" "$node" "N/A" "N/A" "N/A" "N/A"
    continue
  fi

  # Extract ephemeral-storage metrics from the node filesystem stats
  used_bytes=$(echo "$stats" | jq -r '.node["fs"]["usedBytes"] // 0')
  avail_bytes=$(echo "$stats" | jq -r '.node["fs"]["availableBytes"] // 0')
  capacity_bytes=$(echo "$stats" | jq -r '.node["fs"]["capacityBytes"] // 0')

  if [[ "$capacity_bytes" -gt 0 ]]; then
    # Calculate percentage
    pct=$(awk "BEGIN {printf \"%.1f%%\", ($used_bytes / $capacity_bytes) * 100}")
    
    # Format bytes to human-readable strings (GiB/MiB)
    used_human=$(numfmt --to=iec-i --suffix=B "$used_bytes")
    avail_human=$(numfmt --to=iec-i --suffix=B "$avail_bytes")
    cap_human=$(numfmt --to=iec-i --suffix=B "$capacity_bytes")

    printf "%-30s %-12s %-12s %-12s %-8s\n" "$node" "$used_human" "$avail_human" "$cap_human" "$pct"
  else
    printf "%-30s %-12s %-12s %-12s %-8s\n" "$node" "N/A" "N/A" "N/A" "N/A"
  fi
done