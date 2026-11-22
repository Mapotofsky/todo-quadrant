# 四象限待办悬浮窗 —— 软件设计与技术选型文档

> 版本：v1.0（待评审）
> 目标机器：华为擎云 L420x / 麒麟 9000C（aarch64）/ 银河麒麟桌面 V10 SP1
> 本文记录麒麟版原始设计。Windows 运行与打包见第十四节。

---

## 一、项目目标与范围

做一个**本机个人使用**的轻量桌面待办工具，以「重要 × 紧急」四象限组织任务，并以**常驻、可收起、半透明、始终置顶**的悬浮窗形态运行。除手工录入外，支持把一段聊天/文本粘贴进输入框、由**用户自配的 OpenAI 兼容 AI 接口**自动总结成一条结构化任务；任务可**关联本机目录**并可一键打开；支持**截止时间与到期提醒**。

非目标（明确不做，避免范围蔓延）：

- 不做云同步 / 多端 / 账号体系（纯本地单机）。
- 不做团队协作、看板、甘特图、统计报表。
- 不做移动端。
- 不内置任何 AI 服务，AI 由用户自备接口（可选，缺省时可纯手工使用）。

---

## 二、需求确认（已与你逐项确认）

| 维度 | 结论 |
|---|---|
| AI 接口 | OpenAI 兼容接口（`base_url` + `api_key` + `model` 三要素，覆盖 DeepSeek/OpenAI/Moonshot/本地 Ollama 等） |
| 象限分级 | 重要 / 紧急 各「高 / 低」二元，经典 2×2 四象限 |
| 悬浮窗形态 | 悬浮窗即完整四象限；「收起」= 缩成一条窄条/圆点；展开/收起点按切换，**始终置顶、半透明** |
| 任务字段 | 标题、备注、重要(高/低)、紧急(高/低)、关联目录、完成状态、**截止时间 + 到期提醒** |
| 启动方式 | 手动启动（先跑通主流程，暂不做开机自启） |
| 技术栈 | Python + **系统 PyQt5**（复用本机 Qt5.15.13，零 pip 依赖） |

---

## 三、本机环境探测结论

在开发机上实测（非推断）得到的事实：

| 项 | 结果 |
|---|---|
| 架构 / 内核 | `aarch64`，`5.10.97-32-9000c`（KylinOS） |
| 发行版 | 银河麒麟桌面 V10 SP1（`ID_LIKE=debian`，glibc 2.31） |
| 内存 | 15 GiB |
| 显示会话 | **Wayland**（`XDG_SESSION_TYPE=wayland`，`DESKTOP_SESSION=ukui-wayland`，合成器为 UKUI/KWin），同时存在 XWayland（`DISPLAY=:0`） |
| 系统 Python | `/usr/bin/python3` = **3.8.10** |
| 系统 Qt | **Qt5 5.15.13** + `python3-pyqt5 5.15.4` + `python3-pyqt5.sip` 已安装，**实测 `import PyQt5.QtWidgets` 成功**（运行时 qVersion=5.15.13） |
| Qt5 平台插件 | `/usr/lib/aarch64-linux-gnu/qt5/plugins/platforms/` 同时含 `libqxcb.so` 与 `libqwayland-*.so`、`UKUIKWinQpaPlugin.so` |
| GTK | GTK3 3.24.23 + `python3-gi` 可用（备选，非首选） |
| uv | `~/.local/bin/uv` 0.12.9（aarch64），托管 CPython 3.12.14 在位 |
| Node | v22.23.2 / npm 12.0.2（本项目不需要） |
| sqlite3 | Python 内置，SQLite 3.31.1 |
| 打开目录 | `xdg-open` / `gio` / `peony`（默认文件管理器 `peony.desktop`） |
| 通知 | `notify-send` / `gdbus` / `dbus-send` / `busctl` 均在，`DBUS_SESSION_BUS_ADDRESS` 正常 |
| 屏幕 | 2880×1920（HiDPI，需在首日验证缩放） |
| 辅助 | `xdotool` / `wmctrl` 在位（兜底置顶用） |
| 安全约束 | kysec 拒绝执行 home 下的可执行脚本 → 以 `python3 main.py` 方式启动，避免 home 下 shell 启动脚本 |

**关键结论**：本机是 Wayland 会话，但 UI 工具链（Qt5 + PyQt5）是**系统原生、零安装、与 UKUI 同源**的现成资产，是「轻量化」的最优解。

---

## 四、同类先例调研（借鉴什么、不照抄什么）

调研到的相关先例（仅作思路参考，不基于其打补丁）：

- [eis-quads](https://github.com/Melokeo/eis-quads)：Windows 版四象限任务面板，验证了「四象限网格 + 任务卡片」的交互范式。
- [郭飞飞/focus-board](https://gitee.com/guocdfeifei/focus-board)：四象限 + 悬浮磁贴的离线桌面效率工具，验证了「悬浮 + 四象限 + 本地存储」的组合可行。
- 多方资料确认：**Qt 的置顶 `windowFlags` 在原生 Wayland 下会被合成器忽略**（见 [The Wayland Shift](https://runebook.dev/en/docs/qt/qml-qtwayland-compositor-qtshell-qtshellchrome/windowFlags)），因此本机必须走 `xcb`（XWayland）路线；这与本机 Electron/Chromium 既有经验 `--ozone-platform=x11` 完全一致。
- UKUI 面板支持 SNI 托盘协议（见 [UKUI 托盘 SNI 指南](http://mp.weixin.qq.com/s?__biz=Mzg2MDc5MDU1OQ==&mid=2247501560&idx=1&sn=3000a765aae909b9a6b80d45091d6e5b)），但本项目用「收起成小条」绕开托盘依赖，托盘仅作可选项。

**边界声明**：上述项目多为 Windows/Electron/多端定位，与本机「aarch64 + Wayland + 轻量」约束不符，故只借鉴交互范式与四象限配色约定，**从零实现**，不复用其代码。

---

## 五、技术选型与理由

### 5.1 选定方案

| 层 | 选择 | 理由 |
|---|---|---|
| 语言 / 运行时 | 系统 `/usr/bin/python3`（3.8.10） | 与系统 PyQt5 绑定天然匹配，零安装；本应用不需要 3.9+ 特性 |
| GUI 框架 | **PyQt5（系统 `python3-pyqt5`，绑定系统 Qt 5.15.13）** | ① 已装且实测可用；② 与 UKUI 同源 Qt，兼容性最好；③ 对「无边框 + 透明 + 置顶 + 拖动」支持最成熟；④ QSS 一键美化；⑤ 零额外体积 |
| 显示后端 | **强制 `QT_QPA_PLATFORM=xcb`（XWayland）** | 置顶/透明在原生 Wayland 被忽略，xcb 下 `_NET_WM_STATE_ABOVE` + ARGB 视觉可靠（与本机既有 x11 经验一致） |
| 数据存储 | SQLite（Python 内置 `sqlite3`），单文件 | 轻量、零依赖、事务可靠 |
| AI HTTP | Python 标准库 `urllib.request` | 短请求无并发，够用；避免引入 `requests/httpx` |
| 通知 | 应用内悬浮提醒（主）+ `notify-send`（辅，可选） | 应用内提醒可靠且不依赖桌面通知；notify-send 走会话 D-Bus 与显示协议无关 |
| 打开目录 | `QDesktopServices.openUrl(QUrl.fromLocalFile(...))` → 系统默认 `peony` | 原生、零依赖 |
| 第三方 pip 依赖 | **0 个** | 全部复用系统 Qt5 + Python 标准库 + 系统 `notify-send` |

### 5.2 备选（已评估，不采用）

| 方案 | 不采用原因 |
|---|---|
| Electron / Chromium 系 | 重；本机 maleoon 核显对普通客户端 GPU 易出问题，需软渲染，违背「轻量化」 |
| Tauri | 需 Rust 工具链（本机无），且 webview 依赖 webkit2gtk，风险高 |
| PySide6 / Qt6 | 更重、体积更大；Qt6 在本机 UKUI 上的置顶/透明未验证；glibc 2.31 勉强满足但无必要 |
| uv 3.12 + PyQt5 wheel | 会再带一份捆绑 Qt5（约数十 MB），且捆绑版本(5.15.2)低于系统(5.15.13)，属重复引入 |
| GTK3 / PyGObject | 无边框+置顶+透明在 GTK 下实现更繁琐、代码量大，美化与开发效率不如 Qt |

---

## 六、系统架构

单一进程、单一悬浮窗，模块化但刻意保持精简：

```
todo-quadrant/
├── main.py                  # 入口：设置 xcb/缩放环境变量 → QApplication → 托盘/悬浮窗
├── app/
│   ├── __init__.py
│   ├── config.py            # 配置读写（SQLite settings 表：AI 接口、窗口位置/状态等）
│   ├── db.py                # SQLite 访问层（tasks + settings）
│   ├── ai.py                # OpenAI 兼容调用 + 健壮 JSON 解析 + 降级
│   ├── remind.py            # QTimer 到期扫描 + 应用内提醒 + notify-send
│   └── ui/
│       ├── __init__.py
│       ├── floating_window.py  # 悬浮窗容器：展开/收起状态机、拖动、置顶、透明、圆角
│       ├── windows_tray.py     # Windows 托盘常驻与通知
│       ├── linux_tray.py       # 麒麟托盘常驻、显示/新建/退出
│       ├── quadrant_view.py    # 2×2 四象限网格 + 任务列表 + 跨象限拖拽
│       ├── task_row.py         # 单条任务卡片（勾选/打开目录/编辑/删除/逾期标红）
│       ├── task_dialog.py      # 手动新建 / 编辑
│       ├── ai_dialog.py        # 粘贴文本 → AI 总结 → 预填确认
│       └── settings_dialog.py  # AI 接口三要素配置
├── resources/
│   ├── todo-quadrant.png    # 应用图标（Linux 启动器/托盘、Windows 运行时）
│   └── style.qss            # 全局样式（圆角、半透明、四象限配色）
├── packaging/
│   ├── windows/             # PyInstaller + Inno Setup 安装包
│   └── linux/               # 用户级 tar.gz 安装包构建/安装/卸载
├── todo-quadrant.desktop    # 桌面快捷方式模板（Exec=python3 main.py，可选）
├── README.md
└── DESIGN.md                # 本文档
```

数据流：`ui` → `db` → SQLite；`ai_dialog` → `ai`（urllib）→ 外部 API；`remind`（QTimer）→ `ui`/`notify-send`。

---

## 七、数据模型（SQLite）

麒麟库文件为 `~/.config/todo-quadrant/todo.db`，Windows 库文件为
`%LOCALAPPDATA%\TodoQuadrant\todo.db`。Windows 新位置尚无库时，通过 SQLite
备份接口迁移旧默认位置的任务和设置，原库保留。

```sql
CREATE TABLE tasks (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  title        TEXT    NOT NULL,
  note         TEXT    DEFAULT '',
  important    INTEGER NOT NULL DEFAULT 0,   -- 1=重要, 0=不重要
  urgent       INTEGER NOT NULL DEFAULT 0,   -- 1=紧急, 0=不紧急
  dir_path     TEXT,                          -- 关联目录绝对路径（可空）
  due_at       TEXT,                          -- ISO 'YYYY-MM-DD HH:MM'（可空）
  done         INTEGER NOT NULL DEFAULT 0,
  reminded     INTEGER NOT NULL DEFAULT 0,    -- 到期提醒是否已发，避免重复
  sort_order   INTEGER NOT NULL DEFAULT 0,    -- 象限内手动排序
  created_at   TEXT    NOT NULL,
  completed_at TEXT
);
CREATE INDEX idx_tasks_open ON tasks(done, important, urgent);

CREATE TABLE settings (
  key   TEXT PRIMARY KEY,
  value TEXT
);
```

- 象限由 `important`/`urgent` **派生**，不单独存储，避免不一致：

  | | 紧急=1 | 紧急=0 |
  |---|---|---|
  | **重要=1** | Q1（重要且紧急） | Q2（重要不紧急） |
  | **重要=0** | Q3（不重要但紧急） | Q4（不重要不紧急） |

- `settings` 关键键：`ai_base_url` / `ai_api_key` / `ai_model` / `ai_system_prompt` / `window_geometry` / `collapsed` / `remind_enabled` / `remind_lead_minutes`。

**安全说明**：`ai_api_key` 明文存于本机 SQLite（个人单机可接受），文档与 README 中明示。

---

## 八、UI / 交互设计

### 8.1 悬浮窗（`floating_window.py`）

- 窗口标志：`Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`，配合 `setAttribute(WA_TranslucentBackground)`，QSS 圆角 + 半透明底色。
- 拖动：无边框，在顶部手柄区（及空白处）实现 `mousePressEvent`/`mouseMoveEvent` 拖动整窗；记忆位置。
- 置顶兜底：若 `_NET_WM_STATE_ABOVE` 在个别场景失效，用 `wmctrl -r <win> -b add,above` 或 `X11BypassWindowManagerHint` 兜底（spike 阶段验证）。
- **展开态**：2×2 四象限网格（见下）。
- **收起态**：一条细长半透明窄条，仅显示「＋快速新建」「进行中任务数」「展开」三个元素；点按展开。

### 8.2 四象限配色（经典 Eisenhower 约定）

| 象限 | 语义 | 配色 |
|---|---|---|
| Q1 重要且紧急 | 立即做 | 红（半透明） |
| Q2 重要不紧急 | 计划做 | 蓝（半透明） |
| Q3 不重要但紧急 | 委派/尽快 | 橙（半透明） |
| Q4 不重要不紧急 | 可搁置 | 灰绿（半透明） |

布局：左上 Q1、右上 Q2、左下 Q3、右下 Q4（横轴=紧急度，纵轴=重要度）。

### 8.3 任务卡片（`task_item.py`）

- 每张卡片：完成勾选框、标题（完成后划线置灰）、逾期/临近日期标红、📁 按钮（有关联目录时显示，点击打开）、悬停显示「编辑/删除/移入其他象限」。
- 交互：
  - **勾选** = 标记完成（移入对应象限底部「已完成」折叠区或直接灰显，具体在 M1 定稿）。
  - **拖拽到另一象限** = 自动改写 `important/urgent`（符合直觉）。
  - 右键菜单：编辑、删除、快速移入 Q1–Q4、打开目录、复制标题。
- 排序：未完成按 `sort_order`（可手动上移/下移），逾期项自动置顶标红；完成项沉底。

### 8.4 新建任务（手动 & AI）

- **手动**（`task_dialog.py`）：标题、备注、重要/紧急开关（或四象限单选）、截止时间（`QDateTimeEdit`）、关联目录（`QFileDialog.getExistingDirectory` + 可手填/粘贴路径）。
- **AI 粘贴**（`ai_dialog.py`）：大文本框粘贴原始聊天/文本 → 点击「总结为任务」→ 调用 AI → 返回结构化结果**预填到同一表单供确认/修改** → 保存。AI 失败或未配置时自动降级为手动编辑，原文保留在备注中。

### 8.5 全局样式（`style.qss`）

无边框、圆角、半透明背景、四象限柔和配色、简洁字体，全部走 QSS，不引入图片资源。

---

## 九、AI 总结流程（`ai.py`）

1. **配置**（`settings_dialog.py`）：`base_url`（如 `https://api.deepseek.com/v1`）、`api_key`、`model`（如 `deepseek-chat`），可选自定义 system prompt。
2. **请求**：`POST {base_url}/chat/completions`，`urllib.request`，超时 30s，`temperature≈0.2`。
   - System prompt 示例：
     > 你是任务提炼助手。把用户粘贴的聊天/文本提炼成一条待办任务，只输出 JSON：
     > `{"title":"不超过20字的任务标题","note":"一句话补充(可空字符串)","important":true或false,"urgent":true或false,"due_at":"YYYY-MM-DD HH:MM"或null}`
     > 不要输出任何其它内容。
   - User message = 用户粘贴的原文。
3. **解析（健壮）**：先整体 `json.loads`；失败则用正则抽取第一个平衡 `{...}` 再解析；再失败则把整段回复当作 `title` 降级。
4. **降级链**：未配置接口 → 提示去设置；网络/超时/解析失败 → 弹提示并进入手动表单，原文保留。
5. 结果进入 8.4 的预填确认表单，**人确认后才落库**（避免 AI 幻觉直接污染待办）。

可使用MIMO进行测试，api key保存在`api-key.txt`。

---

## 十、目录关联与打开

- 任务可选关联一个绝对目录（`dir_path`）。
- 打开：`QDesktopServices.openUrl(QUrl.fromLocalFile(path))`，交由系统默认 `peony` 打开；异常时回退 `xdg-open`。
- 选择：文件对话框选目录，或直接粘贴/输入路径；保存时做存在性校验并给出轻提示。

---

## 十一、截止时间与到期提醒（`remind.py`）

- 单一 `QTimer`（每 60s）扫描「未完成 && 有 due_at」的任务。
- 判定：`due_at` 已过（或按 `remind_lead_minutes` 提前）且 `reminded=0` → 触发提醒，置 `reminded=1`。
- 提醒形态（两级）：
  1. **应用内**（可靠）：悬浮窗收起态闪烁高亮 + 展开态该任务标红置顶；任务卡片日期变红。
  2. **桌面通知**（可选、best-effort）：`subprocess` 调 `notify-send`（本机已装，走会话 D-Bus）。
- 逾期未完成项持续红色显示，直至完成或改期。

---

## 十二、关键技术风险与首日验证（Spike）

| # | 风险 | 影响 | 验证/缓解 |
|---|---|---|---|
| 1 | `xcb` 下 `WindowStaysOnTopHint` + `WA_TranslucentBackground` 是否在 UKUI/KWin-Wayland 下真正「置顶 + 半透明」 | 核心体验 | 首日写 20 行 spike：一个无边框半透明置顶小窗，目测置顶/透明/拖动；失败则启用 `wmctrl`/`X11BypassWindowManagerHint` 兜底 |
| 2 | HiDPI 2880×1920 下缩放（XWayland 对 Qt5 的 scale factor） | 窗口过小/发虚 | 测试 `QT_AUTO_SCREEN_SCALE_FACTOR` / `QT_SCALE_FACTOR` 组合，锁定最清晰者并写入环境变量 |
| 3 | maleoon 无 GPU：Qt 是否误走 GL 路径 | 闪退/花屏 | 本项目纯 Widgets 无 GL；必要时 `LIBGL_ALWAYS_SOFTWARE=1` 兜底 |
| 4 | 桌面通知在 Wayland 会话是否送达 | 次要（有应用内提醒兜底） | spike 里跑一次 `notify-send` 观察 |
| 5 | Python 3.8 EOL | 长期维护 | 仅个人本地使用，可接受；代码保持 3.8 兼容，不引入需 3.9+ 的依赖 |

> 若 Spike #1 失败且兜底也无法达到「始终置顶」的可用体验，我会回到你这里重新评估技术路线（这是本方案最大的单点风险）。

---

## 十三、开发计划（里程碑）

| 里程碑 | 内容 | 验收标准 |
|---|---|---|
| **M0 首日 Spike** | 验证置顶/透明/拖动、HiDPI、通知；搭骨架 | 悬浮小窗稳定置顶半透明可拖动 |
| **M1 核心** | 数据层 + 四象限悬浮窗（展开/收起/拖动/透明/置顶）+ 手动增删改查 + 完成勾选 + 拖拽换象限 | 四象限可完整手工使用 |
| **M2 目录** | 目录关联 + 一键打开 | 📁 按钮能打开 `peony` 对应目录 |
| **M3 提醒** | 截止时间 + 应用内/桌面到期提醒 | 到期标红 + 通知 |
| **M4 AI** | OpenAI 兼容调用 + 配置界面 + 预填确认 + 降级 | 粘贴文本 → 生成 → 确认落库 |
| **M5 打磨** | QSS 美化、桌面快捷方式、README、整体自测 | 达到「简洁美观、操作直觉」 |

每个里程碑完成后向你展示、确认再进入下一阶段。

---

## 十四、启动与打包方式

- **麒麟启动**：在源码目录运行 `/usr/bin/python3 main.py`。
  - 环境变量在 `main.py` 内自设置（`QT_QPA_PLATFORM=xcb`、缩放因子等），无需外部脚本；规避 kysec 对 home 脚本的拦截。
  - 启动后常驻通知区域，默认不显示浮窗；单击托盘显示，关闭浮窗只隐藏。通知区域不可用时退回普通浮窗。
- **麒麟桌面快捷方式**（可选）：`scripts/install_linux_shortcut.py` 按当前源码位置生成。
- **麒麟安装包**：`packaging/linux/build.py` 生成用户级 tar.gz，`install.py` 安装到 `~/.local`，卸载时默认保留任务数据库；不引入系统级依赖或 shell 启动脚本。
- **Windows 启动**：`python main.py` 或安装后的开始菜单入口，默认通过原生 Qt 后端在系统托盘常驻。
- **Windows 安装包**：PyInstaller `onedir` 收集 Python、Qt 和 QSS，Inno Setup 负责安装、升级、快捷方式及卸载。SQLite 数据位于用户数据目录。

---

## 十五、依赖清单

- **系统包（本机已装，无需新增）**：`python3`(3.8)、`python3-pyqt5`(5.15.4)、`libqt5core5a`(5.15.13)、`notify-send`(libnotify-bin，可选)、`peony`/`xdg-open`(打开目录)、`wmctrl`/`xdotool`(置顶兜底，可选)。
- **Python 第三方 pip 包：无**。
- 全部使用 Python 标准库：`sqlite3` / `urllib.request` / `json` / `subprocess` / `os` / `datetime` / `re`。

---

## 十六、待确认 / 假设

1. **已完成任务**的处理：倾向「留在原象限底部灰显，可一键清理」；若你希望「完成后立即隐藏/移出」，实现时再定。
2. **提醒提前量**：默认到期即提醒；是否需要「提前 N 分钟提醒」可配（已在 settings 预留键）。
3. **AI 接口**：默认按 OpenAI 兼容实现；若你的服务商响应格式特殊，M4 前给我一个样例返回即可适配。
4. **窗口默认尺寸/位置**：默认靠屏幕右侧中部、约 640×420（展开态），首启后可拖动记忆。
5. **是否常驻开机自启**：本期不做，后续可加 `.desktop` 到 `~/.config/autostart/`。

---

*如无异议，请回复「确认」或指出要调整的点，我即从 M0（首日 Spike）开始实现。*
