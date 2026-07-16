<#
Thin wrapper around Windows Credential Manager (advapi32 CredWrite/CredRead/
CredDelete) for storing a single generic secret. This is the actual OS
keyring on Windows -- the same backing store python-keyring's wincred
backend would use -- reached here via P/Invoke instead of a Python
dependency, since no Python runtime is installed in this environment.

Secret material is never accepted as a command-line argument (visible in
process listings / shell history) -- Write reads it from stdin.
#>
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("Write", "Read", "Delete")]
  [string]$Action,

  [Parameter(Mandatory = $true)]
  [string]$Target
)

$ErrorActionPreference = "Stop"

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

namespace SunoCred
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct CREDENTIAL
    {
        public uint Flags;
        public uint Type;
        public string TargetName;
        public string Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public uint CredentialBlobSize;
        public IntPtr CredentialBlob;
        public uint Persist;
        public uint AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    public static class Native
    {
        [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern bool CredWrite([In] ref CREDENTIAL userCredential, [In] uint flags);

        [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern bool CredRead(string target, uint type, uint reservedFlag, out IntPtr credentialPtr);

        [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern bool CredDelete(string target, uint type, uint flags);

        [DllImport("advapi32.dll", SetLastError = true)]
        public static extern void CredFree([In] IntPtr cred);
    }
}
"@

$CRED_PERSIST_LOCAL_MACHINE = 2

switch ($Action) {
  "Write" {
    $secret = [Console]::In.ReadToEnd().TrimEnd("`r", "`n")
    if ([string]::IsNullOrEmpty($secret)) { throw "No secret provided on stdin." }
    $bytes = [System.Text.Encoding]::Unicode.GetBytes($secret)
    $blob = [Runtime.InteropServices.Marshal]::AllocHGlobal($bytes.Length)
    try {
      [Runtime.InteropServices.Marshal]::Copy($bytes, 0, $blob, $bytes.Length)
      $cred = New-Object SunoCred.CREDENTIAL
      $cred.Type = 1
      $cred.TargetName = $Target
      $cred.CredentialBlobSize = [uint32]$bytes.Length
      $cred.CredentialBlob = $blob
      $cred.Persist = $CRED_PERSIST_LOCAL_MACHINE
      $cred.UserName = $env:USERNAME
      $ok = [SunoCred.Native]::CredWrite([ref]$cred, 0)
      if (-not $ok) { throw "CredWrite failed: Win32 error $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
      Write-Host "Stored under target '$Target'."
    } finally {
      [Runtime.InteropServices.Marshal]::FreeHGlobal($blob)
      [Array]::Clear($bytes, 0, $bytes.Length)
    }
  }
  "Read" {
    $ptr = [IntPtr]::Zero
    $ok = [SunoCred.Native]::CredRead($Target, 1, 0, [ref]$ptr)
    if (-not $ok) { throw "CredRead failed (not found?): Win32 error $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
    try {
      $cred = [Runtime.InteropServices.Marshal]::PtrToStructure($ptr, [Type][SunoCred.CREDENTIAL])
      $bytes = New-Object byte[] $cred.CredentialBlobSize
      [Runtime.InteropServices.Marshal]::Copy($cred.CredentialBlob, $bytes, 0, $cred.CredentialBlobSize)
      [Console]::Out.Write([System.Text.Encoding]::Unicode.GetString($bytes))
    } finally {
      [SunoCred.Native]::CredFree($ptr)
    }
  }
  "Delete" {
    $ok = [SunoCred.Native]::CredDelete($Target, 1, 0)
    if (-not $ok) { throw "CredDelete failed: Win32 error $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
    Write-Host "Deleted target '$Target'."
  }
}
