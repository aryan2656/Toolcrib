import {onScan} from "./scanner.js";

const IDLE_TIMEOUT_MS = 10000;
const RESULT_DISPLAY_MS = 3000;
const SCAN_TIMEOUT_MS = 5000;

const STATE = {
    AWAITING_BADGE: "AWAITING_BADGE",
    AWAITING_TOOL: "AWAITING_TOOL",
    RESULT: "RESULT",
};

let state = STATE.AWAITING_BADGE;
let badge = null;
let resetTimer = null;
let elements = {};

export function initTerminal() {
    elements = {
        statusText: document.getElementById("status-text"),
        employeeLine: document.getElementById("employee-name"),
        resultBanner: document.getElementById("result-banner"),
        manualForm: document.getElementById("manual-entry-form"),
        manualInput: document.getElementById("manual-entry-input"),
    };

    enterAwaitingBadge();
    onScan((value) => handleScan(value.trim().toUpperCase()));

    elements.manualForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const value = elements.manualInput.value.trim().toUpperCase();
        elements.manualInput.value = "";
        if (value) {
            handleScan(value);
        }
    });
}

function handleScan(value) {
    if (state === STATE.RESULT) {
        // Any scan during RESULT interrupts the auto-reset and is handled
        // immediately, as though we'd already returned to AWAITING_BADGE.
        enterAwaitingBadge();
    }

    if (state === STATE.AWAITING_BADGE) {
        if (value.startsWith("E-")) {
            badge = value;
            enterAwaitingTool();
        } else if (value.startsWith("T-")) {
            setStatus("Scan your badge first");
        }
        return;
    }

    if (state === STATE.AWAITING_TOOL) {
        if (value.startsWith("E-")) {
            badge = value;
            enterAwaitingTool(); // replaces badge, refreshes idle timer
        } else if (value.startsWith("T-")) {
            submitScan(badge, value);
        }
    }
}

function enterAwaitingBadge() {
    clearTimeout(resetTimer);
    state = STATE.AWAITING_BADGE;
    badge = null;
    setStatus("Scan your badge");
    elements.employeeLine.hidden = true;
    hideBanner();
}

function enterAwaitingTool() {
    clearTimeout(resetTimer);
    state = STATE.AWAITING_TOOL;
    setStatus("Scan the tool");
    elements.employeeLine.hidden = false;
    elements.employeeLine.textContent = `Badge: ${badge}`;
    hideBanner();
    resetTimer = setTimeout(enterAwaitingBadge, IDLE_TIMEOUT_MS);
}

function enterResult(message, variant) {
    clearTimeout(resetTimer);
    state = STATE.RESULT;
    setStatus(message);
    elements.resultBanner.className = `alert alert-${variant} fs-4`;
    elements.resultBanner.textContent = message;
    resetTimer = setTimeout(enterAwaitingBadge, RESULT_DISPLAY_MS);
}

function setStatus(text) {
    elements.statusText.textContent = text;
}

function hideBanner() {
    elements.resultBanner.className = "d-none";
    elements.resultBanner.textContent = "";
}

async function submitScan(scannedBadge, assetTag) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), SCAN_TIMEOUT_MS);

    try {
        const response = await fetch("/api/scan/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({badge: scannedBadge, asset_tag: assetTag}),
            signal: controller.signal,
        });
        const data = await response.json();

        if (!response.ok) {
            enterResult(data.message || "Something went wrong.", "danger");
            return;
        }

        if (data.action === "checked_out") {
            enterResult(`Checked out to ${data.employee.name}`, "success");
        } else {
            enterResult(`Returned (${data.duration_minutes} min)`, "primary");
        }
    } catch (error) {
        enterResult("Network error — scan not recorded. Try again.", "danger");
    } finally {
        clearTimeout(timeout);
    }
}

function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
}
