"""Cloud Shell selective tool recovery regression checks.

No test installs a package or starts an actual tunnel/ollama process.
"""
from pathlib import Path
import os
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/cloudshell-recover.sh"


class CloudShellRecoveryTests(unittest.TestCase):
    def invoke(self, action, *, cloud_shell=False, overrides=None):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env.update(HOME=tmp, XDG_STATE_HOME=tmp, ZCLOUD_CONFIG=str(Path(tmp) / "missing.yml"))
            for key in ("CLOUD_SHELL", "DEVSHELL_PROJECT_ID", "ZWSL_ALLOW_NON_CLOUDSHELL", "ZCLOUD_HOSTNAME", "OLLAMA_MODELS", "ZWSL_OLLAMA_MODELS", "ZWSL_ALLOW_MODEL_DOWNLOAD", "ZWSL_RECOVERY_MODEL"):
                env.pop(key, None)
            if cloud_shell:
                env["CLOUD_SHELL"] = "true"
            if overrides:
                env.update(overrides)
            return subprocess.run(["bash", str(SCRIPT), action], cwd=ROOT,
                                  env=env, capture_output=True, text=True, timeout=15)

    def test_bash_syntax(self):
        result = subprocess.run(["bash", "-n", str(SCRIPT)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_status_is_nonmutating_even_without_cloud_shell(self):
        result = self.invoke("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("external_access_and_model_inference=NOT_VERIFIED", result.stdout)
        self.assertIn("tunnel_config=MISSING_OR_INVALID", result.stdout)
        self.assertIn("ollama_storage_path=/opt/zeaz-storage/models", result.stdout)

    def test_repair_requires_cloud_shell(self):
        result = self.invoke("repair")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Mutation is Cloud Shell only", result.stderr)

    def test_tunnel_start_requires_cloud_shell(self):
        result = self.invoke("tunnel-start")
        self.assertEqual(result.returncode, 2)

    def test_tunnel_start_requires_authorized_hostname(self):
        result = self.invoke("tunnel-start", cloud_shell=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ZCLOUD_HOSTNAME", result.stderr)

    def test_missing_ollama_archive_dependency_has_selective_install_gate(self):
        source = SCRIPT.read_text()
        # Cloud Shell can have curl and cloudflared but lack the zstd CLI needed
        # to extract Ollama's Linux release. Installing missing zstd must precede
        # execution of the upstream installer; re-runs must skip a present tool.
        helper = source.index("ensure_ollama_prerequisites() {")
        installer = source.index("install_ollama() {")
        downloader = source.index("https://ollama.com/install.sh")
        self.assertLess(helper, installer)
        self.assertLess(installer, downloader)
        section = source[helper:installer]
        self.assertIn('if exists zstd; then', section)
        self.assertIn('SKIP: zstd already installed', section)
        self.assertIn('sudo apt-get install -y --no-install-recommends zstd', section)
        self.assertIn('exists zstd || fail', section)
        self.assertIn('ensure_ollama_prerequisites', source[installer:downloader])
        self.assertIn('ollama_dependency_zstd=', source)

    def test_dependency_status_is_reported_without_install(self):
        result = self.invoke("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"ollama_dependency_zstd=(INSTALLED|MISSING)")
        self.assertNotIn("Installing missing", result.stdout)

    def test_installer_reuses_existing_without_model_pull_or_routing_changes(self):
        source = SCRIPT.read_text()
        self.assertIn("SKIP: cloudflared installed", source)
        self.assertIn("SKIP: Ollama installed", source)
        self.assertIn("SKIP: Ollama already responding", source)
        self.assertIn('OLLAMA_MODELS="$MODEL_DIR" OLLAMA_HOST=127.0.0.1:11434', source)
        self.assertIn('ollama_uses_model_store || fail', source)
        self.assertIn("https://pkg.cloudflare.com/cloudflared any main", source)
        self.assertIn("https://ollama.com/install.sh", source)
        self.assertIn("OLLAMA_HOST=127.0.0.1:11434", source)
        self.assertIn('bash "$ROOT/scripts/zcloud-tunnel.sh" start', source)
        for forbidden in ("tunnel route dns", "tunnel delete",
                          "rm -rf ~/.cloudflared", "docker compose down", "systemctl restart ssh"):
            self.assertNotIn(forbidden, source)

    def test_model_restore_requires_explicit_download_opt_in(self):
        result = self.invoke("model-restore", cloud_shell=True,
                             overrides={"ZWSL_RECOVERY_MODEL": "qwen2.5-coder:7b"})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("ZWSL_ALLOW_MODEL_DOWNLOAD=1", result.stderr)

    def test_model_restore_requires_explicit_model_name(self):
        result = self.invoke("model-restore", cloud_shell=True,
                             overrides={"ZWSL_ALLOW_MODEL_DOWNLOAD": "1"})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("ZWSL_RECOVERY_MODEL", result.stderr)

    def test_model_restore_rejects_invalid_model_name(self):
        result = self.invoke("model-restore", cloud_shell=True,
                             overrides={"ZWSL_ALLOW_MODEL_DOWNLOAD": "1",
                                        "ZWSL_RECOVERY_MODEL": "model ; touch /tmp/unsafe"})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("ZWSL_RECOVERY_MODEL", result.stderr)

    def test_repair_rejects_symlinked_model_directory_before_package_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = base / "actual"
            target.mkdir()
            shortcut = base / "models"
            shortcut.symlink_to(target, target_is_directory=True)
            result = self.invoke("repair", cloud_shell=True,
                                 overrides={"ZWSL_OLLAMA_MODELS": str(shortcut)})
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("non-canonical or contains a symlink", result.stderr)
            self.assertNotIn("Installing missing", result.stdout)

    def test_status_reports_override_storage_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "models"
            store.mkdir()
            result = self.invoke("status", overrides={"ZWSL_OLLAMA_MODELS": str(store)})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"ollama_storage_path={store}", result.stdout)
            self.assertIn("ollama_storage=PRESENT size_kib=", result.stdout)
            self.assertTrue(store.is_dir())

    def test_restore_action_is_only_path_allowed_to_download_weights(self):
        source = SCRIPT.read_text()
        self.assertIn('ZWSL_ALLOW_MODEL_DOWNLOAD:-0', source)
        self.assertIn('ollama pull "$model"', source)
        self.assertIn("    restore_model\n", source)
        self.assertNotIn('ollama pull', source.split('restore_model() {', 1)[0])
        self.assertIn("    prepare_model_dir\n    install_cloudflared", source)

    def test_invalid_existing_tunnel_credentials_block_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            binary = base / "bin"
            binary.mkdir()
            cloudflared = binary / "cloudflared"
            cloudflared.write_text("#!/bin/sh\nexit 0\n")
            cloudflared.chmod(0o700)
            tunnel_id = "11111111-1111-4111-8111-111111111111"
            config = base / "config.yml"
            credentials = base / "credentials.json"
            config.write_text(
                f"tunnel: {tunnel_id}\n"
                f"credentials-file: {credentials}\n"
                "ingress:\n"
                "  - hostname: ssh.example.org\n"
                "    service: ssh://127.0.0.1:22\n"
                "  - service: http_status:404\n"
            )
            config.chmod(0o600)
            credentials.write_text(json.dumps({"TunnelID": "22222222-2222-4222-8222-222222222222"}))
            credentials.chmod(0o600)
            env = dict(os.environ, CLOUD_SHELL="true", HOME=tmp,
                       ZCLOUD_HOSTNAME="ssh.example.org", ZCLOUD_CONFIG=str(config),
                       PATH=f"{binary}:{os.environ.get('PATH', '')}")
            result = subprocess.run(["bash", str(SCRIPT), "tunnel-start"], env=env,
                                    cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("TunnelID mismatch", result.stderr)

            credentials.write_text(json.dumps({"TunnelID": tunnel_id}))
            credentials.chmod(0o600)
            config.write_text(config.read_text().replace(
                "ssh://127.0.0.1:22", "http://127.0.0.1:8080"
            ))
            config.chmod(0o600)
            result = subprocess.run(["bash", str(SCRIPT), "tunnel-start"], env=env,
                                    cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not mapped to local port 22", result.stderr)

    def test_supervisor_can_start_without_executable_bit(self):
        supervisor = (ROOT / "scripts/zcloud-tunnel.sh").read_text()
        self.assertIn('nohup bash "$SELF" supervise', supervisor)

    def test_makefile_exposes_recovery_and_native_model_fallback(self):
        makefile = (ROOT / "Makefile").read_text()
        for target in ("cloudshell-recover-status", "cloudshell-recover",
                       "cloudshell-tunnel-start"):
            self.assertIn(f"\n{target}:\n", makefile)
        self.assertIn("docker exec zwslcore-ollama ollama list", makefile)
        self.assertIn("elif command -v ollama", makefile)


if __name__ == "__main__":
    unittest.main()
