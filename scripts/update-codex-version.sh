#!/usr/bin/env bash
set -euo pipefail

dockerfile="${DOCKERFILE_PATH:-codex/Dockerfile}"
config_file="${CONFIG_PATH:-codex/config.yaml}"
changelog="${CHANGELOG_PATH:-codex/CHANGELOG.md}"

current_cli_version="$(sed -nE 's/^ARG CODEX_VERSION=([0-9][0-9A-Za-z.+-]*)$/\1/p' "${dockerfile}")"
current_app_version="$(sed -nE 's/^version:[[:space:]]*"?([0-9]+\.[0-9]+\.[0-9]+)"?[[:space:]]*$/\1/p' "${config_file}")"
latest_cli_version="${LATEST_CODEX_VERSION:-$(npm view @openai/codex@latest version)}"

if [[ -z "${current_cli_version}" || -z "${current_app_version}" || -z "${latest_cli_version}" ]]; then
    echo "Unable to determine the current or latest Codex version." >&2
    exit 1
fi

if [[ "${current_cli_version}" == "${latest_cli_version}" ]]; then
    echo "Codex CLI is already at ${current_cli_version}."
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

echo "Updated Codex CLI ${current_cli_version} -> ${latest_cli_version}; App ${current_app_version} -> ${next_app_version}."
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
        echo "changed=true"
        echo "codex_version=${latest_cli_version}"
        echo "app_version=${next_app_version}"
    } >> "${GITHUB_OUTPUT}"
fi
