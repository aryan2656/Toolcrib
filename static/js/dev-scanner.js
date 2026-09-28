// DEBUG-only: dispatches synthetic keydown events (15ms gaps, trailing
// Enter) so the terminal can be exercised without real scanner hardware —
// indistinguishable from a real scan to scanner.js.

const PRESETS = [
    {label: "Valid badge", value: "E-1001"},
    {label: "Valid tool (free)", value: "T-0015"},
    {label: "Tool held by other", value: "T-0004"},
    {label: "Unknown tag", value: "T-9999"},
    {label: "Calibration-overdue tool", value: "T-0001"},
];

export function initDevScanner(container) {
    if (!container) {
        return;
    }

    const panel = document.createElement("div");
    panel.className = "card shadow-sm";
    panel.innerHTML = '<div class="card-header small text-secondary">Dev scanner (DEBUG only)</div>' +
        '<div class="card-body d-flex flex-column gap-2 p-2"></div>';

    const body = panel.querySelector(".card-body");
    for (const preset of PRESETS) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-outline-secondary btn-sm";
        button.textContent = preset.label;
        button.addEventListener("click", () => simulateScan(preset.value));
        body.appendChild(button);
    }

    container.appendChild(panel);
}

async function simulateScan(value) {
    for (const key of value) {
        dispatchKey(key);
        await sleep(15);
    }
    dispatchKey("Enter");
}

function dispatchKey(key) {
    document.dispatchEvent(new KeyboardEvent("keydown", {key, bubbles: true}));
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
