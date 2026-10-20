from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap-wsl.sh"


def docker_package_completion_block() -> str:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    start = source.index("# Existing Docker CE installations")
    end = source.index("# END Docker package completion", start)
    return source[start:end]


class WslBootstrapTests(unittest.TestCase):
    def run_package_check(self, installed: str) -> list[str]:
        block = docker_package_completion_block()
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "apt.log"
            prelude = r'''
dpkg-query() {
  local package="${@: -1}"
  case " ${INSTALLED_DOCKER_PACKAGES:-} " in
    *" ${package} "*) printf 'ii  %s\n' "$package" ;;
    *) return 1 ;;
  esac
}
apt-get() { printf '%s\n' "$*" >> "$APT_LOG"; }
log() { :; }
'''
            env = os.environ | {
                "INSTALLED_DOCKER_PACKAGES": installed,
                "APT_LOG": str(log_path),
            }
            result = subprocess.run(
                ["bash", "-c", prelude + "\n" + block],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return log_path.read_text(encoding="utf-8").splitlines() if log_path.exists() else []

    def test_existing_engine_installs_only_missing_buildx_and_compose_plugins(self) -> None:
        commands = self.run_package_check("docker-ce docker-ce-cli containerd.io")
        self.assertEqual(
            commands,
            ["update", "install -y docker-buildx-plugin docker-compose-plugin"],
        )

    def test_complete_docker_install_does_not_trigger_apt_upgrade(self) -> None:
        commands = self.run_package_check(
            "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
        )
        self.assertEqual(commands, [])


if __name__ == "__main__":
    unittest.main()
