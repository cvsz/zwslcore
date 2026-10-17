"""Safety checks for optional Cloudflare WebUI ingress configurator."""
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/cloudflare-stack.sh"

class CloudflareStackTests(unittest.TestCase):
    def test_script_parses(self):
        result=subprocess.run(["bash","-n",str(SCRIPT)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_fails_closed(self):
        text=SCRIPT.read_text()
        for required in ("ZWSL_WEBUI_ACCESS_VERIFIED", "rollback)", "WebUI and SSH must use separate hostnames", "http_status:404", "127.0.0.1", "curl -fsS"):
            self.assertIn(required,text)
        self.assertNotIn("kill -9",text)
        self.assertNotIn("cloudflared tunnel run",text)
    def test_make_exposes_lifecycle(self):
        text=(ROOT/"Makefile").read_text()
        for name in ("cloudflare-stack-preflight","cloudflare-stack-configure","cloudflare-stack-rollback"):
            self.assertIn("\n"+name+":\n",text)

if __name__=="__main__":
    unittest.main()
