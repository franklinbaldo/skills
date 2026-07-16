// Shared Clerk client constants used by both login-and-capture.mjs (initial
// interactive login) and mint-bearer-token.mjs (minting a fresh Bearer JWT
// from the stored cookie). Kept in one place so a Clerk API/JS version bump
// can't be applied to one script and silently missed in the other.
export const CRED_TARGET = "suno-clerk-client-cookie";
export const CLERK_API_VERSION = "2025-11-10";
export const CLERK_JS_VERSION = "5.117.0";

export function clerkClientUrl() {
  return `https://auth.suno.com/v1/client?__clerk_api_version=${CLERK_API_VERSION}&_clerk_js_version=${CLERK_JS_VERSION}`;
}
