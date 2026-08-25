#!/usr/bin/env bash
set -euo pipefail

# Check if cluster name argument is provided
if [ -z "${1:-}" ]; then
  echo "Error: Cluster name argument required."
  echo "Usage: $0 <cluster-name>"
  exit 1
fi

CLUSTER_NAME="$1"
NAMESPACE="${CLUSTER_NAME}"
ADDON_SECRET="${CLUSTER_NAME}-vsphere-cpi-addon"
CPI_CONFIG_NAME="${CLUSTER_NAME}"

echo "=== Target Namespace: '${NAMESPACE}' ==="

# Function to update values.yaml (preserves quotes/types and deletes thumbprint lines)
update_values_yaml() {
  local content="$1"
  echo "${content}" | sed -E \
    -e 's/(insecure[_-]?[fF]lag\s*[:=]\s*)"false"/\1"true"/g' \
    -e 's/(insecure[_-]?[fF]lag\s*[:=]\s*)'\''false'\''/\1'\''true'\''/g' \
    -e 's/(insecure[_-]?[fF]lag\s*[:=]\s*)false/\1true/g' \
    -e 's/(insecure[_-]?[fF]lag\s*[:=]\s*)"0"/\1"1"/g' \
    -e 's/(insecure[_-]?[fF]lag\s*[:=]\s*)0/\11/g' \
    -e '/(tls[_-]?)?[tT]humbprint/d'
}

# Function to update vsphereconf-custom.lib.txt (adds insecure-flag = true strictly inside [Global] section)
update_vsphereconf() {
  local content="$1"
  echo "${content}" | awk '
    BEGIN { in_global = 0; found_insecure = 0; global_seen = 0 }
    
    # Delete any thumbprint references
    /(tls[_-]?)?[tT]humbprint/ { next }

    # Detect INI section headers like [Global] or [VirtualCenter]
    /^\[.*\]/ {
      if (in_global && !found_insecure) {
        print "insecure-flag = true"
        found_insecure = 1
      }
      if (tolower($0) ~ /^\[global\]/) {
        in_global = 1
        global_seen = 1
      } else {
        in_global = 0
      }
      print $0
      next
    }

    # Process lines inside [Global]
    in_global {
      if ($0 ~ /insecure[_-]?[fF]lag/) {
        print "insecure-flag = true"
        found_insecure = 1
        next
      }
    }

    # Output all other lines
    { print $0 }

    END {
      if (in_global && !found_insecure) {
        print "insecure-flag = true"
      } else if (!global_seen && !found_insecure) {
        print "[Global]"
        print "insecure-flag = true"
      }
    }
  '
}

encode_base64() {
  local content="$1"
  echo -n "${content}" | base64 -w 0 2>/dev/null || echo -n "${content}" | base64
}

# ======================================================
# 1. Process <cluster-name>-vsphere-cpi-addon Secret
# ======================================================
echo ""
echo "--- Checking Secret: '${ADDON_SECRET}' ---"
if kubectl get secret "${ADDON_SECRET}" -n "${NAMESPACE}" >/dev/null 2>&1; then
  echo "Fetching and decoding '${ADDON_SECRET}'..."
  ADDON_VALUES=$(kubectl get secret "${ADDON_SECRET}" -n "${NAMESPACE}" -o jsonpath='{.data.values\.yaml}' | base64 --decode 2>/dev/null || true)
  ADDON_CONF=$(kubectl get secret "${ADDON_SECRET}" -n "${NAMESPACE}" -o jsonpath='{.data.vsphereconf-custom\.lib\.txt}' | base64 --decode 2>/dev/null || true)

  PATCH_DATA="{}"

  if [ -n "${ADDON_VALUES}" ]; then
    echo "Modifying 'values.yaml' in '${ADDON_SECRET}'..."
    UPDATED_ADDON_VALUES=$(update_values_yaml "${ADDON_VALUES}")
    ENCODED_ADDON_VALUES=$(encode_base64 "${UPDATED_ADDON_VALUES}")
    PATCH_DATA=$(echo "${PATCH_DATA}" | jq --arg v "${ENCODED_ADDON_VALUES}" '. + {"values.yaml": $v}')
  fi

  if [ -n "${ADDON_CONF}" ]; then
    echo "Modifying 'vsphereconf-custom.lib.txt' in '${ADDON_SECRET}'..."
    UPDATED_ADDON_CONF=$(update_vsphereconf "${ADDON_CONF}")
    ENCODED_ADDON_CONF=$(encode_base64 "${UPDATED_ADDON_CONF}")
    PATCH_DATA=$(echo "${PATCH_DATA}" | jq --arg v "${ENCODED_ADDON_CONF}" '. + {"vsphereconf-custom.lib.txt": $v}')
  fi

  echo "Patching secret '${ADDON_SECRET}'..."
  kubectl patch secret "${ADDON_SECRET}" -n "${NAMESPACE}" --type=merge -p "{\"data\": ${PATCH_DATA}}"
  echo "Successfully updated Secret '${ADDON_SECRET}'."
else
  echo "Secret '${ADDON_SECRET}' not found in namespace '${NAMESPACE}'. Skipping."
fi

# ======================================================
# 2. Process VSphereCPIConfig CR (<cluster-name>)
# ======================================================
echo ""
echo "--- Checking VSphereCPIConfig CR: '${CPI_CONFIG_NAME}' ---"
if kubectl get vspherecpiconfig "${CPI_CONFIG_NAME}" -n "${NAMESPACE}" >/dev/null 2>&1; then
  echo "Modifying VSphereCPIConfig '${CPI_CONFIG_NAME}' in namespace '${NAMESPACE}'..."

  # Build JSON patch payload
  PATCH_OPS='[{"op": "replace", "path": "/spec/vsphereCPI/insecure", "value": true}]'

  # If tlsThumbprint key exists, add a remove operation to the patch
  HAS_THUMBPRINT=$(kubectl get vspherecpiconfig "${CPI_CONFIG_NAME}" -n "${NAMESPACE}" -o jsonpath='{.spec.vsphereCPI.tlsThumbprint}' 2>/dev/null || true)
  if [ -n "${HAS_THUMBPRINT}" ] || kubectl get vspherecpiconfig "${CPI_CONFIG_NAME}" -n "${NAMESPACE}" -o json | jq -e '.spec.vsphereCPI | has("tlsThumbprint")' >/dev/null 2>&1; then
    PATCH_OPS='[{"op": "replace", "path": "/spec/vsphereCPI/insecure", "value": true}, {"op": "remove", "path": "/spec/vsphereCPI/tlsThumbprint"}]'
  fi

  echo "Applying JSON patch to VSphereCPIConfig '${CPI_CONFIG_NAME}'..."
  kubectl patch vspherecpiconfig "${CPI_CONFIG_NAME}" -n "${NAMESPACE}" --type=json -p "${PATCH_OPS}"
  echo "Successfully updated VSphereCPIConfig '${CPI_CONFIG_NAME}'."
else
  echo "VSphereCPIConfig CR '${CPI_CONFIG_NAME}' not found in namespace '${NAMESPACE}'. Skipping."
fi

echo ""
echo "=== Script Execution Complete ==="