// Polls GET /api/board/ every 5 seconds. Every fetch gets a timeout, an
// error state (shown without tearing down the last-known-good table), and
// an empty state — and a stale indicator flips on if polling has been
// failing for more than 15 seconds straight.

const POLL_INTERVAL_MS = 5000;
const FETCH_TIMEOUT_MS = 5000;
const STALE_AFTER_MS = 15000;

let elements = {};
let lastSuccessAt = null;

export function initBoard() {
    elements = {
        body: document.getElementById("board-body"),
        empty: document.getElementById("board-empty"),
        error: document.getElementById("board-error"),
        stale: document.getElementById("stale-indicator"),
        generatedAt: document.getElementById("generated-at"),
    };

    poll();
    setInterval(poll, POLL_INTERVAL_MS);
    setInterval(updateStaleIndicator, 1000);
}

async function poll() {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    try {
        const response = await fetch("/api/board/", {signal: controller.signal});
        if (!response.ok) {
            throw new Error(`board request failed with status ${response.status}`);
        }
        const data = await response.json();
        render(data);
        lastSuccessAt = Date.now();
        elements.error.hidden = true;
    } catch (error) {
        elements.error.hidden = false;
        elements.error.textContent = "Couldn't reach the server. Retrying...";
    } finally {
        clearTimeout(timeout);
    }
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
    if (lastSuccessAt === null) {
        return;
    }
    elements.stale.hidden = Date.now() - lastSuccessAt <= STALE_AFTER_MS;
}

function formatTime(iso) {
    return new Date(iso).toLocaleString();
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}
