const express = require("express");
const { spawn } = require("child_process");
const path = require("path");

const app = express();
app.use(express.json({ limit: "10mb" }));

const MCP_PATH = path.join(__dirname, "node_modules/@dymoo/media-understanding/dist/mcp.js");

async function callMcpTool(toolName, args) {
  return new Promise((resolve, reject) => {
    const proc = spawn("node", [MCP_PATH], { stdio: ["pipe", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (d) => (stdout += d.toString()));
    proc.stderr.on("data", (d) => (stderr += d.toString()));

    proc.on("close", (code) => {
      const lines = stdout.split("\n").filter((l) => l.trim());
      for (const line of lines) {
        try {
          const msg = JSON.parse(line);
          if (msg.id === 2) {
            if (msg.result) resolve(msg.result);
            else if (msg.error) reject(new Error(JSON.stringify(msg.error)));
            return;
          }
        } catch {}
      }
      reject(new Error(`MCP failed (code ${code}): ${stderr.slice(0, 300)}`));
    });

    proc.on("error", reject);

    const init = JSON.stringify({
      jsonrpc: "2.0", id: 1, method: "initialize",
      params: { protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "warroom-media", version: "1.0" } }
    });
    const call = JSON.stringify({
      jsonrpc: "2.0", id: 2, method: "tools/call",
      params: { name: toolName, arguments: args }
    });

    proc.stdin.write(init + "\n");
    proc.stdin.write(call + "\n");
    proc.stdin.end();
  });
}

app.get("/health", (req, res) => res.json({ status: "ok" }));

app.post("/analyze", async (req, res) => {
  try {
    const args = { ...req.body };
    if (!args.file_path) return res.status(400).json({ error: "file_path required" });
    // Default smaller grids for portrait video to avoid budget exceeded
    if (!args.thumb_width) args.thumb_width = 120;
    if (!args.max_grids) args.max_grids = 3;
    const result = await callMcpTool("understand_media", args);
    res.json(result);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post("/probe", async (req, res) => {
  try {
    const result = await callMcpTool("probe_media", req.body);
    res.json(result);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post("/frames", async (req, res) => {
  try {
    const result = await callMcpTool("get_frames", req.body);
    res.json(result);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post("/transcript", async (req, res) => {
  try {
    const result = await callMcpTool("get_transcript", req.body);
    res.json(result);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

const PORT = process.env.PORT || 18796;
app.listen(PORT, () => console.log(`media-understanding API on :${PORT}`));
