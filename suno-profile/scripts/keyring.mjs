import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const CREDMGR = path.join(path.dirname(fileURLToPath(import.meta.url)), "credmgr.ps1");

function run(args, input) {
  const res = spawnSync(
    "powershell",
    ["-NoProfile", "-NonInteractive", "-File", CREDMGR, ...args],
    { input, encoding: "utf8" },
  );
  if (res.status !== 0) {
    throw new Error(`credmgr.ps1 ${args.join(" ")} failed: ${res.stderr || res.stdout}`);
  }
  return res.stdout;
}

/** Store `value` under `target` in Windows Credential Manager. Never logs the value. */
export function setSecret(target, value) {
  run(["-Action", "Write", "-Target", target], value);
}

/** Read the secret stored under `target`. Throws if not found. */
export function getSecret(target) {
  return run(["-Action", "Read", "-Target", target]);
}

/** Remove the secret stored under `target`. */
export function deleteSecret(target) {
  run(["-Action", "Delete", "-Target", target]);
}
