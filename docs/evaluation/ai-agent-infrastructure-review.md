# AI Agent 基礎架構評估 — 事實查核與風險補充報告

> 本報告針對 Alexander 撰寫的「AI Agent 基礎架構評估與導入計畫」進行獨立驗證
> 查核日期：2026-02-27
> 方法：對文件中所有可驗證的技術主張進行網路調研與 GitHub 原始碼交叉比對

---

## 一、方案比較表查核

### 1.1 Claude Agent SDK

| 文件主張 | 查核結果 | 判定 |
|---------|---------|------|
| 架構模式：CLI 引擎直接抽出 | 官方文件明確表示「Built on top of the agent harness that powers Claude Code」，SDK 套件自動打包 Claude Code CLI | **正確** |
| 語言支援：TypeScript Python | npm `@anthropic-ai/claude-agent-sdk`、PyPI `claude-agent-sdk` 均已發布 | **正確** |
| 模型綁定：Claude only（支援 Bedrock/Vertex） | 正確，另外也支援 Azure AI Foundry（`CLAUDE_CODE_USE_FOUNDRY=1`），文件未提及此項 | **正確，但不完整** |
| 無官方 Web UI | SDK 本身不含 Web UI，社群方案如 CUI、Claude Agent UI 等均為非官方 | **正確** |

**補充事實**：
- Claude Agent SDK 最初於 2025-05-22 以「Claude Code SDK」之名發布，2025-09-29 更名為「Claude Agent SDK」
- SDK 為 source-available，受 Anthropic 商業授權條款約束，非傳統開源

### 1.2 GitHub Copilot SDK

| 文件主張 | 查核結果 | 判定 |
|---------|---------|------|
| 架構模式：CLI 引擎直接抽出 | 所有 SDK 語言透過 JSON-RPC 與 Copilot CLI（server mode）通訊 | **正確** |
| 語言支援：TS Python Go .NET | Node.js、Python、Go、.NET 均有官方 SDK；另有社群 Java/Rust/C++ | **正確** |
| 模型綁定：多模型 | 支援 Claude Opus 4.6、Sonnet 4.6、GPT-5.3-Codex、Gemini 3 Pro 等 + BYOK | **正確** |
| 無 Web UI | 無官方 Web UI | **正確** |

**補充事實**：
- SDK 於 2026-01-14 進入 technical preview（文件撰寫時剛好一個多月前）
- Copilot CLI 於 2026-02-25 GA（昨天）
- SDK 本身為 proprietary，非開源

### 1.3 OpenAI Codex + Agents SDK

| 文件主張 | 查核結果 | 判定 |
|---------|---------|------|
| 架構模式：CLI 變 MCP Server 由獨立 SDK 編排 | Codex **可以**作為 MCP Server 被 Agents SDK 編排，但這只是其中一種整合模式，非其主要架構。主要路徑為 Codex App Server（JSON-RPC）和 Codex SDK（TypeScript） | **過度簡化** |
| 語言支援：Python（SDK）Rust（CLI） | Agents SDK 有 Python 和 TypeScript 版本；Codex CLI 確為 Rust；Codex SDK 為 TypeScript | **部分正確** |
| 模型綁定：OpenAI only | Agents SDK 可透過 LiteLLM 接非 OpenAI 模型 | **不完全正確** |
| 無 Web UI | Codex 有獨立的 Web 版（codex.openai.com），但 SDK 本身無內建 Web UI | **大致正確** |

**重要修正**：文件將 Codex 與 Agents SDK 混為一體，但它們是可獨立使用的不同產品。三者關係：
- **Codex CLI**：coding agent（如同 Claude Code）
- **Codex SDK**：程式化控制 Codex agent 的 TypeScript library
- **Agents SDK**：通用 agent 編排框架，可選擇性地透過 MCP 整合 Codex

### 1.4 OpenHands SDK

| 文件主張 | 查核結果 | 判定 |
|---------|---------|------|
| 架構模式：CLI/Cloud 引擎抽出 | 以 event-sourced 狀態模型和 typed tool system 為核心，同時驅動 CLI、Web UI、Cloud | **正確** |
| 語言支援：Python + REST | SDK 為 Python，其他語言可透過 REST API 存取 | **正確** |
| 模型綁定：多模型 | 模型無關，支援 Claude、GPT、Gemini 等 | **正確** |
| 內建完整 Web UI | 是，Web UI 為第一公民，包含 React SPA + REST API | **正確** |

**補充事實**：
- OpenHands V1.0.0 於 2025-12-16 發布
- 有學術論文支撐（arXiv:2511.03690）
- 提供 CLI / Web UI / Cloud（openhands.dev）三種介面

---

## 二、Claudex 推薦方案查核

### 2.1 專案基本資訊

| 項目 | 實際狀況 |
|-----|---------|
| 倉庫 | github.com/Mng-dev-ai/claudex（確認存在） |
| 作者 | Michael Gendy（Mng-dev-ai），位於埃及 |
| Stars | ~213 |
| Forks | ~42 |
| Commits | ~615 |
| Releases | 26 個（最新 v0.1.28，2026-02-26 發布） |
| Contributors | 3 人 |
| 授權 | Apache-2.0 |
| 技術棧 | TypeScript 55.2%, Python 42.7% |

### 2.2 功能主張查核

| 文件主張 | 查核結果 | 判定 |
|---------|---------|------|
| 保留 Claude Agent SDK 的完整 agent loop | 後端透過 `claude-agent-sdk` 驅動 Claude Code CLI，在沙箱環境中執行 | **正確** |
| 提供完整 Web UI | React 19 + FastAPI + PostgreSQL/Redis（Web 模式）；Tauri 桌面版也可用 | **正確** |
| 含 in-browser VS Code terminal sandbox | Docker Compose 中有 OpenVSCode Server（port 8765）+ VNC（port 5900/6080） | **正確** |
| 支援模型熱切換（透過 anthropic-bridge） | Claudex 在沙箱內啟動 anthropic-bridge，支援 provider-scoped model ID 切換 | **正確** |

### 2.3 anthropic-bridge 查核

Claudex 使用的 anthropic-bridge 為 **Mng-dev-ai/anthropic-bridge**（同一作者）：

| 項目 | 狀況 |
|-----|------|
| Stars | 8 |
| Releases | 39 |
| 最後更新 | 2026-02-17 |
| 支援 provider | OpenRouter、OpenAI（Codex CLI auth）、GitHub Copilot |
| 功能 | Streaming SSE、tool/function calling、extended thinking、reasoning cache |

---

## 三、文件未提及的重大風險

### 風險 A：模型切換的「靜默降級」問題（嚴重）

文件低估了模型切換的複雜度。根據調研，Claude Code 使用 model ID 字串進行內部功能檢測（最大輸出 token 數、訓練日期、可用功能）。當 anthropic-bridge 返回的 model name 與 Claude Code 預期的子字串不匹配時：

- 輸出會被截斷
- 功能靜默消失
- **沒有任何錯誤訊息**

這意味著「切換模型時 agent loop 工具系統 Web UI 完全不變」的主張在功能層面正確，但在**行為品質層面過於樂觀**。實際上只有基本對話和簡單編輯能可靠運作；複雜的多步驟工具串接高度依賴上游模型的原生能力。

### 風險 B：Claudex 與 anthropic-bridge 為同一作者（集中風險）

Claudex 和 anthropic-bridge 均由 Michael Gendy 開發。這帶來：
- **單人巴士因子**：核心元件依賴同一個人維護
- 兩個專案的 star 數（213 + 8）和 contributor 數（3 + 1）均極低
- v0.1.x 版號表明作者自認為 pre-1.0 品質

### 風險 C：更成熟的替代方案未被評估

anthropic-bridge 生態中最成熟的專案是 **1rgs/claude-code-proxy**（3,100 stars、413 forks、11 contributors），使用 LiteLLM 作為轉譯層。文件完全未提及此方案，也未解釋為何選擇 star 數低兩個量級的 anthropic-bridge。

### 風險 D：Anthropic 授權政策風險

Anthropic 已明確禁止在 Claude Code 和 Claude.ai 以外的工具中使用 Claude Free/Pro/Max 訂閱的 OAuth token。Claudex 的使用場景（透過第三方 Web UI 呼叫 Claude Agent SDK）可能落入灰色地帶。建議：
- 確認使用 pay-as-you-go API key（非訂閱 token）
- 追蹤 Anthropic ToS 變更

### 風險 E：OpenAI Codex/Agents SDK 架構描述過度簡化

文件將三個獨立產品（Codex CLI、Codex SDK、Agents SDK）混為「CLI 變 MCP Server 由獨立 SDK 編排」。實際上 MCP 只是可選的整合模式之一，主要整合路徑為 Codex App Server（JSON-RPC）。這影響方案比較的公正性。

---

## 四、正面評價

文件中以下核心判斷經查核為正確且有洞見：

1. **「Claude Agent SDK 的護城河在 agent loop 工程品質」** — 正確。SDK 確實是從 Claude Code CLI 的完整 agent harness 抽取而來，包含 context window 管理、retry/replan、prompt caching 等工程優化，非純 API 呼叫可複製。

2. **「MCP 解決介面標準化但不保證行為可移植」** — 精確。MCP 確保工具定義格式一致，但模型能否正確編排多步驟工具呼叫，取決於模型能力。

3. **「CLI 衍生 SDK 已成主流趨勢」** — 完全正確。Claude Agent SDK（2025-05/09）、OpenAI Codex SDK（2025-10）、OpenHands SDK（2025-12）、GitHub Copilot SDK（2026-01）均依此模式發展。

4. **分級 failover 策略** — 同模型異基礎設施 → 異模型同架構 → 確定性 pipeline 的降級邏輯合理。

5. **業務工具封裝為 MCP Server** — 正確的長期投資方向，即使更換 SDK 框架也能保留工具層。

---

## 五、修正建議摘要

| 項目 | 問題 | 建議修正 |
|-----|------|---------|
| 方案比較表 — Codex | 過度簡化為「CLI 變 MCP Server」 | 區分 Codex CLI/SDK/App Server 與 Agents SDK 的關係 |
| 方案比較表 — Codex | 「OpenAI only」不完全正確 | 註明 Agents SDK 支援 LiteLLM 多模型 |
| 方案比較表 — Claude SDK | 缺少 Azure Foundry | 補充 Azure AI Foundry 支援 |
| 方案比較表 — Copilot SDK | 未標註為 proprietary | 補充授權資訊 |
| Claudex 評估 | 未提及 claude-code-proxy（3100 stars）| 至少應比較兩者 |
| 模型切換風險 | 低估靜默降級問題 | 補充 model ID 字串匹配機制說明 |
| 單人風險 | 未評估 Claudex/bridge 同一作者風險 | 補充 bus factor 分析 |
| 授權風險 | 未提及 Anthropic ToS 限制 | 補充使用合規建議 |
| Copilot SDK 時間線 | 未提及剛 GA 的 CLI 和 technical preview 的 SDK | 補充現狀供決策參考 |

---

## 六、結論

### 文件整體評價

這是一份**品質不錯的技術評估文件**，核心洞見（agent loop 價值、MCP 局限、CLI→SDK 趨勢、分級降級策略）均經得起查核。主要弱點在於：

1. **方案比較不夠完整公正**（特別是 OpenAI 生態的描述過度簡化）
2. **對 Claudex 的風險評估不足**（單人維護、同作者依賴、更成熟替代方案未列入比較）
3. **模型切換的實際挑戰被低估**（靜默降級是已知且嚴重的問題）

### Claudex 選型的判定

Claudex 確實是一個**真實存在且功能如文件所述的方案**，但其成熟度（213 stars、3 contributors、v0.1.x）和集中風險（核心元件同一作者）需要團隊充分理解。建議：

1. **Phase 1 的 PoC 值得進行** — 投入有限，可快速驗證
2. **同時評估 claude-code-proxy + 自建前端**作為 Plan B — 底層轉譯層更成熟
3. **認真評估 GitHub Copilot SDK** — 剛 GA，原生多模型，可能是中長期更穩定的選項
4. **建立 fork 準備** — 若 Claudex PoC 通過，應立即 fork 以降低單人維護風險
