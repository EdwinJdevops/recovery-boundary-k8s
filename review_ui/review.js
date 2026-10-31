"use strict";
const el = id => document.getElementById(id);
let loaded = null;
const invalidate = () => { loaded = null; el("approve").disabled = true; el("revoke").hidden = true; el("confirm").checked = false; el("review").hidden = true; };
for (const id of ["review-id", "token"]) el(id).addEventListener("input", invalidate);
el("confirm").addEventListener("change", () => { el("approve").disabled = !loaded || !el("confirm").checked || loaded.status !== "PENDING"; });
async function request(path, options = {}) {
  const response = await fetch(path, { ...options, cache: "no-store", credentials: "omit", headers: {"Authorization": "Bearer " + el("token").value, ...options.headers} });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || "Review unavailable");
  return value;
}
el("load").addEventListener("click", async () => {
  invalidate();
  const id = el("review-id").value;
  if (!/^[a-zA-Z0-9_-]{1,64}$/.test(id)) { el("status").textContent = "Invalid review ID"; return; }
  try {
    const value = await request("/reviews/" + id);
    if (id !== el("review-id").value) return;
    loaded = { ...value, id };
    el("revoke").hidden = !value.can_revoke;
    const s = value.snapshot, a = s.action;
    el("summary").textContent = `${a.operation}: ${a.cluster} / ${a.namespace} / ${a.name} → ${a.replicas} replicas`;
    el("expiry").textContent = "Approval expires " + new Date(s.expires_at * 1000).toISOString();
    el("snapshot").textContent = JSON.stringify(s, null, 2);
    el("digest").textContent = value.snapshot_sha256;
    el("review").hidden = false;
    el("status").textContent = value.status;
  } catch (error) { el("status").textContent = error.message; }
});
el("revoke").addEventListener("click", async () => {
  if (!loaded || loaded.status !== "APPROVED") return;
  const exact = loaded;
  el("revoke").disabled = true;
  try {
    const result = await request("/reviews/" + exact.id + "/revoke", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({snapshot_sha256:exact.snapshot_sha256})});
    invalidate();
    el("status").textContent = result.status + ". An already claimed dispatch cannot be cancelled.";
  } catch (error) { invalidate(); el("status").textContent = error.message; }
  finally { el("revoke").disabled = false; }
});
el("approve").addEventListener("click", async () => {
  if (!loaded || !el("confirm").checked) return;
  const exact = loaded;
  el("approve").disabled = true;
  try {
    const result = await request("/reviews/" + exact.id + "/approve", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({snapshot_sha256:exact.snapshot_sha256})});
    invalidate();
    el("status").textContent = result.status + " by " + result.approver + ". No write was dispatched.";
  } catch (error) { invalidate(); el("status").textContent = error.message + ". Reload the review before trying again."; }
});
