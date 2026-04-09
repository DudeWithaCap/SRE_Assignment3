const endpoints = {
  success: "/api/payments/success",
  fail: "/api/payments/fail",
  slow: "/api/payments/slow",
};

const lastResultEl = document.getElementById("last-result");
const logEl = document.getElementById("log");
const btnStart = document.getElementById("btn-start");
const btnStop = document.getElementById("btn-stop");
const btnSuccess = document.getElementById("btn-success");
const btnFail = document.getElementById("btn-fail");
const btnSlow = document.getElementById("btn-slow");

let simTimer = null;
let busy = false;

const SIM_INTERVAL_MS = 2500;

function appendLog(line, kind) {
  const li = document.createElement("li");
  li.textContent = line;
  if (kind === "ok") li.classList.add("ok");
  if (kind === "err") li.classList.add("err");
  logEl.insertBefore(li, logEl.firstChild);
  while (logEl.children.length > 80) {
    logEl.removeChild(logEl.lastChild);
  }
}

async function callPayment(url, label) {
  const t0 = performance.now();
  try {
    const res = await fetch(url, { method: "POST" });
    const text = await res.text();
    let body;
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
    const ms = Math.round(performance.now() - t0);
    const summary = {
      label,
      httpStatus: res.status,
      clientLatencyMs: ms,
      body,
    };
    lastResultEl.textContent = JSON.stringify(summary, null, 2);
    const ok = res.ok;
    appendLog(
      `[${new Date().toLocaleTimeString()}] ${label} → ${res.status} (${ms} ms)`,
      ok ? "ok" : "err",
    );
    return summary;
  } catch (e) {
    const ms = Math.round(performance.now() - t0);
    const msg = e instanceof Error ? e.message : String(e);
    lastResultEl.textContent = JSON.stringify(
      { label, error: msg, clientLatencyMs: ms },
      null,
      2,
    );
    appendLog(`[${new Date().toLocaleTimeString()}] ${label} → network error: ${msg}`, "err");
    throw e;
  }
}

async function randomSimulatedCall() {
  if (busy) return;
  busy = true;
  const r = Math.random();
  const url = r < 0.5 ? endpoints.success : r < 0.8 ? endpoints.fail : endpoints.slow;
  const label = url === endpoints.success ? "sim:success" : url === endpoints.fail ? "sim:fail" : "sim:slow";
  try {
    await callPayment(url, label);
  } finally {
    busy = false;
  }
}

function startSimulation() {
  if (simTimer != null) return;
  btnStart.disabled = true;
  btnStop.disabled = false;
  appendLog(`[${new Date().toLocaleTimeString()}] Simulation started`, "ok");
  simTimer = setInterval(randomSimulatedCall, SIM_INTERVAL_MS);
  randomSimulatedCall();
}

function stopSimulation() {
  if (simTimer != null) {
    clearInterval(simTimer);
    simTimer = null;
  }
  btnStart.disabled = false;
  btnStop.disabled = true;
  appendLog(`[${new Date().toLocaleTimeString()}] Simulation stopped`, "ok");
}

btnStart.addEventListener("click", startSimulation);
btnStop.addEventListener("click", stopSimulation);
btnSuccess.addEventListener("click", () => callPayment(endpoints.success, "manual:success"));
btnFail.addEventListener("click", () => callPayment(endpoints.fail, "manual:fail"));
btnSlow.addEventListener("click", () => callPayment(endpoints.slow, "manual:slow"));
