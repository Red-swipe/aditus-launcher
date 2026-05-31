import logging
import os
import subprocess

logger = logging.getLogger("aditus.launcher")


class AppLauncher:
    def launch(self, app: dict) -> bool:
        try:
            path = app.get("path")
            if not path:
                logger.error("App entry missing required key 'path': %s", app)
                return False
            if not os.path.isfile(path):
                logger.error("File not found: %s", path)
                return False

            try:
                os.startfile(path)
                logger.info(f"aditus.launcher: launched via startfile: {path}")
            except Exception as e:
                logger.warning(f"aditus.launcher: startfile failed, trying Popen: {e}")
                subprocess.Popen([path], shell=True)
            return True
        except Exception:
            logger.exception("Failed to launch %s", app.get("label", app.get("name", "unknown")))
            return False

    def launch_all(self, apps: list) -> dict:
        launched = []
        failed = []

        for app in apps:
            label = app.get("label", app.get("name", "unknown"))
            if self.launch(app):
                launched.append(label)
            else:
                failed.append(label)

        return {"launched": launched, "failed": failed}
