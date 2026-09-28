// Detects a hardware barcode-scanner burst (fast keydown events terminated
// by Enter) versus ordinary human typing, without anything needing focus.
// A scan is a run of keys with under 30ms between each, ended by Enter.

const MAX_INTER_KEY_MS = 30;

export function onScan(callback) {
    let buffer = "";
    let lastKeyTime = 0;

    document.addEventListener("keydown", (event) => {
        if (isTypingIntoField(event.target)) {
            return;
        }

        const now = performance.now();
        const gap = now - lastKeyTime;
        lastKeyTime = now;

        if (event.key === "Enter") {
            if (buffer.length > 0 && gap <= MAX_INTER_KEY_MS) {
                callback(buffer);
            }
            buffer = "";
            return;
        }

        if (event.key.length !== 1) {
            // Ignore Shift/Tab/arrow keys etc — not part of a scan payload,
            // and they'd otherwise reset the burst on every keystroke.
            return;
        }

        if (gap > MAX_INTER_KEY_MS) {
            buffer = ""; // gap too large: this starts a new (likely human) burst
        }
        buffer += event.key;
    });
}

function isTypingIntoField(target) {
    if (!target || !target.tagName) {
        return false;
    }
    return target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
}
