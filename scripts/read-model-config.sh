#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config_file="${repo_root}/config/models.env"
model="${VS_OPENAI_MODEL:-}"

if [[ -z "${model}" ]]; then
  if [[ ! -f "${config_file}" ]]; then
    echo "missing model configuration: ${config_file}" >&2
    exit 1
  fi
  while IFS='=' read -r key value; do
    value="${value%$'\r'}"
    if [[ "${key}" == "VS_OPENAI_MODEL" ]]; then
      model="${value}"
      break
    fi
  done <"${config_file}"
fi

if [[ ! "${model}" =~ ^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$ ]]; then
  echo "VS_OPENAI_MODEL is missing or invalid" >&2
  exit 1
fi

printf '%s\n' "${model}"
