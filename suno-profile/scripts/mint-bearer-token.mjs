// Exchanges the stored Clerk `__client` session cookie for a fresh Bearer
// JWT (valid ~1 hour) usable against studio-api-prod.suno.com's write API
// (see references/write-api.md). This is the mechanism that makes storing
// the durable cookie worthwhile: every call mints a new short-lived token
// rather than reusing one that expires mid-session.
import { pathToFileURL } from "node:url";
import { getSecret } from "./keyring.mjs";
import { CRED_TARGET, clerkClientUrl } from "./clerk-constants.mjs";

export async function mintBearerToken() {
  const cookie = getSecret(CRED_TARGET);
  const res = await fetch(clerkClientUrl(), {
    headers: { Cookie: `__client=${cookie}` },
  });
  if (!res.ok) {
    throw new Error(
      `Clerk /v1/client returned ${res.status} — stored cookie may be stale, re-run login-and-capture.mjs`,
    );
  }
  const body = await res.json();
  const session = body?.response?.sessions?.[0];
  const jwt = session?.last_active_token?.jwt;
  if (!jwt) {
    throw new Error("No active session/token in Clerk response — cookie may be invalid or expired.");
  }
  return jwt;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const jwt = await mintBearerToken();
  process.stdout.write(jwt + "\n");
}
