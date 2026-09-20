# Claude Desktop 汉化 (zh-CN UI localization)

## 选型（重要：javaht 在本机已被证伪）

- **首选** `LifeActor/Claude_zh-CN_LanguagePack`（2026-09 本机实测路径：`C:/Users/mnb77/Downloads/Claude_zh-CN_LanguagePack`）：轻量、不碰 exe 签名、不破坏官方自动更新。
- **不要再用** `javaht/claude-desktop-zh-cn`：它给 `Claude.exe` 打二进制补丁并走 Frida 注入，签名哈希校验被破坏后应用容易被杀/闪退（用户实测"不完全兼容且容易退出"），已弃用并记入 MEMORY。两者机制对比见下。

## 机制（决定稳定性）

| 方案 | 手段 | 签名/更新后果 |
|---|---|---|
| javaht | 二进制补丁 Claude.exe + Frida 钩子 + 在线 DOM 注入 | HashMismatch、Defender/杀软可杀进程、Squirrel 自升后旧补丁失效 → 闪退 |
| LifeActor | ① 正则把 `zh-CN` 注册进 `ion-dist/assets/v1/*.js` 的语言数组；② 复制 `zh-CN.json` 到官方 i18n 目录；③ 正则改 `LocalCache\Roaming\Claude\config.json` 的 `locale` 字段 | 不碰 exe、不用 Frida、兼容官方自动更新 |

## 本机操作（Windows MSIX 安装）

- 安装包路径：`C:\Program Files\WindowsApps\Claude_<ver>_x64__pzs8sxrjxfjjc\app\resources`（用 `Get-AppxPackage -Name Claude` 定位，版本号会变）。
- 安装脚本：`LanguagePack.ps1`，入口 `安装中文语言包.bat`（带 `-PauseAtEnd`）。**写 `C:\Program Files\WindowsApps` 需要管理员（UAC）**。
- 卸载：`卸载中文语言包.bat`（`-Uninstall`），会从 `%TEMP%\claude-zh-cn-backup` 恢复原 JS 并把 locale 改回 `en-US`。

## 运行 PowerShell 安装脚本的坑（本机 terminal 环境）

- terminal 的 bash 会话**无法**让 UAC 弹窗可达：`powershell -File ...` 与 `cmd //c 安装.bat` 都会挂起超时（前台 300s 超时）；`Start-Process -Verb RunAs` 同理——弹窗落在用户桌面会话，terminal 拿不到交互。
- 可行做法：请用户在桌面点一下 UAC"是"（脚本弹在他会话里），或让他双击 `安装中文语言包.bat`；随后由 agent 在后台验证落地。
- 验证命令（无需管理员，纯读）：
  ```bash
  ls "/c/Program Files/WindowsApps/Claude_*/app/resources/ion-dist/i18n/" | grep zh-CN
  ```
  再看配置 locale：`grep '"locale"' "C:/Users/mnb77/AppData/Local/Packages/Claude_*/_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/config.json"` 应为 `"zh-CN"`。
- 安装完成后若 Claude 弹自动更新重启，重跑一次安装脚本即可（LifeActor 方案对新版目录是幂等的，备份目录在 `%TEMP%\claude-zh-cn-backup`）。

## 关键前置诊断（做注入前先跑，别盲改）

**Windows 包类型决定成败**：先 `Get-AppxPackage -Name Claude` 确认安装形态。
- **MSIX/MSIX 包**（安装位置在 `C:\Program Files\WindowsApps\Claude_<ver>..._pzs8sxrjxfjjc`）：整个包目录被 **AppContainer 沙箱锁死**——ACL 只授 `BUILTIN\Users:(R)`、写权限仅 `NT AUTHORITY\SYSTEM` + `TrustedInstaller`。后果：① 非提权进程写入直接 `Permission denied`；② `icacls /grant`（即使 UAC 提权）返回「成功 0 个文件 / 失败 N 个文件」，全部 access denied；③ 提权 PowerShell 脚本在此类目录同样写不进。javaht 在 MSIX 实例上"容易退出"很大程度源于此。
- **MSI 包**（安装位置在 `C:\Program Files\Claude`）：无 AppContainer 沙箱，管理员可直接写文件。LifeActor 语言包在此形态下才可靠生效。
- 诊断一行流：`icacls "<i18n 目录>"` 看 ACL 是否只有 SYSTEM/TrustedInstaller 持有 F；或 `Get-AppxPackage -Name Claude` 是否命中。

**决定树**：
- MSIX 且无法转 EXE/MSI → 不要浪费时间跑 LifeActor 或 icacls 破权，直接告知用户两条稳路：① 重装为官方 EXE（Squirrel 用户级）或 MSI 包再跑语言包；② 放弃本地汉化，走 CC Switch 第三方路由（UI 保持英文）。
- 可转 EXE/MSI → 先彻底卸载 MSIX（杀光 `claude.exe` 残留后 `Get-AppxPackage -Name Claude | Remove-AppxPackage`），再走下方 EXE 或 MSI 流程。

## Squirrel 用户级 EXE 安装（2026-09 本机验证成功的形态）

官网 `Claude-Setup-x64.exe` 走 Squirrel，装到 **`%LOCALAPPDATA%\AnthropicClaude\app-<ver>\`**（如 `app-2.2553.1`），用户级目录完全可写、**无需 UAC**。注意：`app-<ver>` 目录版本号与 winget 显示的应用版本不一致，操作前用 `tasklist`/`Get-Process` 看 `claude.exe` 的实际 Path 或列目录取最新 `app-*`，**不要写死版本号**。安装包用 winget 直链（`winget show Anthropic.Claude` 取安装程序 URL，`downloads.claude.ai` 可匿名下载）；`claude.ai/api/.../redirect` 会 403，别用它。

3 处纯文件注入（参考脚本 `%LOCALAPPDATA%\Temp\apply_zh.py` 可复用；官方升级后对新版目录重跑）：
1. **语言 JSON**：`translated-zh-CN` 下 4 个文件拷入 `resources/ion-dist/i18n/`（zh-CN.json + overrides）、`resources/zh-CN.json`（外壳）、`resources/ion-dist/i18n/statsig/`（新版无此目录则跳过）。
2. **JS 语言注册**：`resources/ion-dist/assets/v1/*.js` 中把 `=["en-US",...]` 硬编码数组插入 `"zh-CN"`。⚠️ **必须同时覆盖单元素 `["en-US"]` 与多元素 `["en-US","fr-FR",...]` 两种形态**——LifeActor 自带脚本的正则只匹配含其他语言的多元素数组，会漏掉只声明 `["en-US"]` 的文件（本机实测漏 4 个 JS，界面残留英文；补 `re.subn(r'\["en-US"\]', '["en-US","zh-CN"]')` 后清零）。注入后用扫描脚本复核「还有没有不含 zh-CN 的 en-US 数组」，别只信注入脚本自报的计数。
3. **locale**：`%LOCALAPPDATA%\Claude\config.json`（官方账号）或 `%LOCALAPPDATA%\Claude-3p\config.json`（3P 模式）写 `"locale": "zh-CN"`（字段不存在则插进最后一个 `}` 前）。

完成后 `taskkill /F /IM claude.exe` 再 `Start-Process claude.exe`。不碰 exe 签名，官方 Squirrel 升级不冲突。

## 本机 terminal 环境跑安装/注入的坑

- **静默安装经 `powershell Start-Process <exe> -ArgumentList '/S' -Wait`**：`cmd //c <exe>` 会被 terminal 会话吞掉（瞬间返回提示符，安装实际未执行）。`-Wait` 会挂到 300s 超时但安装已完成——超时后 `tasklist | grep -i claude` 查落地，不要重跑安装。
- **`powershell -Command` 里含 `$_` 的管道会被 MSYS 转义成 `/c/Users/<user>.Name` 乱码、整条命令崩溃**：查进程一律改 `tasklist | grep -i <name>`；多行/批量逻辑 write_file 成 .py 再 `python xxx.py`。
- **`python -c` 多层引号嵌套会被 shell 截断报 SyntaxError**：超一行的逻辑一律落盘成 .py 再执行。
- **`find` 全量搜 `AppData` 会超时**：用精确路径 ls/cat 或限定深度。

## 与 CC Switch / 第三方路由的共存

- 汉化只动 UI 文本与 locale，不影响 CC Switch 的本地路由（`ANTHROPIC_BASE_URL` 走的是 CC Switch 的 env/proxy 配置，与 UI 语言正交）。用户已用 AgnesAI 走 CC Switch 第三方入口，汉化后两者不冲突。
- 若汉化后 UI 变中文但 "Developer → Configure Third-Party Inference" 菜单文字变化，不影响操作——菜单结构不变，只是标签换语言。
