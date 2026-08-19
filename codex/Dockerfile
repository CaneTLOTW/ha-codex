ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.13-alpine3.21
FROM ${BUILD_FROM}

LABEL maintainer="CaneTLOTW"
LABEL org.opencontainers.image.title="Codex App for Home Assistant"
LABEL org.opencontainers.image.description="OpenAI Codex App for the Home Assistant sidebar with terminal access, model controls, and optional MCP integration"
LABEL org.opencontainers.image.source="https://github.com/CaneTLOTW/ha-codex"
LABEL org.opencontainers.image.licenses="MIT"

ENV \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TERM=xterm-256color \
    NODE_OPTIONS=--max-old-space-size=512

RUN apk add --no-cache \
    acl \
    bash \
    bubblewrap \
    ca-certificates \
    coreutils \
    curl \
    findutils \
    gawk \
    git \
    github-cli \
    grep \
    jq \
    nano \
    ncurses \
    ncurses-terminfo-base \
    nodejs \
    npm \
    openssh-client \
    openssl \
    p7zip \
    ripgrep \
    sed \
    sudo \
    su-exec \
    tmux \
    vim \
    json-c \
    libuv \
    libwebsockets \
    libwebsockets-evlib_uv \
    libstdc++ \
    && update-ca-certificates

ARG BUILD_ARCH
ARG CODEX_VERSION=0.148.0
ARG TTYD_VERSION=1.7.7
COPY ttyd-selection-clipboard.patch /tmp/ttyd-selection-clipboard.patch
RUN apk add --no-cache --virtual .ttyd-build-deps \
        build-base \
        cmake \
        json-c-dev \
        libuv-dev \
        libwebsockets-dev \
        libwebsockets-evlib_uv \
        linux-headers \
        openssl-dev \
        pkgconf \
        zlib-dev \
    && mkdir -p /tmp/ttyd-build \
    && curl -fsSL "https://github.com/tsl0922/ttyd/archive/refs/tags/${TTYD_VERSION}.tar.gz" \
        | tar -xz -C /tmp/ttyd-build --strip-components=1 \
    && patch -d /tmp/ttyd-build -p1 < /tmp/ttyd-selection-clipboard.patch \
    && cd /tmp/ttyd-build/html \
    && npm install --global corepack@0.31.0 \
    && corepack enable \
    && yarn install --immutable \
    && yarn inline \
    && cd /tmp/ttyd-build \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --parallel 2 \
    && install -m 0755 build/ttyd /usr/bin/ttyd \
    && rm -rf /tmp/ttyd-build /tmp/ttyd-selection-clipboard.patch \
    && apk del .ttyd-build-deps

RUN NPM_CONFIG_CACHE=/tmp/npm-cache npm install -g @openai/codex@${CODEX_VERSION} \
    && codex --version \
    && rm -rf /tmp/npm-cache

RUN pip3 install --no-cache-dir --break-system-packages hass-mcp

RUN case "${BUILD_ARCH}" in \
        amd64) HA_ARCH="amd64" ;; \
        aarch64) HA_ARCH="aarch64" ;; \
        *) HA_ARCH="amd64" ;; \
    esac && \
    curl -fsSL "https://github.com/home-assistant/cli/releases/latest/download/ha_${HA_ARCH}" -o /usr/local/bin/ha && \
    chmod +x /usr/local/bin/ha

RUN adduser -D -H -u 22000 -G root codex && \
    mkdir -p \
    /data/codex-home \
    /data/codex-managed \
    /homeassistant \
    /root/.local/bin

COPY rootfs/ /

RUN chmod +x \
    /usr/local/bin/hass-mcp-wrapper \
    /usr/local/bin/hass-mcp-root-helper \
    /usr/local/bin/codex-merge-config \
    /usr/local/bin/codex-shell \
    /usr/local/bin/codex-session \
    /usr/local/bin/codex-start \
    && chmod 440 /etc/sudoers.d/codex-hass-mcp

RUN cat > /etc/tmux.conf << 'EOF'
set -g history-limit 5000
set -ga terminal-overrides ',xterm*:smcup@:rmcup@'
set -g mouse on
set -g xterm-keys on
set -s set-clipboard on
set -g allow-passthrough on
bind -n WheelUpPane if-shell -F -t = "#{mouse_any_flag}" "send-keys -M" "if -Ft= '#{pane_in_mode}' 'send-keys -M' 'select-pane -t=; copy-mode -e; send-keys -M'"
bind -n WheelDownPane select-pane -t= \; send-keys -M
EOF

RUN ln -sf /etc/tmux.conf /root/.tmux.conf

RUN cat > /etc/codex.bashrc << 'EOF'
export TERM=xterm-256color
export LANG=C.UTF-8
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PS1='\[\033[1;36m\]codex\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]\$ '

alias ll='ls -la'
alias ha-config='cd /homeassistant'
alias ha-logs='cat /homeassistant/home-assistant.log 2>/dev/null || echo "Log not found"'
EOF

RUN echo 'source /etc/codex.bashrc' > /root/.profile

ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /homeassistant

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -sf http://localhost:7681/ >/dev/null || exit 1

ENTRYPOINT []
CMD ["/usr/local/bin/codex-start"]
