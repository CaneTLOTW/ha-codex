#!/usr/bin/env bash
set -euo pipefail

dockerfile="${DOCKERFILE_PATH:-codex/Dockerfile}"
config_file="${CONFIG_PATH:-codex/config.yaml}"
changelog="${CHANGELOG_PATH:-codex/CHANGELOG.md}"
model_config="${MODEL_CONFIG_PATH:-codex/config.yaml}"

current_cli_version="$(sed -nE 's/^ARG CODEX_VERSION=([0-9][0-9A-Za-z.+-]*)$/\1/p' "${dockerfile}")"
current_app_version="$(sed -nE 's/^version:[[:space:]]*"?([0-9]+\.[0-9]+\.[0-9]+)"?[[:space:]]*$/\1/p' "${config_file}")"
latest_cli_version="${LATEST_CODEX_VERSION:-$(npm view @openai/codex@latest version)}"

if [[ -z "${current_cli_version}" || -z "${current_app_version}" || -z "${latest_cli_version}" ]]; then
    echo "Unable to determine the current or latest Codex version." >&2
    exit 1
fi

temporary_home="$(mktemp -d)"
trap 'rm -rf "${temporary_home}"' EXIT

NPM_CONFIG_CACHE="${temporary_home}/npm-cache" \
    npm install --prefix "${temporary_home}/cli" --no-save "@openai/codex@${latest_cli_version}" >/dev/null
codex_bin="${temporary_home}/cli/node_modules/.bin/codex"
model_catalog="${temporary_home}/models.json"
"${codex_bin}" debug models --bundled > "${model_catalog}"

mapfile -t models < <(jq -r '.models[] | select(.visibility == "list" and .supported_in_api == true) | .slug' "${model_catalog}")
if [[ "${#models[@]}" -eq 0 ]]; then
    echo "Unable to determine visible API models from the Codex CLI catalog." >&2
    exit 1
fi

model_options="$(IFS='|'; echo "${models[*]}")"
current_model="$(awk '
    /^options:/ { section = "options"; next }
    /^schema:/ { section = "schema"; next }
    section == "options" && /^  default_model:/ {
        sub(/^  default_model:[[:space:]]*"?/, "")
        sub(/"?[[:space:]]*$/, "")
        print
        exit
    }
' "${model_config}")"
selected_model="${current_model}"
if ! printf '%s\n' "${models[@]}" | grep -Fxq "${selected_model}"; then
    selected_model="${models[0]}"
fi

old_schema="$(sed -nE '/^schema:/,/^environment:/ s/^  default_model:[[:space:]]*list\(([^)]*)\)[[:space:]]*$/\1/p' "${model_config}")"
config_tmp="$(mktemp)"
awk -v selected_model="${selected_model}" -v model_options="${model_options}" '
    /^options:/ { section = "options" }
    /^schema:/ { section = "schema" }
    /^environment:/ { section = "" }
    /^  default_model:/ {
        if (section == "options") {
            print "  default_model: \"" selected_model "\""
            next
        }
        if (section == "schema") {
            print "  default_model: list(" model_options ")"
            next
        }
    }
    { print }
' "${model_config}" > "${config_tmp}"
mv "${config_tmp}" "${model_config}"

models_changed=false
if [[ "${old_schema}" != "${model_options}" ]]; then
    models_changed=true
fi

if [[ "${current_cli_version}" == "${latest_cli_version}" && "${models_changed}" != "true" ]]; then
    echo "Codex CLI and model dropdown are already current."
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        echo "changed=false" >> "${GITHUB_OUTPUT}"
    fi
    exit 0
fi

IFS=. read -r major minor patch extra <<< "${current_app_version}"
if [[ -n "${extra:-}" || ! "${major}" =~ ^[0-9]+$ || ! "${minor}" =~ ^[0-9]+$ || ! "${patch}" =~ ^[0-9]+$ ]]; then
    echo "App version ${current_app_version} is not a three-part numeric version." >&2
    exit 1
fi
next_app_version="${major}.${minor}.$((patch + 1))"

sed -i -E "s/^ARG CODEX_VERSION=.*/ARG CODEX_VERSION=${latest_cli_version}/" "${dockerfile}"
sed -i -E "s/^version:[[:space:]]*.*/version: \"${next_app_version}\"/" "${config_file}"

changelog_tmp="$(mktemp)"
awk -v app_version="${next_app_version}" -v cli_version="${latest_cli_version}" -v release_date="$(date -u +%F)" '
    { print }
    $0 == "All notable changes to this project will be documented in this file." {
        print ""
        print "## [" app_version "] - " release_date
        print ""
        print "### Changed"
        print "- Update bundled OpenAI Codex CLI to " cli_version "."
    }
' "${changelog}" > "${changelog_tmp}"
mv "${changelog_tmp}" "${changelog}"

echo "Updated Codex CLI ${current_cli_version} -> ${latest_cli_version}; App ${current_app_version} -> ${next_app_version}; models: ${model_options}."
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
        echo "changed=true"
        echo "codex_version=${latest_cli_version}"
        echo "app_version=${next_app_version}"
    } >> "${GITHUB_OUTPUT}"
fi
