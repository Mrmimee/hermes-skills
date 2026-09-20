# ☤ Hermes Skills Vault (实战精选技能库)

> 个人定制与实战沉淀的 Hermes Agent 高价值技能库。模块化分类管理，换机一键同步复用。

---

## 🚀 换机一键复用 (One-Line Setup)

在任何新电脑（Windows / macOS / Linux）上，只需克隆本仓库并运行安装脚本：

```bash
git clone https://github.com/Mrmimee/hermes-skills.git
cd hermes-skills
python install.py
```

安装脚本会自动识别系统的 Hermes 路径（Windows `%LOCALAPPDATA%\hermes\skills` 或 Linux/macOS `~/.hermes/skills`），完成分类目录与运维脚本的自动化挂载。

---

## 📂 技能分类清单 (30 个实战沉淀 Skills)

### 1. Autonomous AI Agents (智能体架构与路由调度)
* **`agent-decision-routing`**: 智能体动态任务路由与工作流分流仲裁
* **`ccswitch-provider-db`**: CC Switch 多供应商 SQLite 规则配置
* **`claude-desktop-llm-gateway`**: Claude Desktop 第三方 LLM 开发者网关通道配置
* **`hermes-model-chain-wiring`**: Hermes 多供应商主模型与 Fallback 链配置与校验
* **`hermes-gateway-triage`**: Hermes 网关延迟排障与技能膨胀精简
* **`hermes-config-audit`**: 插件与 MCP 服务器配置审计
* **`hermes-credentials-setup`**: 敏感 API 密钥与凭据生命周期管理
* **`hermes-desktop-theme-sync`**: 桌面端主题热重载与文件级同步
* **`hermes-command-tts-provider`**: 命令行与本地自定义 TTS/STT 供应商挂载
* **`jev-decision-engine`**: Jev 极速结构化裁决小脑 (Choice / Score / Noul)
* **`vertex-provider-setup`**: Google Cloud Vertex AI 服务账号与 OpenAI 兼容端点接入

### 2. Study & Engineering (架构研读与工程排障)
* **`claude-code-source-study`**: Claude Code 源码架构深度研读 (34章实战知识库)
* **`local-llm-deployment`**: 本地轻量 LLM 部署 (RTX 3050 4GB 优化路线)
* **`inspecting-hermes-desktop-dom`**: 基于 CDP 协议对 Hermes 桌面应用 DOM/CSS 进行热调试
* **`node-inspect-debugger`**: Node.js --inspect + CDP 调试器
* **`requesting-code-review`**: 自动化代码审查、安全扫描与质量门禁
* **`systematic-debugging`**: 四阶段根因排查法
* **`simplify-code`**: 代码重构与复杂度清理
* **`spike`**: 探索性快速验证实验
* **`test-driven-development`**: TDD 红绿重构测试驱动开发

### 3. Creative & Design (视觉设计与前端)
* **`frontend-design`**: 现代化高质量视觉设计与组件规范
* **`claude-design`**: 一次性 HTML 原型与独立交互页面设计
* **`design-md`**: Google DESIGN.md 规范校验与导出
* **`hermes-styling-and-theming`**: Hermes CLI / TUI / 桌面端主题定制
* **`humanizer`**: 文本去 AI 化与自然语气润色
* **`impeccable`**: 界面设计审美评估与批判

### 4. Workflow & Tools (实战工作流与轻量工具)
* **`ponytail`**: 极简极懒主义实战解决方案 (Lazy Path)
* **`grill-me`**: 针对方案进行深度穷追猛打与漏洞审计
* **`find-skills`**: 智能体技能自动检索与安装引导
* **`bazi-mingli`**: 四柱八字排盘与紫微斗数推演

---

## 🛠️ 随附运维脚本 (`scripts/`)

* **`model_chain_probe.py`**: Hermes 主模型与 Fallback 链 8 小时无头健康巡检探针（Watchdog 模式，健康零骚扰，故障即时告警）。
* **`free_pool_monitor.py`**: 全球备用免费池（OpenRouter / NaraRouter / Nous）可用性与 429 限流盯梢器。
