#!/usr/bin/env python3
"""
Browser automation to inject transcribed text into OpenClaw webchat.
Watches /tmp/stt-output.txt and injects new content into the textarea.
"""

import time
import subprocess
from pathlib import Path

OUTPUT_FILE = "/tmp/stt-output.txt"
LAST_SIZE_FILE = "/tmp/stt-last-size"

def inject_text_to_webchat(text):
    """Use browser tool to inject text into webchat textarea."""
    if not text.strip():
        return
    
    # JavaScript to inject text into the textarea
    js_code = f'''
    const textarea = document.querySelector('textarea[placeholder*="message"], textarea');
    if (textarea) {{
        textarea.value = {repr(text)};
        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
        textarea.focus();
        console.log("Text injected:", {repr(text)});
    }} else {{
        console.error("Textarea not found");
    }}
    '''
    
    # Use OpenClaw browser tool to execute JavaScript
    try:
        result = subprocess.run([
            "openclaw", "browser", "act", "evaluate", 
            "--fn", js_code,
            "--url", "http://localhost:18789"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ Injected: {text}")
        else:
            print(f"❌ Injection failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Browser automation error: {e}")

def main():
    print("👁️  Watching for transcribed text...")
    
    last_size = 0
    if Path(LAST_SIZE_FILE).exists():
        last_size = int(Path(LAST_SIZE_FILE).read_text().strip() or "0")
    
    while True:
        try:
            if not Path(OUTPUT_FILE).exists():
                time.sleep(0.1)
                continue
                
            current_size = Path(OUTPUT_FILE).stat().st_size
            
            if current_size > last_size:
                # New content added
                content = Path(OUTPUT_FILE).read_text().strip()
                if content:
                    inject_text_to_webchat(content)
                    # Clear the file after injection
                    Path(OUTPUT_FILE).write_text("")
                
                last_size = 0
                Path(LAST_SIZE_FILE).write_text("0")
            
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\n👋 Stopping text injection...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()