# 四象限待办悬浮窗

信创工作机（麒麟 V10 SP1 / aarch64 / Wayland）个人待办工具：无边框半透明始终置顶悬浮窗，以「重要 × 紧急」四象限组织任务，支持目录关联一键打开、截止提醒、AI 粘贴总结。

## 运行

```bash
/usr/bin/python3 main.py
```

桌面快捷方式（可选）：`.desktop` 文件必须有可执行权限，直接复制不带权限会以文本方式打开。用 `install` 安装：

```bash
install -m 755 todo-quadrant.desktop ~/.local/share/applications/   # 开始菜单
install -m 755 todo-quadrant.desktop ~/桌面/                        # 桌面双击
```

## 环境要求（本机已具备，无需安装）

- `python3`（3.8）、`python3-pyqt5`、系统 Qt5（5.15）
- 可选：`peony`（打开目录）、`notify-send`（桌面通知）

## 显示说明

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
- **设置**：右上角「⚙」配置 AI 接口（默认 MiMo：`https://api.xiaomimimo.com/v1` / `mimo-v2.6-flash`）。项目根存在 `api-key.txt` 时首启会自动导入 key。
- 拖动任务行到其它象限即可换象限；拖动顶部标题栏移动窗口；右下角拉伸大小。
- 截止时间到期：应用内标红 + `notify-send` 桌面通知（每 60 秒扫描一次）。
- 「—」收起为窄条，「展开」恢复；右键悬浮窗空白：新建 / AI / 设置 / 收起 / 退出。

## 项目结构

```
todo-quadrant/
├── main.py                      # 入口：环境变量(xcb/缩放/软渲染) → QApplication(fusion) → 悬浮窗
├── app/
│   ├── db.py                    # SQLite 数据层：tasks + settings 两表，全部读写经此处
│   ├── config.py                # 设置读写 + AI 接口默认值 + api-key.txt 首启导入
│   ├── ai.py                    # OpenAI 兼容调用(urllib) + 健壮 JSON 解析/降级
│   ├── remind.py                # QTimer 每 60s 扫描到期任务 → 应用内标红 + notify-send
│   └── ui/
│       ├── floating_window.py   # 悬浮窗容器：无边框/半透明/置顶/收起/拖动/尺寸状态记忆
│       ├── quadrant_view.py     # 2×2 四象限网格 + 象限标题栏 + 拖拽换象限 + 空态提示
│       ├── task_row.py          # 单个任务行：勾选/标题/截止/📁/✎/✕ + 拖拽源
│       ├── task_dialog.py       # 任务新建/编辑表单（象限/目录/截止时间，支持 AI 预填）
│       ├── ai_dialog.py         # 粘贴文本 → 后台线程调 AI → 结果预填
│       ├── settings_dialog.py   # AI 接口三要素(base_url/key/model)配置
│       └── message.py           # 深色确认/提示对话框（替代会被系统接管的 QMessageBox）
├── resources/
│   └── style.qss                # 全局样式唯一来源：半透明圆角 + 四象限配色 + 深色控件
├── scripts/                     # 测试与验证（均不依赖真实显示，offscreen 可跑）
│   ├── smoke_test.py            #   主自测：数据层/UI构造/状态机/按钮行为，须输出 SMOKE OK
│   ├── mock_ai_test.py          #   AI 链路：本地起 mock 服务验证请求/解析，须 MOCK_AI OK
│   ├── render_capture.py        #   离屏渲染主窗口为 PNG（布局/配色回归核对）
│   ├── capture_real.py          #   目标设备上抓真实窗口外观
│   ├── capture_delete_real.py   #   目标设备上抓删除确认框（对话框样式验收）
│   ├── capture_dialogs.py       #   离屏渲染对话框 PNG
│   ├── spike_window.py          #   人工核验「置顶+半透明+拖动」的最小窗口
│   └── x11_above_test.py        #   读取 _NET_WM_STATE 验证置顶机制
├── todo-quadrant.desktop        # 桌面快捷方式（复制到 ~/.local/share/applications/ 使用）
├── DESIGN.md                    # 设计文档：需求/选型/架构/数据模型/风险
├── AGENTS.md                    # 开发规范：目标设备约束、硬性规则、完成标准
└── README.md                    # 本文件
```

数据流：`ui/*` → `db.py` → SQLite；`ai_dialog` → `ai.py` → OpenAI 兼容接口；`remind` → `notify-send` / 应用内标红。

运行期数据在 `~/.config/todo-quadrant/todo.db`（不入库）；仓库内不出现运行时数据。
