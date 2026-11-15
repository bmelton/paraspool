# /// script
# requires-python = ">=3.10"
# dependencies = []
# [tool.orcaslicer.plugin]
# name = "Paraspool"
# description = "Parametric rim adapter for cardboard filament spools in an AMS. Pick a brand or enter a diameter, preview, send to plate."
# author = "Barry Melton"
# version = "0.1.0"
# license = "MIT"
# ///
"""Paraspool: OrcaSlicer Pages plugin wrapping openscad/src/rim.scad.

Dev layout reads assets from the repo; the release build (build.py) inlines them
into _EMBEDDED so dist/paraspool.py is a single file.
"""
from __future__ import annotations

import base64
import gzip
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

_EMBEDDED: dict[str, str] = {}  # build.py replaces this line with base64(gzip(bytes)) per asset

_HERE = Path(__file__).resolve().parent
_DEV_PATHS = {
    "page.html": _HERE / "page.html",
    "three.min.js": _HERE.parent / "vendor" / "three.min.js",
    "rim.scad": _HERE.parent.parent / "openscad" / "src" / "rim.scad",
    "AllertaStencil-Regular.ttf": _HERE.parent.parent / "openscad" / "fonts" / "AllertaStencil-Regular.ttf",
    "brand_presets.json": _HERE.parent.parent / "presets" / "brand_presets.json",
}
STL_NAME = "paraspool.stl"


def asset(name: str) -> bytes:
    p = _DEV_PATHS[name]
    if p.exists():
        return p.read_bytes()
    return gzip.decompress(base64.b64decode(_EMBEDDED[name]))


def presets() -> dict:
    return json.loads(asset("brand_presets.json"))


def page_html() -> str:
    return asset("page.html").decode().replace("/*THREE_JS*/", asset("three.min.js").decode())


# --- OpenSCAD ----------------------------------------------------------------

def find_openscad() -> str | None:
    cands = [shutil.which("openscad"), shutil.which("openscad-nightly")]
    if sys.platform == "darwin":
        cands += ["/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD", "/opt/homebrew/bin/openscad"]
    elif os.name == "nt":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", "")):
            if base:
                cands += [os.path.join(base, "OpenSCAD", "openscad.exe"), os.path.join(base, "OpenSCAD (Nightly)", "openscad.exe")]
    else:
        cands += ["/usr/bin/openscad", "/usr/local/bin/openscad", shutil.which("org.openscad.OpenSCAD")]
    for c in cands:
        if c and Path(c).is_file():
            return c
    return None


def openscad_version(exe: str) -> str:
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
    return (out.stdout + out.stderr).strip().replace("OpenSCAD version ", "")


def scad_literal(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(float(v)) if isinstance(v, float) else str(v)
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_argv(exe: str, workdir: Path) -> list[str]:
    """Constant command line: OrcaSlicer persists process permissions keyed on str(argv),
    so parameters live in main.scad rather than -D flags."""
    return [exe, "--backend=Manifold", "--export-format=binstl", "-o", str(workdir / STL_NAME), str(workdir / "main.scad")]


def render(exe: str, workdir: Path, params: dict, timeout: int = 120) -> tuple[Path, float]:
    """Run rim.scad with the given overrides. Returns (binary STL path, seconds)."""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "rim.scad").write_bytes(asset("rim.scad"))
    font = workdir / "AllertaStencil-Regular.ttf"
    if not font.exists():
        font.write_bytes(asset("AllertaStencil-Regular.ttf"))

    defs = {
        "spool_type": "Custom",
        "manual_spool_diameter": float(params["diameter"]),
        "manual_label_text": str(params.get("label", "")),
    }
    for k in ("tolerance", "rim_width", "lip_height", "wall_thickness", "font_size"):
        if k in params and params[k] is not None:
            defs[k] = float(params[k])
    # In OpenSCAD the last assignment in a scope wins, so overrides after the include take effect.
    (workdir / "main.scad").write_text(
        "include <rim.scad>\n" + "".join(f"{k} = {scad_literal(v)};\n" for k, v in defs.items()))

    args = render_argv(exe, workdir)
    out = Path(args[4])
    env = dict(os.environ, OPENSCAD_FONT_PATH=str(workdir))
    t0 = time.time()
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    if proc.returncode != 0 and "backend" in proc.stderr.lower():
        # ponytail: older OpenSCAD without --backend; retry on CGAL
        proc = subprocess.run([a for a in args if a != "--backend=Manifold"], capture_output=True, text=True, timeout=timeout, env=env)
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError("OpenSCAD failed:\n" + (proc.stderr or proc.stdout).strip()[-1500:])
    return out, time.time() - t0


def stl_positions(data: bytes) -> tuple[bytes, int]:
    """Binary STL -> (float32 xyz triples for every triangle vertex, triangle count)."""
    if len(data) < 84:
        raise ValueError("STL too short")
    n = struct.unpack_from("<I", data, 80)[0]
    if 84 + 50 * n != len(data):
        raise ValueError("Not a binary STL")
    out = bytearray(n * 36)
    for i in range(n):
        off = 84 + 50 * i + 12  # skip normal
        out[i * 36:(i + 1) * 36] = data[off:off + 36]
    return bytes(out), n


# --- handing the STL to OrcaSlicer's plater -------------------------------------
# OrcaSlicer has no plugin API for loading a file, so reuse its single-instance IPC:
# the running instance accepts an argv string ("exe;path", escape_strings_cstyle format)
# over WM_COPYDATA on Windows and D-Bus on Linux. macOS goes through LaunchServices.

def escape_cstyle(args: list[str]) -> str:
    parts = []
    for a in args:
        if any(c in a for c in ' \t;\\"\r\n') or (a == "" and len(args) == 1):
            a = '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n") + '"'
        parts.append(a)
    return ";".join(parts)


def host_executable() -> str:
    if os.name == "nt":
        import ctypes
        buf = ctypes.create_unicode_buffer(32768)
        ctypes.windll.kernel32.GetModuleFileNameW(None, buf, len(buf))
        return buf.value
    if sys.platform.startswith("linux"):
        return os.environ.get("APPIMAGE") or os.path.realpath("/proc/self/exe")
    return sys.executable


def macos_app_bundle() -> str | None:
    for p in Path(sys.executable).resolve().parents:
        if p.suffix == ".app":
            return str(p)
    for name in ("/Applications/OrcaSlicer.app", os.path.expanduser("~/Applications/OrcaSlicer.app")):
        if Path(name).exists():
            return name
    return None


def macos_open_argv(path: Path) -> list[str]:
    return ["/usr/bin/open", "-a", macos_app_bundle() or "OrcaSlicer", str(path)]


def send_to_plate(path: Path) -> bool:
    payload = escape_cstyle([host_executable(), str(path)])
    if os.name == "nt":
        return _send_windows(payload)
    if sys.platform == "darwin":
        return subprocess.run(macos_open_argv(path), capture_output=True, timeout=10).returncode == 0
    return _send_dbus(payload)


def _send_windows(payload: str) -> bool:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    WM_COPYDATA = 0x004A

    class COPYDATASTRUCT(ctypes.Structure):
        _fields_ = [("dwData", ctypes.c_size_t), ("cbData", wintypes.DWORD), ("lpData", ctypes.c_void_p)]

    found = []
    my_pid = os.getpid()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def enum(hwnd, _):
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value != "wxWindowNR":
            return True
        if not (user32.GetPropW(hwnd, "Instance_Hash_Minor") and user32.GetPropW(hwnd, "Instance_Hash_Major")):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == my_pid:
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(enum, 0)
    if not found:
        return False
    text = ctypes.create_unicode_buffer(payload)
    cds = COPYDATASTRUCT(1, ctypes.sizeof(text), ctypes.cast(text, ctypes.c_void_p))
    # SendMessageW blocks on Orca's UI thread; must not be called from on_message itself.
    user32.SendMessageW(found[0], WM_COPYDATA, 0, ctypes.addressof(cds))
    return True


def _send_dbus(payload: str) -> bool:
    if not shutil.which("dbus-send"):
        return False
    names = subprocess.run(
        ["dbus-send", "--session", "--print-reply", "--dest=org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus.ListNames"],
        capture_output=True, text=True, timeout=10).stdout
    import re
    for name in re.findall(r'"([\w.-]*InstanceCheck\.Object\d+)"', names):
        obj = "/" + name.replace(".", "/")
        r = subprocess.run(["dbus-send", "--session", "--print-reply", "--reply-timeout=1500", f"--dest={name}", obj,
                            f"{name}.AnotherInstance", f"string:{payload}"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 or "NoReply" in r.stderr:  # receiver never replies; NoReply after the timeout means it was dispatched
            return True
    return False


# --- OrcaSlicer capability ---------------------------------------------------------

try:
    import orca  # type: ignore
except ImportError:  # running outside OrcaSlicer (tests, CLI)
    orca = None


def workdir() -> Path:
    try:
        return Path(orca.host.plugin.storage())
    except Exception:
        return _HERE / "work"


if orca is not None:
    _PagesBase = getattr(getattr(orca, "pages", None), "PagesPluginCapabilityBase", None)

    if _PagesBase is not None:
        class ParaspoolPage(_PagesBase):
            def get_name(self):
                return "Paraspool"

            def get_ui(self):
                return page_html()

            def on_message(self, msg):
                # Runs on the UI thread inside the host's audit scope, so a permission prompt is
                # synchronous. Plugin-spawned threads are denied first time (fail closed), so the
                # OpenSCAD run stays here; it takes well under a second with Manifold.
                if isinstance(msg, str):
                    msg = json.loads(msg)
                t = msg.get("type")
                try:
                    if t == "hello":
                        exe = find_openscad()
                        self.post_message({"type": "hello", "presets": presets(), "default_brand": "Polymaker",
                                           "openscad": Path(exe).name if exe else None})
                    elif t == "render":
                        exe = find_openscad()
                        if not exe:
                            raise RuntimeError("OpenSCAD not found.")
                        stl, secs = render(exe, workdir(), msg["params"])
                        pos, n = stl_positions(stl.read_bytes())
                        self.post_message({"type": "mesh", "path": str(stl), "triangles": n, "seconds": secs,
                                           "positions": base64.b64encode(pos).decode()})
                    elif t == "send":
                        if os.name == "nt":
                            # SendMessageW to Orca's own window from the UI thread would deadlock.
                            threading.Thread(target=self._send, args=(msg["path"],), daemon=True).start()
                        else:
                            self._send(msg["path"])
                except Exception as e:  # surfaced in the page, not swallowed
                    self.post_message({"type": "error", "message": str(e)})

            def _send(self, path):
                try:
                    ok = send_to_plate(Path(path))
                except Exception:
                    ok = False
                self.post_message({"type": "sent", "ok": ok})

        _Capability = ParaspoolPage
    else:
        class ParaspoolNeedsPages(orca.script.ScriptPluginCapabilityBase):
            def get_name(self):
                return "Paraspool (needs OrcaSlicer 2.5+)"

            def execute(self):
                return orca.ExecutionResult.failure(orca.PluginResult.RecoverableError,
                                                    "Paraspool needs an OrcaSlicer build with plugin pages (orca.pages).")

        _Capability = ParaspoolNeedsPages

    @orca.plugin
    class ParaspoolPlugin(orca.base):
        def register_capabilities(self):
            try:
                exe = find_openscad()
                procs = [str(render_argv(exe, workdir()))] if exe else []
                if sys.platform == "darwin":
                    procs.append(str(macos_open_argv(workdir() / STL_NAME)))
                orca.request_permissions(process=procs, threading=os.name == "nt")
            except Exception:
                pass  # older host without request_permissions: first use prompts instead
            orca.register_capability(_Capability)


# --- CLI / self-check ---------------------------------------------------------------

def _selfcheck():
    assert escape_cstyle(["orca-slicer", "/tmp/a.stl"]) == "orca-slicer;/tmp/a.stl"
    assert escape_cstyle([r"C:\Program Files\Orca\orca.exe", r"C:\x y\a.stl"]) == r'"C:\\Program Files\\Orca\\orca.exe";"C:\\x y\\a.stl"'
    assert scad_literal('SAY "HI"') == '"SAY \\"HI\\""' and scad_literal(199.5) == "199.5" and scad_literal(6) == "6"
    assert "/*THREE_JS*/" not in page_html() and "REVISION=" in page_html()
    assert "Polymaker" in presets() and presets()["Polymaker"]["diameter"] == 199.5
    # one real triangle: 80 header + count + (normal + 3 verts + attr)
    tri = struct.pack("<12f", 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0) + b"\0\0"
    pos, n = stl_positions(b"\0" * 80 + struct.pack("<I", 1) + tri)
    assert n == 1 and struct.unpack("<9f", pos) == (0, 0, 0, 1, 0, 0, 0, 1, 0)
    exe = find_openscad()
    if exe:
        out, secs = render(exe, Path(sys.argv[1]) if len(sys.argv) > 1 else _HERE / "work", {"diameter": 199.5, "label": "TEST", "tolerance": 0.4})
        pos, n = stl_positions(out.read_bytes())
        assert n > 1000 and len(pos) == n * 36, (n, len(pos))
        print(f"rendered {n} triangles in {secs:.1f}s -> {out}")
    else:
        print("OpenSCAD not found; skipped render check")
    print("selfcheck ok")


if __name__ == "__main__":
    _selfcheck()
