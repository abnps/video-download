export const NATIVE_HOST = "io.github.abnps.videodownload";
export const LEGACY_NATIVE_HOST = "com.videodl.bridge";

function hostNotFound(message) {
  return /(?:native messaging host|native application|native host).*(?:not found|does not exist|not installed|no such)|(?:not found|no such).*(?:native messaging host|native application|native host)/i.test(message);
}

export async function sendNative(message, runtime = chrome.runtime) {
  const call = (host) => new Promise((resolve) => {
    runtime.sendNativeMessage(host, message, (reply) => {
      resolve({ reply, failure: runtime.lastError?.message || "" });
    });
  });

  let result = await call(NATIVE_HOST);
  if (hostNotFound(result.failure)) result = await call(LEGACY_NATIVE_HOST);
  if (result.failure) {
    // Stari program može prepoznati staro ime, ali odbiti novi ID dodatka.
    const code = /forbidden/i.test(result.failure) ? "app-outdated"
      : hostNotFound(result.failure) ? "not-connected" : "connection";
    return code === "connection" ? { ok: false, code, detail: result.failure } : { ok: false, code };
  }
  return result.reply || { ok: false, code: "no-reply" };
}
