#!/usr/bin/env python3
"""Tiny host-side HTTP server for BT profile switching.
Listens on localhost:18797. Called by War Room frontend when conversation mode starts.
"""
import subprocess, json, os
from http.server import HTTPServer, BaseHTTPRequestHandler

XDG = f"/run/user/{os.getuid()}"

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/hfp":
            result = switch_hfp()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Silence logs

def switch_hfp():
    env = {**os.environ, "XDG_RUNTIME_DIR": XDG}
    try:
        # Find all BT cards
        out = subprocess.check_output(
            ["pactl", "list", "cards", "short"], env=env, text=True
        )
        cards = [l.split()[1] for l in out.strip().split("\n") if "bluez_card" in l]
        if not cards:
            return {"ok": False, "error": "No BT devices"}

        # Priority: Stargazer first
        primary = cards[0]
        for c in cards:
            if "4A_41_87" in c:
                primary = c
                break

        # Switch primary to HFP, others to A2DP
        for card in cards:
            if card == primary:
                # Try mSBC first, fallback to regular HFP
                profiles = subprocess.check_output(
                    ["pactl", "list", "cards"], env=env, text=True
                )
                if "headset-head-unit-msbc" in profiles:
                    subprocess.run(["pactl", "set-card-profile", card, "headset-head-unit-msbc"], env=env)
                else:
                    subprocess.run(["pactl", "set-card-profile", card, "headset-head-unit"], env=env)
            else:
                subprocess.run(["pactl", "set-card-profile", card, "a2dp-sink"], env=env, capture_output=True)

        name = primary.replace("bluez_card.", "").replace("_", ":")
        return {"ok": True, "device": name, "action": "switched_to_hfp"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    print("[bt-hfp] Listening on localhost:18797")
    HTTPServer(("127.0.0.1", 18797), Handler).serve_forever()
