/* ============================================================
   NEXUS Corp CTF — Client-side interactions
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {

    // ── Flag Submission ────────────────────────────────────
    document.querySelectorAll(".flag-form").forEach(form => {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const data = new FormData(form);
            const resultEl = form.querySelector(".flag-result") || form.nextElementSibling;

            try {
                const res = await fetch("/submit-flag", { method: "POST", body: data });
                const json = await res.json();

                if (resultEl) {
                    resultEl.textContent = json.message;
                    resultEl.className = "flag-result " +
                        (json.success ? "flag-result--success" : "flag-result--error");
                    resultEl.style.display = "block";
                }
                if (json.success) {
                    setTimeout(() => location.reload(), 1500);
                }
            } catch (err) {
                if (resultEl) {
                    resultEl.textContent = "Network error. Try again.";
                    resultEl.className = "flag-result flag-result--error";
                    resultEl.style.display = "block";
                }
            }
        });
    });

    // ── Hint System ────────────────────────────────────────
    document.querySelectorAll(".hint-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            const level = btn.dataset.level;
            const hintNum = parseInt(btn.dataset.hintNum || "0");
            try {
                const res = await fetch(`/hint/${level}/${hintNum}`);
                const json = await res.json();
                const container = btn.closest(".hint-box");
                const textEl = container.querySelector(".hint-text");
                if (json.hint) {
                    textEl.textContent = `Hint ${hintNum + 1}: ${json.hint}`;
                    textEl.style.display = "block";
                    btn.dataset.hintNum = hintNum + 1;
                    if (hintNum + 1 >= json.total) {
                        btn.disabled = true;
                        btn.textContent = "No more hints";
                    }
                } else {
                    textEl.textContent = "No more hints available.";
                    textEl.style.display = "block";
                }
            } catch {
                // ignore
            }
        });
    });

    // ── Terminal (Level 4 SSH) ──────────────────────────────
    const termInput = document.getElementById("ssh-cmd-input");
    const termBody = document.getElementById("ssh-terminal-body");

    if (termInput) {
        const cmdHistory = [];
        let historyIdx = -1;

        termInput.addEventListener("keydown", async (e) => {
            if (e.key === "ArrowUp") {
                e.preventDefault();
                if (historyIdx < cmdHistory.length - 1) {
                    historyIdx++;
                    termInput.value = cmdHistory[cmdHistory.length - 1 - historyIdx];
                }
            } else if (e.key === "ArrowDown") {
                e.preventDefault();
                if (historyIdx > 0) {
                    historyIdx--;
                    termInput.value = cmdHistory[cmdHistory.length - 1 - historyIdx];
                } else {
                    historyIdx = -1;
                    termInput.value = "";
                }
            }

            if (e.key !== "Enter") return;
            const cmd = termInput.value.trim();
            if (!cmd) return;

            cmdHistory.push(cmd);
            historyIdx = -1;
            termInput.value = "";

            // Show typed command
            appendTerminal(`sysop@nexus-internal-srv:~$ ${cmd}`, "cmd");

            try {
                const data = new FormData();
                data.set("command", cmd);
                const res = await fetch("/level/4/cmd", { method: "POST", body: data });
                const json = await res.json();

                if (json.output === "__CLEAR__") {
                    termBody.innerHTML = "";
                } else {
                    appendTerminal(json.output, "output");
                }
            } catch {
                appendTerminal("Error: connection lost", "error");
            }
        });
    }

    function appendTerminal(text, type) {
        if (!termBody) return;
        const line = document.createElement("div");
        line.style.marginBottom = "2px";
        if (type === "cmd") {
            line.style.color = "#00f0ff";
        } else if (type === "error") {
            line.style.color = "#ff2d55";
        } else {
            line.style.color = "#00ff88";
        }
        const pre = document.createElement("pre");
        pre.textContent = text;
        pre.style.margin = "0";
        pre.style.whiteSpace = "pre-wrap";
        pre.style.wordBreak = "break-all";
        line.appendChild(pre);
        termBody.appendChild(line);
        termBody.scrollTop = termBody.scrollHeight;
    }

    // ── Challenges page progress bar ────────────────────────
    const progressBar = document.getElementById("dash-progress");
    if (progressBar) {
        progressBar.style.width = progressBar.dataset.pct + "%";
    }

    // ── Auto-dismiss flash messages ────────────────────────
    document.querySelectorAll(".flash").forEach(el => {
        setTimeout(() => {
            el.style.opacity = "0";
            el.style.transform = "translateY(-8px)";
            el.style.transition = "all 0.3s";
            setTimeout(() => el.remove(), 300);
        }, 5000);
    });

});
