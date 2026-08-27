import math
import struct
import zlib
import subprocess
import os
import re
import socket
import sys
import time
import threading
import signal as sig_mod
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib

_VERSION = "0.1.0"
_SOCKET_NAME = "noctalia.sock"
_CONFIG_NAME = "noctalia-config.toml"
_HOOK_LOG = "hook.log"
_FALLBACK_SEED = 0xFF7C4DFF


def _home():
    return str(Path.home())


def _runtime_dir():
    d = os.environ.get("XDG_RUNTIME_DIR", "")
    if not d:
        d = f"/tmp/noctalia-{os.getuid()}"
    return d


def _state_dir():
    d = os.environ.get("XDG_STATE_HOME", "")
    if not d:
        d = str(Path.home() / ".local" / "state")
    return os.path.join(d, "noctalia")


def _config_dir():
    return os.path.join(_home(), ".config", "noctalia")


def _config_path():
    return os.path.join(_config_dir(), _CONFIG_NAME)


def _socket_path():
    return os.path.join(_runtime_dir(), _SOCKET_NAME)


def _log_path():
    return os.path.join(_state_dir(), _HOOK_LOG)


@dataclass(frozen=True)
class Rgb:
    r: int
    g: int
    b: int

    @property
    def hex(self):
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    @property
    def rgb_csv(self):
        return f"{self.r},{self.g},{self.b}"


def _srgb_to_linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(v):
    return v * 12.92 if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055


def _argb_to_xyz(a):
    r = ((a >> 16) & 0xFF) / 255.0
    g = ((a >> 8) & 0xFF) / 255.0
    b = (a & 0xFF) / 255.0
    lr = _srgb_to_linear(r)
    lg = _srgb_to_linear(g)
    lb = _srgb_to_linear(b)
    x = 0.41233895 * lr + 0.35762064 * lg + 0.18051042 * lb
    y = 0.2126 * lr + 0.7152 * lg + 0.0722 * lb
    z = 0.01932141 * lr + 0.11916382 * lg + 0.95034478 * lb
    return x, y, z


def _xyz_to_argb(x, y, z):
    lr = 3.24107780 * x - 1.53720832 * y - 0.49870278 * z
    lg = -0.96914381 * x + 1.87593237 * y + 0.04167803 * z
    lb = 0.05571254 * x - 0.20450506 * y + 1.05728689 * z
    r = max(0.0, min(1.0, _linear_to_srgb(lr)))
    g = max(0.0, min(1.0, _linear_to_srgb(lg)))
    b = max(0.0, min(1.0, _linear_to_srgb(lb)))
    return (0xFF << 24) | (int(round(r * 255)) << 16) | (int(round(g * 255)) << 8) | int(round(b * 255))


def _lab_f(t):
    d = 6.0 / 29.0
    return t ** (1.0 / 3.0) if t > d ** 3 else t / (3 * d * d) + 4.0 / 29.0


def _lab_finv(t):
    d = 6.0 / 29.0
    return t ** 3 if t > d else 3 * d * d * (t - 4.0 / 29.0)


def _xyz_to_lab(x, y, z):
    fx = _lab_f(x / 0.95047)
    fy = _lab_f(y / 1.0)
    fz = _lab_f(z / 1.08883)
    return 116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)


def _lab_to_xyz(l, a, b):
    fy = (l + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    return 0.95047 * _lab_finv(fx), 1.0 * _lab_finv(fy), 1.08883 * _lab_finv(fz)


def _argb_to_hct(a):
    x, y, z = _argb_to_xyz(a)
    l, la, lb = _xyz_to_lab(x, y, z)
    c = math.sqrt(la * la + lb * lb)
    h = math.degrees(math.atan2(lb, la)) % 360.0
    return h, c, l


def _hct_to_argb(h, c, t):
    hr = math.radians(h)
    la = c * math.cos(hr)
    lb = c * math.sin(hr)
    x, y, z = _lab_to_xyz(t, la, lb)
    return _xyz_to_argb(x, y, z)


class TonalPalette:
    __slots__ = ("hue", "chroma", "_cache")

    def __init__(self, hue, chroma):
        self.hue = hue
        self.chroma = chroma
        self._cache = {}

    def get(self, tone):
        tone = int(tone)
        if tone in self._cache:
            return self._cache[tone]
        a = _hct_to_argb(self.hue, self.chroma, float(tone))
        rgb = Rgb((a >> 16) & 0xFF, (a >> 8) & 0xFF, a & 0xFF)
        self._cache[tone] = rgb
        return rgb


@dataclass
class ColorRole:
    default: Rgb
    light: Rgb
    dark: Rgb


def _role(p, lt, dt):
    return ColorRole(p.get(dt), p.get(lt), p.get(dt))


def _role_flat(p, t):
    r = p.get(t)
    return ColorRole(r, r, r)


def generate_palette(seed):
    h, c, t = _argb_to_hct(seed)
    if h < 0:
        h += 360.0
    pc = max(36.0, c)
    sc = max(16.0, c * 0.4)
    tc = max(24.0, c * 0.6)
    primary = TonalPalette(h, pc)
    secondary = TonalPalette(h, sc)
    tertiary = TonalPalette((h + 60) % 360, tc)
    neutral = TonalPalette(h, 4.0)
    nv = TonalPalette(h, 8.0)
    error = TonalPalette(25.0, 84.0)
    return {
        "primary": _role(primary, 40, 80),
        "on_primary": _role(primary, 100, 20),
        "primary_container": _role(primary, 90, 30),
        "on_primary_container": _role(primary, 10, 90),
        "secondary": _role(secondary, 40, 80),
        "on_secondary": _role(secondary, 100, 20),
        "secondary_container": _role(secondary, 90, 30),
        "on_secondary_container": _role(secondary, 10, 90),
        "tertiary": _role(tertiary, 40, 80),
        "on_tertiary": _role(tertiary, 100, 20),
        "tertiary_container": _role(tertiary, 90, 30),
        "on_tertiary_container": _role(tertiary, 10, 90),
        "error": _role(error, 40, 80),
        "on_error": _role(error, 100, 20),
        "error_container": _role(error, 90, 30),
        "on_error_container": _role(error, 10, 90),
        "background": _role(neutral, 98, 10),
        "on_background": _role(neutral, 10, 90),
        "surface": _role(neutral, 98, 10),
        "on_surface": _role(neutral, 10, 90),
        "surface_variant": _role(nv, 90, 30),
        "on_surface_variant": _role(nv, 30, 80),
        "outline": _role_flat(nv, 50),
        "outline_variant": _role_flat(nv, 80),
        "surface_container_lowest": _role(neutral, 100, 4),
        "surface_container_low": _role(neutral, 96, 12),
        "surface_container": _role(neutral, 94, 17),
        "surface_container_high": _role(neutral, 92, 22),
        "surface_container_highest": _role(neutral, 90, 27),
    }


def palette_to_context(palette, mode="default"):
    ctx = {}
    for name, role in palette.items():
        if mode == "light":
            rgb = role.light
        elif mode == "dark":
            rgb = role.dark
        else:
            rgb = role.default
        ctx[name] = {
            "default": {"hex": role.default.hex, "rgb_csv": role.default.rgb_csv},
            "light": {"hex": role.light.hex, "rgb_csv": role.light.rgb_csv},
            "dark": {"hex": role.dark.hex, "rgb_csv": role.dark.rgb_csv},
        }
    return ctx


def _extract_seed_from_pixels(px, skip=10):
    best_score = -1.0
    best = _FALLBACK_SEED
    for i in range(0, len(px), skip * 4):
        if i + 3 >= len(px):
            break
        r, g, b, a = px[i + 2], px[i + 1], px[i], px[i + 3]
        if a < 128:
            continue
        if abs(r - g) < 10 and abs(g - b) < 10 and abs(r - b) < 10:
            continue
        argb = (0xFF << 24) | (r << 16) | (g << 8) | b
        _, c, t = _argb_to_hct(argb)
        score = c * (1.0 - abs(t - 50.0) / 50.0)
        if score > best_score:
            best_score = score
            best = argb
    return best


def _unfilter_png(data, w, h, bpp):
    stride = w * bpp
    raw = bytearray(stride * h)
    prev = bytearray(stride)
    pos = 0
    for y in range(h):
        if pos >= len(data):
            break
        ft = data[pos]
        pos += 1
        row = bytearray(data[pos:pos + stride])
        pos += stride
        if ft == 1:
            for i in range(bpp, stride):
                row[i] = (row[i] + row[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                avg = (row[i - bpp] + prev[i]) // 2 if i >= bpp else prev[i] // 2
                row[i] = (row[i] + avg) & 0xFF
        elif ft == 4:
            for i in range(stride):
                ra = row[i - bpp] if i >= bpp else 0
                rb = prev[i]
                rc = prev[i - bpp] if i >= bpp else 0
                p = ra + rb - rc
                pa, pb, pc = abs(p - ra), abs(p - rb), abs(p - rc)
                pr = ra if (pa <= pb and pa <= pc) else (rb if pb <= pc else rc)
                row[i] = (row[i] + pr) & 0xFF
        raw[y * stride:(y + 1) * stride] = row
        prev = row
    if bpp == 4:
        return bytes(raw)
    elif bpp == 3:
        rgba = bytearray(w * h * 4)
        for i in range(w * h):
            rgba[i * 4: i * 4 + 3] = raw[i * 3: i * 3 + 3]
            rgba[i * 4 + 3] = 0xFF
        return bytes(rgba)
    return b""


def extract_seed(path):
    try:
        with open(path, "rb") as f:
            sig = f.read(8)
    except Exception:
        return _FALLBACK_SEED
    if sig[:4] == b"\x89PNG":
        return _extract_png(path)
    return _extract_via_ffmpeg(path)


def _extract_png(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        if data[12:16] != b"IHDR":
            return _FALLBACK_SEED
        w = struct.unpack(">I", data[16:20])[0]
        h = struct.unpack(">I", data[20:24])[0]
        ct = data[25]
        bpp = 4 if ct == 6 else 3 if ct == 2 else 0
        if bpp == 0:
            return _extract_via_ffmpeg(path)
        raw = b""
        pos = 8
        while pos < len(data):
            ln = struct.unpack(">I", data[pos:pos + 4])[0]
            if data[pos + 4:pos + 8] == b"IDAT":
                raw += data[pos + 8:pos + 8 + ln]
            pos += 12 + ln
        dec = zlib.decompress(raw)
        px = _unfilter_png(dec, w, h, bpp)
        if not px:
            return _FALLBACK_SEED
        return _extract_seed_from_pixels(px, max(1, (w * h) // 5000))
    except Exception:
        return _FALLBACK_SEED


def _extract_via_ffmpeg(path):
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgba",
             "-vf", "scale=80:80", "-"],
            capture_output=True, check=False, timeout=10,
        )
        if r.returncode == 0 and len(r.stdout) >= 25600:
            return _extract_seed_from_pixels(r.stdout[:25600], 4)
    except Exception:
        pass
    return _FALLBACK_SEED


def load_config():
    p = _config_path()
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def get_wallpaper():
    return load_config().get("wallpaper", {}).get("current")


def get_theme_mode():
    return load_config().get("theme", {}).get("mode", "auto")


def get_user_templates():
    cfg = load_config()
    templates = cfg.get("theme", {}).get("templates", {}).get("user", {})
    result = []
    for name, t in templates.items():
        entry = {"name": name}
        entry.update(t)
        result.append(entry)
    result.sort(key=lambda x: x.get("index", 0))
    return result


def get_hooks():
    return load_config().get("hooks", {})


def get_wallpaper_dir():
    return load_config().get("wallpaper", {}).get("directory", os.path.join(_home(), "Pictures", "Wallpapers"))


def render_templates(palette, mode):
    ctx = palette_to_context(palette, mode)
    for tmpl in get_user_templates():
        inp = tmpl.get("input_path", "")
        outp = tmpl.get("output_path", "")
        hook = tmpl.get("post_hook", "")
        if not inp or not outp:
            continue
        inp = os.path.expanduser(inp)
        outp = os.path.expanduser(outp)
        if not os.path.isfile(inp):
            continue
        try:
            content = open(inp, "r", encoding="utf-8", errors="replace").read()
            rendered = _render_jinja_simple(content, ctx, mode)
            os.makedirs(os.path.dirname(outp), exist_ok=True)
            open(outp, "w", encoding="utf-8").write(rendered)
        except Exception:
            continue
        if hook:
            try:
                subprocess.run(["bash", "-c", hook], check=False, timeout=30,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass


def _render_jinja_simple(text, ctx, mode):
    pattern = re.compile(r"\{\{\s*colors\.([a-z_]+)\.(default|light|dark)\.(hex|rgb_csv)\s*\}\}")
    def repl(m):
        name, submode, fmt = m.group(1), m.group(2), m.group(3)
        role = ctx.get(name)
        if not role:
            return m.group(0)
        rgb = role.get(submode)
        if not rgb:
            return m.group(0)
        return rgb.get(fmt, m.group(0))
    return pattern.sub(repl, text)


def run_hook(hook_name):
    hooks = get_hooks()
    scripts = hooks.get(hook_name, [])
    if isinstance(scripts, str):
        scripts = [scripts]
    for s in scripts:
        s = os.path.expanduser(s)
        try:
            subprocess.run(["bash", s], check=False, timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           env={**os.environ, "NOCTALIA_THEME_MODE": get_theme_mode()})
        except Exception:
            pass
    _append_hook_log(f"{hook_name} triggered")


def _append_hook_log(msg):
    try:
        os.makedirs(_state_dir(), exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        pass


def random_wallpaper():
    wdir = get_wallpaper_dir()
    if not os.path.isdir(wdir):
        return None
    files = [f for f in os.listdir(wdir) if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))]
    if not files:
        return None
    import random
    return os.path.join(wdir, random.choice(files))


def _panel_toggle(panel):
    tools = {
        "launcher": ["rofi", "-show", "drun"],
        "session": ["wlogout", "-b", "3"],
        "clipboard": ["bash", "-c", "wl-paste | rofi -dmenu | wl-copy"],
    }
    cmd = tools.get(panel)
    if cmd:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


class Daemon:
    def __init__(self):
        self._palette = None
        self._seed = _FALLBACK_SEED
        self._lock = threading.Lock()
        self._sock = None

    def start(self):
        os.makedirs(_runtime_dir(), exist_ok=True)
        os.makedirs(_state_dir(), exist_ok=True)
        sp = _socket_path()
        if os.path.exists(sp):
            os.unlink(sp)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(sp)
        self._sock.listen(8)
        os.chmod(sp, 0o600)
        try:
            sig_mod.signal(sig_mod.SIGTERM, self._signal_handler)
            sig_mod.signal(sig_mod.SIGINT, self._signal_handler)
        except (ValueError, OSError):
            pass
        self._regenerate()
        while True:
            try:
                conn, _ = self._sock.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except Exception:
                break

    def _signal_handler(self, signum, frame):
        try:
            if self._sock:
                self._sock.close()
            os.unlink(_socket_path())
        except Exception:
            pass
        sys.exit(0)

    def _handle(self, conn):
        try:
            data = conn.recv(4096).decode("utf-8").strip()
            if not data:
                conn.sendall(b"OK\n")
                return
            parts = data.split(maxsplit=2)
            result = self._dispatch(parts)
            conn.sendall((result + "\n").encode("utf-8"))
        except Exception:
            try:
                conn.sendall(b"ERROR\n")
            except Exception:
                pass
        finally:
            conn.close()

    def _dispatch(self, parts):
        if len(parts) < 2 or parts[0] != "msg":
            return "ERROR"
        cmd = parts[1]
        arg = parts[2] if len(parts) > 2 else ""
        with self._lock:
            if cmd == "status":
                return "OK"
            elif cmd == "config-reload":
                self._regenerate()
                return "OK"
            elif cmd == "templates-apply":
                self._render()
                return "OK"
            elif cmd == "wallpaper-set":
                return self._cmd_wallpaper_set(arg)
            elif cmd == "wallpaper-get":
                return get_wallpaper() or ""
            elif cmd == "wallpaper-random":
                wp = random_wallpaper()
                if wp:
                    return self._cmd_wallpaper_set(wp)
                return "ERROR"
            elif cmd == "theme-mode-toggle":
                return self._cmd_theme_toggle()
            elif cmd == "theme-mode-set":
                return self._cmd_theme_set(arg)
            elif cmd == "theme-mode-get":
                return get_theme_mode()
            elif cmd == "nightlight-disable":
                return "OK"
            elif cmd == "panel-toggle":
                _panel_toggle(arg)
                return "OK"
            elif cmd == "settings-toggle":
                try:
                    subprocess.Popen(["gnome-control-center"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
                return "OK"
            elif cmd == "session":
                if arg == "lock":
                    try:
                        subprocess.Popen(["swaylock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                    return "OK"
            elif cmd == "plugins":
                return "OK"
            elif cmd == "sessions":
                return "niri"
            return "OK"

    def _cmd_wallpaper_set(self, path):
        cfg = load_config()
        if "wallpaper" not in cfg:
            cfg["wallpaper"] = {}
        cfg["wallpaper"]["current"] = path
        _save_config(cfg)
        self._regenerate()
        run_hook("wallpaper_changed")
        self._render()
        return "OK"

    def _cmd_theme_toggle(self):
        mode = get_theme_mode()
        new_mode = "light" if mode == "dark" else "dark"
        cfg = load_config()
        cfg.setdefault("theme", {})["mode"] = new_mode
        _save_config(cfg)
        run_hook("theme_mode_changed")
        self._render()
        return "OK"

    def _cmd_theme_set(self, mode):
        cfg = load_config()
        cfg.setdefault("theme", {})["mode"] = mode
        _save_config(cfg)
        run_hook("theme_mode_changed")
        self._render()
        return "OK"

    def _regenerate(self):
        wp = get_wallpaper()
        if wp and os.path.isfile(wp):
            self._seed = extract_seed(wp)
        else:
            self._seed = _FALLBACK_SEED
        self._palette = generate_palette(self._seed)

    def _render(self):
        if not self._palette:
            self._regenerate()
        mode = get_theme_mode()
        if mode == "auto":
            mode = "dark"
        render_templates(self._palette, mode)


def _save_config(cfg):
    p = _config_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    lines = []
    _write_toml(lines, "", cfg)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_toml(lines, prefix, data):
    for k, v in data.items():
        if isinstance(v, dict):
            sec = f"{prefix}.{k}" if prefix else k
            lines.append(f"[{sec}]")
            _write_toml(lines, sec, v)
        elif isinstance(v, list):
            vals = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in v)
            lines.append(f"{k} = [{vals}]")
        elif isinstance(v, bool):
            lines.append(f"{k} = {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k} = {v}")
        elif isinstance(v, str):
            lines.append(f'{k} = "{v}"')


def _ipc_client(msg):
    sp = _socket_path()
    if not os.path.exists(sp):
        print("ERROR", file=sys.stderr)
        sys.exit(1)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(sp)
        s.sendall(msg.encode("utf-8"))
        resp = s.recv(4096).decode("utf-8").strip()
        s.close()
        return resp
    except Exception:
        print("ERROR", file=sys.stderr)
        sys.exit(1)


def main():
    args = sys.argv[1:]
    if not args:
        d = Daemon()
        d.start()
        return
    if args[0] == "msg":
        msg_str = " ".join(args)
        resp = _ipc_client(msg_str)
        print(resp)
        if resp == "ERROR":
            sys.exit(1)
        return
    if args[0] == "--version" or args[0] == "-v":
        print(_VERSION)
        return
    print(f"noctalia {_VERSION}\nusage: noctalia msg <command> | noctalia (daemon)")


if __name__ == "__main__":
    main()