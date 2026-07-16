// One-shot interactive setup: launches a plain, non-automated Chrome window
// (a real chrome.exe process, not Playwright's own launcher) on a fresh
// isolated profile so Franklin can log into suno.com himself, then Playwright
// attaches to it over CDP just to watch for the session cookie. Launching
// Chrome ourselves (rather than via Playwright's launcher, which adds an
// `--enable-automation` flag that flips `navigator.webdriver`) avoids
// Google's "this browser may not be secure" OAuth block — a fingerprinting
// check unrelated to which Chrome profile is used. True default-profile
// access is still blocked by Chrome itself (confirmed separately, a hard
// restriction, not an automation-detection issue) — this uses an isolated
// profile instead, same as the original raw-CDP version of this script.
//
// The script never touches Franklin's credentials — it only watches for the
// Clerk session cookie to appear, then stores it in Windows Credential
// Manager and closes the window.
//
// Usage: node scripts/login-and-capture.mjs
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { setSecret } from "./keyring.mjs";

const CRED_TARGET = "suno-clerk-client-cookie";
const PROFILE_DIR = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  ".chrome-login-profile",
);
const CDP_PORT = 9222;
const CDP_URL = `http://localhost:${CDP_PORT}`;
const POLL_MS = 2000;
const TIMEOUT_MS = 5 * 60 * 1000;
const CLERK_API_VERSION = "2025-11-10";
const CLERK_JS_VERSION = "5.117.0";

const CHROME_CANDIDATES = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
];

async function findChrome() {
  const { access } = await import("node:fs/promises");
  for (const candidate of CHROME_CANDIDATES) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      // try next
    }
  }
  throw new Error(`No Chrome executable found in: ${CHROME_CANDIDATES.join(", ")}`);
}

async function waitForCdpReady(deadline) {
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${CDP_URL}/json/version`);
      if (res.ok) return;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error("Chrome's remote debugging port never came up.");
}

// Clerk sets a `__client` cookie for anonymous visitors too (it identifies
// the device/browser, not the login) — its mere presence is not proof of a
// logged-in session. Poll the actual Clerk client endpoint (via the
// context's request API, which reuses the browser's cookies automatically)
// until it reports a session with a signed-in user.
async function waitForAuthenticatedSession(context, deadline) {
  while (Date.now() < deadline) {
    const cookies = await context.cookies("https://auth.suno.com");
    const cookie = cookies.find((c) => c.name === "__client");
    if (cookie) {
      const res = await context.request.get(
        `https://auth.suno.com/v1/client?__clerk_api_version=${CLERK_API_VERSION}&_clerk_js_version=${CLERK_JS_VERSION}`,
      );
      if (res.ok()) {
        const body = await res.json();
        const session = body?.response?.sessions?.[0];
        if (session?.status === "active" && session?.user?.id) {
          return cookie;
        }
      }
    }
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
  return null;
}

export async function loginAndCapture() {
  const chromePath = await findChrome();
  const chromeProcess = spawn(
    chromePath,
    [
      `--remote-debugging-port=${CDP_PORT}`,
      `--user-data-dir=${PROFILE_DIR}`,
      "--no-first-run",
      "--no-default-browser-check",
      "https://suno.com",
    ],
    { stdio: "ignore", detached: true },
  );
  chromeProcess.unref();

  let browser;
  try {
    await waitForCdpReady(Date.now() + 15_000);
    browser = await chromium.connectOverCDP(CDP_URL);
    const context = browser.contexts()[0];

    console.log(
      "Log in to Suno in the window that just opened — this script never " +
        "sees your password. Waiting for login (up to 5 minutes)...",
    );

    const cookie = await waitForAuthenticatedSession(context, Date.now() + TIMEOUT_MS);

    if (!cookie) {
      throw new Error(
        "Timed out waiting for login — no authenticated session detected within 5 minutes.",
      );
    }

    setSecret(CRED_TARGET, cookie.value);
    return cookie.value.length;
  } finally {
    if (browser) await browser.close().catch(() => {});
    // connectOverCDP's close() only disconnects, it doesn't terminate a
    // browser Playwright didn't launch — kill the whole process tree
    // (chrome.exe spawns child renderer processes) explicitly.
    if (chromeProcess.pid) {
      await new Promise((resolve) => {
        spawn("taskkill", ["/F", "/T", "/PID", String(chromeProcess.pid)], {
          stdio: "ignore",
        }).on("exit", resolve);
      });
    }
    // A crashpad handler process can briefly outlive the main tree and hold
    // a file lock on Windows — retry the cleanup instead of crashing on it.
    for (let attempt = 0; attempt < 5; attempt++) {
      try {
        await rm(PROFILE_DIR, { recursive: true, force: true });
        break;
      } catch (err) {
        if (attempt === 4) {
          console.warn(`Could not fully clean up ${PROFILE_DIR}: ${err.message}`);
          break;
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const len = await loginAndCapture();
  console.log(`Stored Clerk session cookie in Windows Credential Manager as '${CRED_TARGET}'.`);
  console.log(`Length: ${len} chars. Value not printed.`);
}
