# 四象限待办悬浮窗

支持 Windows x64 和银河麒麟 V10 SP1（aarch64 / UKUI Wayland）的个人待办工具。无边框半透明悬浮窗始终置顶，以「重要 × 紧急」四象限组织任务，支持目录关联、截止提醒和 AI 粘贴总结。

## Windows

使用安装包时，按简体中文向导选择安装目录，再从开始菜单启动「四象限待办」。安装包自带 Python 和 Qt。覆盖升级默认沿用上次安装的目录。可从开始菜单或 Windows「已安装的应用」打开简体中文卸载向导。

从源码开发时，在已有 Python 3.8 或更新版本及 PyQt5 的环境中进入仓库根目录运行：

```powershell
python main.py
```

- 启动后单击通知区域的「四象限待办」图标打开浮窗。若图标被 Windows 收纳，可在任务栏右下角的隐藏图标里找到。右键图标可「显示待办」「新建任务」「退出」。
- 按 Alt+F4 或在浮窗右键菜单选「隐藏到托盘」，浮窗隐藏并继续扫描到期任务。Esc 仍可取消对话框。通过托盘菜单的「退出」结束进程。系统托盘不可用时，启动会直接显示浮窗，关闭浮窗即退出。
- 任务和设置存于 `%LOCALAPPDATA%\TodoQuadrant\todo.db`，升级及默认卸载会保留它们。首次使用新位置时，若用户主目录下的 `.config/todo-quadrant/todo.db` 存在，应用会复制其中的任务和设置并保留旧库。可用 `TODO_QUADRANT_DB` 指定其它数据库路径。
- Qt 自动选择 Windows 原生后端。`TODO_QUADRANT_QPA` 仍可覆盖平台，`TODO_QUADRANT_SCALE` 可覆盖缩放。Windows 到期通知经系统托盘发送，横幅显示取决于系统通知设置。

### 构建 Windows x64 安装包

使用 Windows x64 Python 3.10（本机验证版本为 3.10.12）、Inno Setup 6.7.3 和 PowerShell。在仓库根目录执行以下命令，将最后一行的编译器路径换为实际的 `ISCC.exe` 位置。构建依赖仅安装在仓库内的虚拟环境。

```powershell
python -m venv .build/windows/venv
.\.build\windows\venv\Scripts\python.exe -m pip install -r packaging/windows/requirements.txt
.\packaging\windows\build.ps1 -Python .build/windows/venv/Scripts/python.exe -Iscc 'C:\path\to\ISCC.exe'
```

PyInstaller `onedir` 产物在 `.build/windows/dist/TodoQuadrant/`，安装包在 `dist/windows/`。构建脚本接受 `-Version` 指定版本号。编译器也可以单独解包到仓库的 `.build/windows/` 后指定其路径。详见 [Inno Setup 官方发布页](https://github.com/jrsoftware/issrc/releases/tag/is-6_7_3)。

简体中文语言文件随仓库提供，构建时与 Inno Setup 一起编译进安装包。语言文件来自 [Inno Setup 6.7.3 源码](https://github.com/jrsoftware/issrc/blob/is-6_7_3/Files/Languages/Unofficial/ChineseSimplified.isl)。

在有 Explorer 托盘的 Windows 桌面会话中运行 `python scripts/windows_test.py`，验证迁移、Windows 原生后端、托盘、Esc、后台提醒及无托盘回退。离屏冒烟测试可单独运行 `python scripts/smoke_test.py`。

## 银河麒麟

```bash
/usr/bin/python3 main.py
```

可从当前源码位置生成带执行权限的快捷方式：

```bash
/usr/bin/python3 scripts/install_linux_shortcut.py          # 开始菜单
/usr/bin/python3 scripts/install_linux_shortcut.py ~/桌面   # 桌面双击
```

- `python3`（3.8）、`python3-pyqt5`、系统 Qt5（5.15）
- 可选：`peony`（打开目录）、`notify-send`（桌面通知）

- Wayland 会话下自动强制 `QT_QPA_PLATFORM=xcb`（XWayland）以获得可靠的置顶/透明。
- 若窗口偏小/发虚，可设置缩放因子：

  ```bash
  TODO_QUADRANT_SCALE=2 /usr/bin/python3 main.py   # 或 1.5
  ```

- 数据存于 `~/.config/todo-quadrant/todo.db`。

## 用法

- 每个象限标题栏右侧「＋」直接在该象限新增；右上角「＋ 新建」全局新增。
- 每行任务右侧：📁 打开关联目录、✎ 编辑、✕ 删除；勾选框标记完成。
- **AI 粘贴**：点「AI 粘贴」→ 粘贴聊天/文本 →「总结为任务」→ 自动生成并预填，确认后保存。
- **设置**：右上角「⚙」配置 AI 接口（默认 MiMo：`https://api.xiaomimimo.com/v1` / `mimo-v2.6-flash`）。源码运行时可从项目根目录的 `api-key.txt` 自动导入尚未配置的密钥。密钥保存在本机 SQLite 设置表中。
- 拖动任务行到其它象限即可换象限；拖动顶部标题栏移动窗口；右下角拉伸大小。
- 每 60 秒扫描到期任务，应用内标红，并通过 Windows 托盘或麒麟的 `notify-send` 发送桌面通知。
- 「—」收起为窄条，「展开」恢复；右键悬浮窗空白：新建 / AI / 设置 / 收起 / 退出。

## 项目结构

```
todo-quadrant/
├── main.py                      # 入口：选择 Qt 平台 → QApplication(Fusion) → 托盘或悬浮窗
├── app/
│   ├── db.py                    # SQLite 数据层：tasks + settings 两表，全部读写经此处
│   ├── config.py                # 设置读写 + AI 接口默认值 + api-key.txt 首启导入
│   ├── ai.py                    # OpenAI 兼容调用(urllib) + 健壮 JSON 解析/降级
│   ├── remind.py                # QTimer 每 60s 扫描到期任务 → 应用内标红 + notify-send
│   └── ui/
│       ├── floating_window.py   # 悬浮窗容器：无边框/半透明/置顶/收起/拖动/尺寸状态记忆
│       ├── windows_tray.py      # Windows 托盘菜单、窗口显示和系统通知
│       ├── quadrant_view.py     # 2×2 四象限网格 + 象限标题栏 + 拖拽换象限 + 空态提示
│       ├── task_row.py          # 单个任务行：勾选/标题/截止/📁/✎/✕ + 拖拽源
│       ├── task_dialog.py       # 任务新建/编辑表单（象限/目录/截止时间，支持 AI 预填）
│       ├── ai_dialog.py         # 粘贴文本 → 后台线程调 AI → 结果预填
│       ├── settings_dialog.py   # AI 接口三要素(base_url/key/model)配置
│       └── message.py           # 深色确认/提示对话框（替代会被系统接管的 QMessageBox）
├── resources/
│   └── style.qss                # 全局样式唯一来源：半透明圆角 + 四象限配色 + 深色控件
├── scripts/                     # 测试、截图及 Linux 快捷方式生成
│   ├── smoke_test.py            #   主自测：数据层/UI构造/状态机/按钮行为，须输出 SMOKE OK
│   ├── windows_test.py          #   Windows 原生托盘、提醒、退出和迁移验证
│   ├── mock_ai_test.py          #   AI 链路：本地起 mock 服务验证请求/解析，须 MOCK_AI OK
│   ├── render_capture.py        #   离屏渲染主窗口为 PNG（布局/配色回归核对）
│   ├── capture_real.py          #   目标设备上抓真实窗口外观
│   ├── capture_delete_real.py   #   目标设备上抓删除确认框（对话框样式验收）
│   ├── capture_dialogs.py       #   离屏渲染对话框 PNG
│   ├── spike_window.py          #   人工核验「置顶+半透明+拖动」的最小窗口
│   └── x11_above_test.py        #   读取 _NET_WM_STATE 验证置顶机制
├── packaging/windows/           # PyInstaller 和 Inno Setup 构建配置
├── todo-quadrant.desktop        # Linux 桌面快捷方式模板
├── DESIGN.md                    # 设计文档：需求/选型/架构/数据模型/风险
├── AGENTS.md                    # 开发规范：目标设备约束、硬性规则、完成标准
└── README.md                    # 本文件
```

数据流为 `ui/*` → `db.py` → SQLite，`ai_dialog` → `ai.py` → OpenAI 兼容接口，`remind` → 应用内标红和系统通知。
