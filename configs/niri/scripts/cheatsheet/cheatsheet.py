import os
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango

CONTENT = """NyxNiri 快捷键与命令

Mod 就是键盘上的 Super 键，也就是 Windows 键，按 Mod 加斜杠随时能呼出系统自带的按键速查浮层，改了键位想生效就按 Mod 加 Shift 加 R 重载配置

桌面按键

会话和系统

Mod+Tab        概览模式，看所有工作区
Mod+Q          关掉当前窗口
Mod+Shift+Q    退出桌面，回到登录界面
Mod+Shift+R    重载 Niri 配置
Mod+L          锁屏
Mod+/          按键速查浮层

应用和面板

Mod+Enter      Kitty 终端
Mod+E          Nautilus 文件管理器
Mod+R          应用启动器
Mod+X          电源菜单
Mod+I          系统设置
Mod+V          剪贴板历史
Mod+W          壁纸选择器
Mod+Ctrl+W     随机换一张壁纸，主题配色跟着变
Mod+N          护眼模式，屏幕变暖，关掉模糊和透明
Mod+`          呼出或收起划屏终端
Mod+A          Orbit 星环启动器
Mod+鼠标前侧键  同上

焦点和移动

Mod+方向键      移焦点，顶到边就自动跳到隔壁屏或隔壁工作区
Mod+Z / Mod+C  左边那列 / 右边那列
Mod+D / Mod+U  下一个 / 上一个工作区
Mod+Ctrl+方向键  搬运窗口，顶到边自动搬去隔壁屏或工作区
Mod+Shift+方向键  老老实实按方向移，不玩花样
Mod+Shift+Ctrl+方向键  把当前列搬到指定方向的另一块屏

布局

Mod+T          浮动和平铺来回切
Mod+Shift+T    在浮动层和平铺层之间跳焦点
Mod+G          当前列变成标签页模式
Mod+F          列宽拉满
Mod+Shift+F    全屏
Mod+Space      轮流切预设列宽
Mod+- 和 Mod+= 列宽减 5 个点 加 5 个点
Mod+Shift+=   窗口高度还原
Mod+,          把旁边窗口吸进当前列
Mod+.          把当前窗口从列里踢出去

工作区

Mod+1 到 Mod+9        直接跳
Mod+Shift+1 到 9      把当前列丢过去

鼠标滚轮

Mod+滚轮上下           切工作区
Mod+Ctrl+滚轮上下      带着当前列切工作区
Mod+滚轮左右           换列，Mod+Shift+滚轮上下也行
Mod+Ctrl+滚轮左右      搬列，Mod+Ctrl+Shift+滚轮上下也行

截图

Mod+Shift+S 或 Print   圈一块截
Ctrl+Print             全屏截
Alt+Print              只截当前窗口

硬件键

音量键                 加减 5 个点，静音键切换
亮度键                 调外接屏的硬件背光，锁屏也能用

壁纸选择器里面

Mod+W 呼出之后

打字              边打边筛，按文件名和标题匹配
Enter             直接上当前第一张
下方向键          从搜索框跳进缩略图格子
上方向键          在第一行按上，焦点回搜索框
Ctrl+R            当前能看见的里面随机来一张
Esc               打了字先清空，没打字直接关
右键或中键        跟 Esc 一个逻辑
点面板外面        关闭
色调标签          点 Red Blue Mono 这些小胶囊就只看那个色调，分析是后台跑的
卡片右上角小圆点  悬停能看到这张图被判成了什么色调

终端命令

直接敲 nyxniri 回车进控制面板，什么都不选退出就是了，想一步到位就用下面的子命令

装和部署

nyxniri install full     完整安装，依赖配置壁纸全来，每步有勾选
nyxniri install config   只铺配置文件，不碰依赖和壁纸
nyxniri wallpapers       补下壁纸包

更新

nyxniri update           拉最新代码，问你要不要重新铺配置
nyxniri update --force   更新完直接强制重铺
nyxniri update --no-deploy   只更代码，配置一点不动
nyxniri update --to 某个tag   更到指定版本，用于回退

快照和回滚

nyxniri snapshot 写点备注    存一份当前部署状态的快照
nyxniri list                 看有哪些快照
nyxniri rollback             交互选一份恢复
nyxniri rollback 序号        直接恢复指定那份
nyxniri snapshot delete      交互勾选删除

动手卸载改配置之前先打个快照

预设

预设就是同一套配置的不同风味，比如 kitty 默认带一个透明的

nyxniri preset kitty list        看有哪些，带星号的是现在用的
nyxniri preset kitty apply transparent   切过去
nyxniri preset kitty apply default       回默认
nyxniri preset kitty save 名字   把现在的配置存成自己的预设
nyxniri preset kitty edit 名字   用编辑器改自己的预设
nyxniri preset kitty delete 名字 删掉自己的，官方的只读

换应用名就对其他配置生效，niri noctalia fish 这些都可以

检查和卸载

nyxniri doctor       全身体检，哪里不对会指出来
nyxniri bug          生成一份完整的问题报告，发 issue 前跑这个
nyxniri test         沙箱里自己装一遍，不碰真实配置

nyxniri uninstall            交互式卸载，会问你怎么处理配置
nyxniri uninstall restore    卸载并还原成装之前的配置
nyxniri uninstall purge      全部删干净，快照也不留
nyxniri purge                同上

扩展模块

这四个都是同一个套路，后面接 install 或 status 或 uninstall

nyxniri greeter      登录管理器，装了开机就是 Noctalia 的登录界面
nyxniri fcitx        输入法皮肤，Material You 配色的 NyxMellow
nyxniri gtk          GTK 应用主题，跟壁纸走
nyxniri fisher       fish 插件管理

主题

nyxniri theme toggle    深浅色对调，GTK 和终端一起变
nyxniri theme dark      直接设深色
nyxniri theme light     直接设浅色
nyxniri theme sync      按现在的壁纸重新取一遍色
nyxniri theme status    看现在是深是浅

其他

nyxniri deps         依赖管理
nyxniri apps         推荐应用，Nautilus 任务管理器 Rime 这些
nyxniri help         命令列表

终端里的小工具

装完自带一套 fish 函数，重启终端或在已开的会话里 source 一下配置就能用

查手册

nyxhelp          总目录
nyxhelp cli      命令相关
nyxhelp keys     桌面按键
nyxhelp pkg      包管理
nyxhelp proxy    代理

代理

proxy_on             走默认 7890 端口开代理，提示符会亮起来
proxy_on 1080        指定端口
proxy_off            关掉
proxy_status         测一下通不通，延迟多少，出口 IP 是哪

包管理

up                   全量更新，paru yay shelly 谁在用谁，坏了自动换备胎
in 软件包            装东西，不带参数就进搜索模式
se 关键字            模糊搜索，fzf 选完直接装，前面加 aur 或 pac 可以只搜一个源
un 关键字            模糊搜已装的包，fzf 选完卸载
clean                扫一遍大缓存和垃圾日志，加 --auto 不用确认
ls                   换成了 eza，带图标
clear                修过的版本，连滚动缓冲一起清干净

进阶

桌面动作都能拿命令行触发，写脚本用得上

niri msg action toggle-overview          开概览
niri msg action focus-column-left        焦点去左列
niri msg action load-config-file         重载配置

noctalia msg wallpaper-random            随机壁纸
noctalia msg wallpaper-set 路径          设壁纸
noctalia msg wallpaper-get               问当前壁纸在哪
noctalia msg panel-toggle clipboard      开关某个面板
noctalia msg session lock                锁屏

几句备忘

键位都写在 .config/niri/binds.kdl，想改就改那里
自己的东西放 .config/niri/__custom__.kdl，系统更新不会动它
卸载回滚这类事情之前，先 snapshot"""


def _parse_palette():
    surface = (0.12, 0.13, 0.18)
    on_surface = (0.95, 0.96, 0.99)
    on_surface_var = (0.68, 0.72, 0.78)
    primary = (0.42, 0.70, 1.00)
    try:
        import os as _os
        starship = _os.path.expanduser("~/.cache/noctalia/starship-palette.toml")
        if _os.path.isfile(starship):
            with open(starship, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith(("#", "[")):
                        k, v = [x.strip() for x in line.split("=", 1)]
                        v = v.strip("\"'")
                        if len(v) == 6:
                            rgb = tuple(int(v[i:i+2], 16) / 255.0 for i in (0, 2, 4))
                            if k in ("surface0", "surface1", "base"):
                                surface = rgb
                            elif k in ("text", "white"):
                                on_surface = rgb
                            elif k in ("subtext0", "subtext1"):
                                on_surface_var = rgb
                            elif k in ("blue", "sapphire", "primary"):
                                primary = rgb
    except Exception:
        pass
    return {"surface": surface, "on_surface": on_surface, "on_surface_var": on_surface_var, "primary": primary}


def _gdk(rgb, a=1.0):
    return Gdk.RGBA(red=rgb[0], green=rgb[1], blue=rgb[2], alpha=a)


class CheatsheetWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_name("NyxNiriCheatsheet")
        self.palette = _parse_palette()

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        GtkLayerShell.set_exclusive_zone(self, -1)
        for edge in (GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT,
                     GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM):
            GtkLayerShell.set_anchor(self, edge, True)
            GtkLayerShell.set_margin(self, edge, 0)

        self.set_app_paintable(False)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                        halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.add(outer)

        dialog = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        dialog.set_size_request(720, 600)
        dialog.override_background_color(Gtk.StateFlags.NORMAL, _gdk(self.palette["surface"]))
        outer.add(dialog)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.override_background_color(Gtk.StateFlags.NORMAL, _gdk(self.palette["surface"]))
        header.set_border_width(16)
        title = Gtk.Label(label="NyxNiri")
        title.override_color(Gtk.StateFlags.NORMAL, _gdk(self.palette["on_surface"]))
        title.set_xalign(0.0)
        fd = Pango.FontDescription.from_string("Inter Bold 16")
        title.override_font(fd)
        sub = Gtk.Label(label="快捷键与命令")
        sub.override_color(Gtk.StateFlags.NORMAL, _gdk(self.palette["on_surface_var"]))
        sub.set_xalign(0.0)
        sub.set_margin_start(8)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        hint = Gtk.Label(label="Esc 关闭")
        hint.override_color(Gtk.StateFlags.NORMAL, _gdk(self.palette["on_surface_var"]))
        fd2 = Pango.FontDescription.from_string("JetBrainsMono 9")
        hint.override_font(fd2)
        header.pack_start(title, False, False, 0)
        header.pack_start(sub, False, False, 0)
        header.pack_start(spacer, True, True, 0)
        header.pack_end(hint, False, False, 0)
        dialog.pack_start(header, False, False, 0)

        sep = Gtk.Box()
        sep.set_size_request(-1, 1)
        sep.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(red=1, green=1, blue=1, alpha=0.08))
        dialog.pack_start(sep, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.override_background_color(Gtk.StateFlags.NORMAL, _gdk(self.palette["surface"]))
        scroll.set_border_width(16)

        text_buf = Gtk.TextBuffer()
        text_buf.set_text(CONTENT)
        text_view = Gtk.TextView(buffer=text_buf)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_left_margin(4)
        text_view.set_right_margin(4)
        text_view.set_pixels_above_lines(2)
        text_view.set_pixels_below_lines(2)
        text_view.override_color(Gtk.StateFlags.NORMAL, _gdk(self.palette["on_surface"]))
        text_view.override_background_color(Gtk.StateFlags.NORMAL, _gdk(self.palette["surface"]))
        mono = Pango.FontDescription.from_string("JetBrainsMono 11")
        text_view.override_font(mono)
        scroll.add(text_view)
        dialog.pack_start(scroll, True, True, 0)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK)
        self.connect("button-press-event", self.on_button_press)
        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", lambda w: Gtk.main_quit())

        self.show_all()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        return True

    def on_button_press(self, widget, event):
        if event.button == 1:
            wa = self.get_allocation()
            da = self.get_child().get_child().get_allocation()
            if da.width > 0 and da.height > 0:
                dx = (wa.width - da.width) // 2
                dy = (wa.height - da.height) // 2
                if not (dx <= event.x <= dx + da.width and dy <= event.y <= dy + da.height):
                    Gtk.main_quit()
        return True


def main():
    import signal
    signal.signal(signal.SIGINT, lambda s, f: Gtk.main_quit())
    signal.signal(signal.SIGTERM, lambda s, f: Gtk.main_quit())
    CheatsheetWindow()
    Gtk.main()


if __name__ == "__main__":
    main()