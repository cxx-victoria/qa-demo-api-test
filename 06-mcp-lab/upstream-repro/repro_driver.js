/**
 * 复现驱动器：用"真实的操作系统管道"启动 Inspector CLI，读到第一块数据后立刻关闭读端。
 * 这等价于 issue 里说的 `mcp-inspector --cli ... | head -n 5` —— 下游提前退出会关掉管道。
 *
 * 为什么要用这个脚本，而不是直接在 PowerShell 里写 `| head`：
 *   PowerShell 的管道是"文本管道"，PowerShell 自己会把上游输出全部读走，
 *   下游提前退出并不会关闭上游进程的管道，所以复现不出来。
 *   本脚本用 child_process.spawn 直接建立 OS 级管道，才能真实触发 EPIPE。
 *
 * 用法（在 upstream-repro 目录下）：
 *   node repro_driver.js                 # 512KB 响应（预期复现 EPIPE 崩溃）
 *   $env:REPRO_SIZE_KB=8; node repro_driver.js   # 8KB 响应（预期的对照组：不崩溃）
 */
const { spawn, execSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const SIZE_KB = process.env.REPRO_SIZE_KB || "512";
const ARGS = [
  "--cli", "python", "big_server.py",
  "--method", "tools/call",
  "--tool-name", "blob",
  "--tool-arg", `size_kb=${SIZE_KB}`,
  "--format", "json",
];

/** 定位 Inspector 的入口 js：优先用 npm 缓存里已下载好的那份（离线可用），否则退回 npx。 */
function resolveInspector() {
  if (process.env.MCP_CLI) return { cmd: process.execPath, pre: [process.env.MCP_CLI] };
  try {
    const cache = execSync("npm config get cache", { encoding: "utf8" }).trim();
    const npxDir = path.join(cache, "_npx");
    for (const d of fs.readdirSync(npxDir)) {
      const entry = path.join(npxDir, d, "node_modules", "@modelcontextprotocol",
                              "inspector", "clients", "launcher", "build", "index.js");
      if (fs.existsSync(entry)) return { cmd: process.execPath, pre: [entry] };
    }
  } catch {
    /* 找不到缓存就继续往下走 */
  }
  console.log("[提示] 未找到本地缓存，改用 npx 启动（需要网络）");
  return { cmd: process.platform === "win32" ? "npx.cmd" : "npx",
           pre: ["-y", "@modelcontextprotocol/inspector"] };
}

const { cmd, pre } = resolveInspector();
console.log(`[执行] ${cmd} ${[...pre, ...ARGS].join(" ")}\n`);

const child = spawn(cmd, [...pre, ...ARGS], { stdio: ["ignore", "pipe", "pipe"] });

let received = 0;
let closed = false;
let stderr = "";

child.stdout.on("data", (chunk) => {
  received += chunk.length;
  if (!closed) {
    closed = true;
    child.stdout.destroy();     // ← 关键动作：提前关闭管道读端，模拟 head/grep/less 提前退出
  }
});
child.stderr.on("data", (chunk) => (stderr += chunk.toString()));
child.on("error", (e) => {
  console.log("启动失败：" + e.message);
});

child.on("exit", (code, signal) => {
  const crashed = /EPIPE/.test(stderr);
  console.log("=========== 复现结果 ===========");
  console.log("被测响应大小      : " + SIZE_KB + " KB");
  console.log("退出码            : " + code);
  console.log("信号              : " + signal);
  console.log("关闭前读到字节数  : " + received + "  （Windows 管道缓冲区 = 65536）");
  console.log("stderr 是否含 EPIPE: " + (crashed ? "是 → 复现成功" : "否 → 未复现"));
  if (stderr.trim()) {
    console.log("\n--------- stderr 原文 ---------");
    console.log(stderr.trim());
  }
});
