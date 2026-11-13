# Codex Project Display Fix

[English](#english) | [中文说明](#中文说明) · MIT License

## 中文说明

一个针对 Codex Desktop **项目文件夹与数据库记录仍在，但侧栏显示“没有项目”**的轻量修复工具。

### 适用情况与原理

在 Windows 版 Codex Desktop 26.1106.6628.0 的一个实际案例中，`state_5.sqlite` 的 `projects` 和 `project_roots` 表保留了项目，但 `.codex-global-state.json` 中的项目显示清单为空。
当前应用接受的项目对象需要 `rootPaths` 字段。仅恢复 ID、名称和时间，而把路径放在独立旧配置中的方案，可能无法被此版本识别。

本工具从使用者自己的数据库中读取项目，并恢复两个配置键：

- `local-projects`：补齐项目对象，包含 `rootPaths`。
- `project-order`：补回项目排序，保留现有顺序。

它保留项目原 ID、额外元数据和已有的有效路径；不从聊天工作目录猜测新项目，不重新分配聊天，不改会话数据库、置顶或侧栏偏好。不读取聊天正文，不联网。

**这是特定数据格式下的恢复办法，无法证明最初消失一定由升级 bug 引起，也不保证适用于所有 Codex 版本。** 数据库没有项目、表结构不同或损坏时会停止。

### 使用

需要 Windows、PowerShell 和 Python 3.10+，无需第三方 Python 包。

先预览（不写入配置，可在 Codex 打开时执行）：

```powershell
python .\repair.py
```

确认项目数量符合预期后，在**独立的 PowerShell 窗口**中操作：

1. 用 Codex 的“文件 → 退出”完全关闭应用。
2. 执行以下命令。
3. 命令成功后重新打开 Codex，检查实际项目显示。

```powershell
python .\repair.py --apply
```

自定义数据目录：

```powershell
python .\repair.py --codex-home 'D:\example\codex-data'
```

默认使用 `CODEX_HOME`，未设置则使用当前用户的 `~/.codex`。输出只包含数量、变更键和备份位置，不输出项目名称或聊天正文。`changed_keys: []` 表示无需更改。

### 备份与安全边界

写入前检查 Codex 是否仍在运行、数据库完整性及配置是否发生并发变化。先备份旧配置，再使用临时文件原子替换。
备份位于所选 Codex 数据目录的 `backups/project-rootpaths-时间戳/`。

要回退：完全关闭 Codex，先另存当前配置，再把备份中的 `.codex-global-state.json` 复制回数据目录。不需要恢复数据库，因为工具没有修改它。

- 应用未来可能改变格式；不要在不了解输出时反复执行。
- 缺失文件夹只会计数，不会自动创建或删除；项目仍会保留。
- 进程检查不能消除最后一次检查与写入之间的所有竞争窗口，修复期间请保持应用关闭。
- 配置及其备份可能含私人数据，不要上传到公开仓库。
- 本仓库不包含真实项目清单、聊天记录、截图、数据库或本机恢复快照。

### 测试

```powershell
python -m unittest discover -v
```

测试使用合成 SQLite 数据，验证预览不写入、修复包含 `rootPaths`、数据库与会话关联保留、备份、重复执行无额外变更，以及运行中的应用会阻止写入。

### 参考

排查时参考了 [Pankaj-1N/codex-desktop-windows-sidebar-recovery](https://github.com/Pankaj-1N/codex-desktop-windows-sidebar-recovery) 的修复思路。本工具针对另一处兼容性缺口，采用数据库项目记录和包含 `rootPaths` 的项目对象；没有打包该项目的代码或私人数据。

非 OpenAI 官方工具，与 OpenAI 无隶属关系。MIT License。

## English

A small, unofficial Windows recovery utility for Codex Desktop projects that still exist in the database but are absent from the sidebar.

It reads `projects` and `project_roots` from `state_5.sqlite` in read-only mode and restores `local-projects` records **including `rootPaths`**, plus `project-order`, in `.codex-global-state.json`. It preserves extra metadata and existing valid roots, does not infer projects from chat folders, and does not change chat assignments, pins, or the database.

The underlying approach restored 40 projects in a real Windows Codex Desktop 26.1106.6628.0 case. This published implementation removes the original machine-specific snapshot and has been validated with synthetic tests and a read-only preview; it is not a universal migration fix.

Requires Python 3.10+, Windows and PowerShell. No third-party Python dependencies.

```powershell
python .\repair.py           # preview only
# Fully exit Codex, then run in a separate PowerShell window:
python .\repair.py --apply   # back up and write
python -m unittest discover -v
```

Use `--codex-home PATH` for a custom data directory. The tool stops on missing tables or failed database integrity, refuses apply while Codex is running, backs up the state file and replaces it atomically. Keep Codex closed throughout apply. Other versions may use different schemas. To undo, close Codex and restore the backed-up JSON file; no database rollback is needed.

No project snapshots, database files, conversation content or local logs are included. MIT License. See the Chinese sections above for detailed usage and limitations.
