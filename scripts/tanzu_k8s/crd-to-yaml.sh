#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Check if CRD name is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <crd-name>"
    echo "Example: $0 certificates.cert-manager.io"
    exit 1
fi

CRD_NAME=$1

# 1. Verify the CRD exists and extract API group/version
echo "🔍 Fetching CRD metadata for $CRD_NAME..." >&2
CRD_JSON=$(kubectl get crd "$CRD_NAME" -o json 2>/dev/null)

if [ -z "$CRD_JSON" ]; then
    echo "❌ Error: CRD '$CRD_NAME' not found in cluster." >&2
    exit 1
fi

# Extract Group, Kind, and the latest/stored version
GROUP=$(echo "$CRD_JSON" | jq -r '.spec.group')
KIND=$(echo "$CRD_JSON" | jq -r '.spec.names.kind')
VERSION=$(echo "$CRD_JSON" | jq -r '.spec.versions[] | select(.storage==true).name')

# Fallback if no explicit storage version is flagged
if [ -z "$VERSION" ] || [ "$VERSION" == "null" ]; then
    VERSION=$(echo "$CRD_JSON" | jq -r '.spec.versions.name')
fi

echo "📋 Found Resource: Kind: $KIND, APIVersion: $GROUP/$VERSION" >&2
echo "🛠️  Extracting fields via 'kubectl explain'..." >&2

# 2. Extract the recursive field tree using kubectl explain
EXPLAIN_TREE=$(kubectl explain "$KIND" --recursive 2>/dev/null)

if [ -z "$EXPLAIN_TREE" ]; then
    # Fallback to group-qualified name if Kind conflicts
    EXPLAIN_TREE=$(kubectl explain "${KIND}.${GROUP}" --recursive)
fi

# Export variables so the subshell Python environment can read them natively via os.environ
export EXPLAIN_TREE
export GROUP
export KIND
export VERSION

# 3. Use Python to parse the environment variables safely into a YAML template
python3 - <<'EOF'
import os
import sys
import yaml
import re

raw_tree = os.environ.get('EXPLAIN_TREE', '')
group = os.environ.get('GROUP', '')
kind = os.environ.get('KIND', '')
version = os.environ.get('VERSION', '')

lines = raw_tree.split('\n')

# Keep track of structural fields and types cleanly
flat_schema = {}
current_path = []
last_field_path_str = None

# Step 1: Parse the plain-text tree into a flat key-value path schema
for line in lines:
    if not line.strip() or any(line.startswith(p) for p in ['GROUP:', 'KIND:', 'VERSION:', 'DESCRIPTION:', 'FIELDS:']):
        continue

    leading_spaces = len(line) - len(line.lstrip())
    level = leading_spaces // 2
    cleaned_line = line.strip()

    # Handle standalone enum lines belonging to the immediate previous field path
    if cleaned_line.startswith("enum:") and last_field_path_str:
        enum_content = cleaned_line.replace("enum:", "").strip()
        options = [opt.strip() for opt in enum_content.split(",") if opt.strip()]
        enum_str = f"<enum {'|'.join(options)}>"

        # Check if the field was an array type or single type
        if "[]" in flat_schema.get(last_field_path_str, ""):
            flat_schema[last_field_path_str] = f"<[]enum {'|'.join(options)}>"
        else:
            flat_schema[last_field_path_str] = enum_str
        continue

    # Tokenize standard field line into: [field_name, metadata]
    tokens = re.split(r'\s+', cleaned_line, maxsplit=1)
    field_name = tokens[0]
    metadata = tokens[1].replace("-required-", "").strip() if len(tokens) > 1 else ""

    if not field_name or field_name.startswith('-'):
        continue

    # Isolate data type
    type_match = re.search(r'<([^>]+)>', metadata)
    field_type = f"<{type_match.group(1)}>" if type_match else "<Object>"

    # Align our breadcrumb path tracker to match indentation depth
    current_path = current_path[:level-1]
    current_path.append(field_name)

    # Skip tracking boilerplate root parameters
    if len(current_path) > 0 and current_path[0] in ['apiVersion', 'kind', 'metadata']:
        continue

    path_str = ".".join(current_path)
    flat_schema[path_str] = field_type
    last_field_path_str = path_str

# Step 2: Explode flat paths into a cleanly nested dictionary manifest structure
yaml_structure = {}

# Filter out paths that are parents of deeper paths so they don't overwrite child nodes
all_paths = sorted(flat_schema.keys())
leaf_paths = [p for p in all_paths if not any(other.startswith(p + ".") for other in all_paths)]

for path in leaf_paths:
    parts = path.split('.')
    node = yaml_structure

    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)

        # Reconstruct the current path prefix step to lookup its data type
        step_path = ".".join(parts[:i+1])
        step_type = flat_schema.get(step_path, "<Object>")
        is_array = "[]" in step_type

        if is_last:
            if is_array:
                # Format primitive array types into standard lists cleanly
                clean_t = step_type.replace("[]", "")
                node[part] = [clean_t]
            else:
                node[part] = step_type
        else:
            # Build intermediate structural routing branches
            if part not in node:
                node[part] = [{}] if is_array else {}

            # Navigate into the subshell context safely
            if isinstance(node[part], list):
                if not node[part]:
                    node[part].append({})
                node = node[part][0]
            else:
                node = node[part]

# Step 3: Bundle everything into the canonical Kubernetes layout
manifest = {
    "apiVersion": f"{group}/{version}",
    "kind": kind,
    "metadata": {
        "name": f"example-{kind.lower()}",
        "namespace": "default"
    },
    "spec": yaml_structure.get("spec", {})
}

# Add top level elements that aren't inside the standard spec payload block
for k, v in yaml_structure.items():
    if k not in ["spec", "status", "apiVersion", "kind", "metadata"]:
        manifest[k] = v

print(yaml.dump(manifest, sort_keys=False))
EOF
