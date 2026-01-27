function log(msg) {
  const el = document.getElementById("log");
  const now = new Date().toLocaleTimeString();
  if (el.textContent === "(nothing yet)") el.textContent = "";
  el.textContent += `[${now}] ${msg}\n`;
  el.scrollTop = el.scrollHeight;
}

async function checkStatus() {
  try {
    const res = await fetch("/status");
    const data = await res.json();
    log("Server status: " + JSON.stringify(data));
  } catch (e) {
    log("Error calling /status: " + e);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btnCheckStatus").addEventListener("click", checkStatus);
});
