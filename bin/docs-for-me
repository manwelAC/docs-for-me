#!/usr/bin/env node

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

function platformKey() {
  const platform = os.platform();
  const arch = os.arch();

  if (platform === "win32" && arch === "x64") {
    return "win32-x64";
  }

  if (platform === "darwin" && arch === "arm64") {
    return "darwin-arm64";
  }

  if (platform === "darwin" && arch === "x64") {
    return "darwin-x64";
  }

  if (platform === "linux" && arch === "x64") {
    return "linux-x64";
  }

  return `${platform}-${arch}`;
}

function executableName() {
  return os.platform() === "win32" ? "docs-for-me.exe" : "docs-for-me";
}

const packageRoot = path.resolve(__dirname, "..");
const binaryPath = path.join(packageRoot, "prebuilt", platformKey(), executableName());

if (!fs.existsSync(binaryPath)) {
  console.error("");
  console.error("docs-for-me is installed, but no bundled executable was found for this platform.");
  console.error("");
  console.error(`Expected: ${binaryPath}`);
  console.error("");
  console.error("For users, install a released npm package that includes prebuilt binaries.");
  console.error("For contributors, build one first:");
  console.error("");
  console.error("  npm run build:exe:win");
  console.error("");
  process.exit(1);
}

const result = spawnSync(binaryPath, process.argv.slice(2), {
  stdio: "inherit",
  cwd: process.cwd(),
  env: process.env,
  windowsHide: false,
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 0);
