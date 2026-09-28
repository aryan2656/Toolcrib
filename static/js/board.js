// Live board updates over a WebSocket (Django Channels + Redis channel
// layer), not polling: the server pushes a fresh board_state() on every
// checkout/return via crib/services.py::_notify_board_update(). Still
// gets everything a polling loop would need for resilience — a timeout
// on the connection attempt has no meaning for WebSockets, so instead:
// automatic reconnection with capped exponential backoff, a ping/pong
// keep-alive so a half-dead connection is caught quickly, and a stale
// indicator if no message (data or pong) has arrived in 15 seconds.

const STALE_AFTER_MS = 15000;
const PING_INTERVAL_MS = 10000;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 10000;

let elements = {};
let socket = null;
let reconnectAttempt = 0;
let reconnectTimer = null;
let pingTimer = null;
let lastMessageAt = null;

// The browser's own connectivity signal fires the moment the OS reports the
// network is back — don't make the operator wait out the backoff timer.
window.addEventListener("online", () => {
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
        return;
    }
    clearTimeout(reconnectTimer);
    connect();
});

export function initBoard() {
    elements = {
        body: document.getElementById("board-body"),
        empty: document.getElementById("board-empty"),
        error: document.getElementById("board-error"),
        stale: document.getElementById("stale-indicator"),
        generatedAt: document.getElementById("generated-at"),
    };

    connect();
    setInterval(updateStaleIndicator, 1000);
}

function connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${protocol}//${window.location.host}/ws/board/`);

    socket.addEventListener("open", () => {
        reconnectAttempt = 0;
        elements.error.hidden = true;
        pingTimer = setInterval(sendPing, PING_INTERVAL_MS);
    });

    socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        lastMessageAt = Date.now();
        if (payload.type === "board_state") {
            render(payload);
            elements.error.hidden = true;
        }
        // "pong" needs no handling beyond the lastMessageAt update above —
        // it exists purely to prove the connection is still alive.
    });

    socket.addEventListener("close", scheduleReconnect);
    socket.addEventListener("error", () => socket.close());
}

function sendPing() {
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({type: "ping"}));
    }
}

function scheduleReconnect() {
    clearInterval(pingTimer);
    elements.error.hidden = false;
    elements.error.textContent = "Connection lost. Reconnecting...";

    const delay = Math.min(RECONNECT_BASE_MS * 2 ** reconnectAttempt, RECONNECT_MAX_MS);
    reconnectAttempt += 1;
    reconnectTimer = setTimeout(connect, delay);
}

function render(data) {
    elements.generatedAt.textContent = `Last updated: ${new Date(data.generated_at).toLocaleTimeString()}`;

    if (data.tools.length === 0) {
        elements.empty.hidden = false;
        elements.body.innerHTML = "";
        return;
    }
    elements.empty.hidden = true;

    elements.body.innerHTML = data.tools.map((row) => `
        <tr class="${row.overdue ? "table-danger" : ""}">
            <td>${escapeHtml(row.asset_tag)}</td>
            <td>${escapeHtml(row.description)}</td>
            <td>${escapeHtml(row.holder_name)}</td>
            <td>${formatTime(row.checked_out_at)}</td>
            <td>${formatTime(row.due_back_at)}</td>
            <td>${row.overdue
        ? '<span class="badge text-bg-danger">Overdue</span>'
        : '<span class="badge text-bg-success">On time</span>'}</td>
        </tr>
    `).join("");
}

function updateStaleIndicator() {
    if (lastMessageAt === null) {
        return;
    }
    elements.stale.hidden = Date.now() - lastMessageAt <= STALE_AFTER_MS;
}

function formatTime(iso) {
    return new Date(iso).toLocaleString();
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}
