import assert from "node:assert/strict";
import { test } from "node:test";

import { LEGACY_NATIVE_HOST, NATIVE_HOST, sendNative } from "../../extension/native.js";

function runtimeWith(answers) {
  const calls = [];
  const runtime = {
    lastError: null,
    sendNativeMessage(host, message, callback) {
      calls.push({ host, message });
      const answer = answers[host];
      this.lastError = answer?.error ? { message: answer.error } : null;
      callback(answer?.reply);
      this.lastError = null;
    },
  };
  return { runtime, calls };
}

test("novo ime radi bez pokušaja starog", async () => {
  const { runtime, calls } = runtimeWith({ [NATIVE_HOST]: { reply: { ok: true } } });
  assert.deepEqual(await sendNative({ action: "status" }, runtime), { ok: true });
  assert.deepEqual(calls.map((call) => call.host), [NATIVE_HOST]);
});

test("staro ime se koristi samo kada novo nije pronađeno", async () => {
  const { runtime, calls } = runtimeWith({
    [NATIVE_HOST]: { error: "Specified native messaging host not found." },
    [LEGACY_NATIVE_HOST]: { reply: { ok: true, running: true } },
  });
  assert.deepEqual(await sendNative({ action: "status" }, runtime), { ok: true, running: true });
  assert.deepEqual(calls.map((call) => call.host), [NATIVE_HOST, LEGACY_NATIVE_HOST]);
});

test("Firefoxova poruka o nepostojećoj aplikaciji pokreće povratak na staro ime", async () => {
  const { runtime, calls } = runtimeWith({
    [NATIVE_HOST]: { error: `No such native application ${NATIVE_HOST}` },
    [LEGACY_NATIVE_HOST]: { reply: { ok: true } },
  });
  assert.deepEqual(await sendNative({ action: "status" }, runtime), { ok: true });
  assert.equal(calls.length, 2);
});

test("odbijen host ili neuspjela veza ne pokreću staro ime", async () => {
  for (const error of ["Access to the specified native messaging host is forbidden.", "Native host has exited."]) {
    const { runtime, calls } = runtimeWith({ [NATIVE_HOST]: { error } });
    const result = await sendNative({ action: "status" }, runtime);
    assert.equal(result.code, error.includes("forbidden") ? "app-outdated" : "connection");
    assert.equal(calls.length, 1);
  }
});

test("oba nepostojeća hosta daju poruku o nepovezanom programu", async () => {
  const { runtime, calls } = runtimeWith({
    [NATIVE_HOST]: { error: "Specified native messaging host not found." },
    [LEGACY_NATIVE_HOST]: { error: "Specified native messaging host not found." },
  });
  assert.deepEqual(await sendNative({ action: "status" }, runtime), { ok: false, code: "not-connected" });
  assert.equal(calls.length, 2);
});
