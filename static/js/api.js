// Shared fetch wrapper for the scan endpoint: every call gets a 5-second
// timeout, and a failure that isn't a real server response (offline, DNS,
// timeout) is queued and retried automatically — a dropped scan is worse
// than a visible error, so a scan is never silently lost.

const SCAN_TIMEOUT_MS = 5000;
const RETRY_INTERVAL_MS = 10000;

const queue = [];
const queueListeners = new Set();

window.addEventListener("online", () => {
    retryQueue();
});
setInterval(retryQueue, RETRY_INTERVAL_MS);

export function onQueueChange(listener) {
    queueListeners.add(listener);
    listener(queue.length);
}

function notifyQueueChange() {
    for (const listener of queueListeners) {
        listener(queue.length);
    }
}

export async function submitScan(badge, assetTag) {
    try {
        return await postScan(badge, assetTag);
    } catch (error) {
        // Network-level failure (offline, DNS, timeout) — not a real
        // response from the server, so this scan can't be shown a result
        // yet. Queue it instead of dropping it.
        queue.push({badge, assetTag});
        notifyQueueChange();
        return {queued: true, queueDepth: queue.length};
    }
}

async function postScan(badge, assetTag) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), SCAN_TIMEOUT_MS);

    try {
        const response = await fetch("/api/scan/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({badge, asset_tag: assetTag}),
            signal: controller.signal,
        });
        const data = await response.json();
        return {queued: false, ok: response.ok, status: response.status, data};
    } finally {
        clearTimeout(timeout);
    }
}

async function retryQueue() {
    while (queue.length > 0) {
        const next = queue[0];
        try {
            await postScan(next.badge, next.assetTag);
            queue.shift();
            notifyQueueChange();
        } catch (error) {
            break; // still unreachable; stop and try again on the next tick
        }
    }
}

function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
}
