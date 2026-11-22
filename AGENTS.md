# AGENTS.md — 四象限待办悬浮窗

给在本仓库工作的 agent / 开发者的约束与流程。**开发机与运行机可能不同**：代码可以在任意机器上写，但最终验收环境只有一种（见下）。架构与设计理由见 [DESIGN.md](DESIGN.md)，用法见 [README.md](README.md)，本文件不重复它们。

## 目标设备（唯一验收环境）

华为擎云 L420x / 麒麟 9000C（aarch64）/ 银河麒麟桌面 V10 SP1：

- **UKUI Wayland 会话 + XWayland**。Qt 置顶/透明 windowFlags 在原生 Wayland 下被合成器忽略，应用必须走 `QT_QPA_PLATFORM=xcb`（main.py 已强制，勿改默认值）。
- **无可用 GPU**（maleoon 核显不对普通客户端开放）。只用 Qt Widgets 软渲染；main.py 已设 `LIBGL_ALWAYS_SOFTWARE=1`。
- **系统 Python 3.8 + 系统 PyQt5（Qt 5.15.13）**，`notify-send`、`peony`、`wmctrl` 在位。
- **kysec 安全策略**拒绝执行 home 下的 shell 脚本 → 启动方式固定为 `python3 main.py`，不写 home 下的启动脚本。

## 硬性开发约束

1. **零第三方 pip 依赖**。只用 Python 标准库 + PyQt5。新功能先想标准库方案。
2. **Python 3.8 兼容**。开发机可能是新版 Python，禁用 3.9+ 语法（match、`X | Y` 类型标注等）。
3. **提示/确认一律用 `app/ui/message.py` 的 `confirm()` / `warn()`**。QMessageBox 会被 UKUI 平台主题的「原生对话框助手」接管、绕过 QSS 渲染成白底白字——这是真机实测的坑，原因写在 message.py 注释里。同理 `app.setStyle("fusion")`（main.py）勿移除。
4. **样式唯一来源是 `resources/style.qss`**。改外观改 QSS，不在代码里散落 setStyleSheet（行内状态变色等个别动态场景除外）。
5. **窗口尺寸状态机**：收起态的小尺寸永远不得写回「展开尺寸」记忆；展开下限 520×340，恢复时钳位。floating_window.py 中 `_save_state / _apply_collapsed` 的两处防护是修过的 bug，勿退回。
6. **`api-key.txt` 是用户密钥**：已在 .gitignore；任何代码、日志、测试不得读取并打印其内容（`config.auto_load_api_key` 是唯一合法读取点）。AI 默认 base_url / model 的唯一来源是 config.py 的 `DEFAULT_*`，改默认值只改那里。

## 完成标准（每次改动收尾前按序跑完）

```bash
python3 -m py_compile main.py app/*.py app/ui/*.py scripts/*.py   # 全量编译
QT_QPA_PLATFORM=offscreen python3 scripts/smoke_test.py           # 必须输出 SMOKE OK
```

- 改了 AI 调用：再跑 `python3 scripts/mock_ai_test.py`（本地 mock，必须 `MOCK_AI OK`）。
- 以上在**任意开发机**都应通过（offscreen 不依赖显示环境）。失败即改动未完成，修到通过为止。
- **视觉验收只能在目标设备上做**：`scripts/capture_real.py`（真实窗口）、`scripts/capture_delete_real.py`（对话框）生成 PNG 截图后人工核对。开发机上不许以离屏渲染结果宣称「视觉效果正确」。
- 测试用临时数据库：设 `TODO_QUADRANT_DB` 指向临时文件，测试结束删除；不得动 `~/.config/todo-quadrant/todo.db` 里的用户真实数据。

## 数据与配置

- SQLite 单文件（表结构见 app/db.py 的 `init()`），改表结构必须写迁移逻辑（老用户已有数据）。
- 设置项走 settings 表 + config.py 访问函数，新增 key 同时在 config.py 登记默认值。
