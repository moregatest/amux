# claude-code-proxy 深度評估報告

> 針對 1rgs/claude-code-proxy 及整個 Claude Code 模型路由生態系的獨立技術評估
> 查核日期：2026-02-27

---

## 一、1rgs/claude-code-proxy 專案概覽

| 項目 | 數據 |
|------|------|
| 倉庫 | github.com/1rgs/claude-code-proxy |
| 作者 | Rahul (1rgs)，Ramp.com AI 負責人，前 cohere.io 共同創辦人 |
| Stars | ~3,100 |
| Forks | ~413 |
| Contributors | 11（15+ PR 作者） |
| Commits | 42 |
| 建立日期 | 2025-03-19 |
| **最後 commit** | **2025-11-19（距今 3+ 個月無更新）** |
| Releases | **無**（無正式版本號、無 changelog） |
| License | **未指定**（企業使用有法律風險） |
| 技術棧 | Python 99.7%, FastAPI + LiteLLM + Pydantic |
| 測試 | **無**（倉庫中無測試檔案） |

### 核心定位

「Run Claude Code on OpenAI models」— 一個單檔 proxy server（`server.py`），接收 Anthropic Messages API 格式請求，透過 LiteLLM 翻譯後轉發至 OpenAI/Gemini/其他後端。

---

## 二、技術架構分析

### 請求流程（5 階段 pipeline）

```
Claude Code CLI
  → POST /v1/messages（Anthropic 格式）
    → Model Mapping（haiku→SMALL_MODEL, sonnet→BIG_MODEL）
      → convert_anthropic_to_litellm()（格式轉換）
        → LiteLLM API（轉發至後端 provider）
          → convert_litellm_to_anthropic()（回譯為 Anthropic 格式）
            → SSE Streaming 回應給 Claude Code
```

### 支援的 Provider

| Provider | 設定方式 | 預設模型 |
|----------|---------|---------|
| OpenAI（預設） | `PREFERRED_PROVIDER=openai` | gpt-4.1 / gpt-4.1-mini |
| Google Gemini | `PREFERRED_PROVIDER=google` | gemini-2.5-pro / gemini-2.5-flash |
| Vertex AI | `USE_VERTEX_AUTH=true` | 同 Gemini |
| Anthropic（透傳） | `PREFERRED_PROVIDER=anthropic` | 原模型直通 |
| 自訂 OpenAI 相容端點 | 設定 `OPENAI_BASE_URL` | 任意 |

### 模型映射邏輯

- 請求中包含 "haiku" → 映射到 `SMALL_MODEL` 環境變數
- 請求中包含 "sonnet" → 映射到 `BIG_MODEL` 環境變數
- Anthropic 模式 → 不做映射，直接透傳

---

## 三、已知的關鍵技術問題

### 問題 1：靜默能力降級（Critical）

Claude Code CLI 使用 model ID 子字串檢測功能：

| 子字串 | 觸發的能力 |
|--------|-----------|
| `opus-4-5` / `opus-4-6` | 64K token 輸出上限 |
| `sonnet` | 計畫模式自動升級 |
| `haiku` | 輕量任務路由 |

當 proxy 將 model ID 改寫為 `gpt-4.1` 後，這些子字串消失：
- 功能**靜默降級**，無任何錯誤訊息
- 輸出被截斷
- 狀態列顯示錯誤的模型名稱

**緩解方式**：設定 `ANTHROPIC_DEFAULT_OPUS_MODEL`、`ANTHROPIC_DEFAULT_SONNET_MODEL`、`ANTHROPIC_DEFAULT_HAIKU_MODEL` 環境變數，但 proxy 本身未記錄此方法。

### 問題 2：max_tokens 硬編碼為 16,384（Critical）

程式碼中將 OpenAI/Gemini 的 max_tokens 硬上限設為 16,384，而 Claude 的 context window 為 200K。這導致：
- 長輸出被靜默截斷
- 複雜的多步驟任務提前中止

### 問題 3：Tool Calling 邊緣案例

| 問題 | 影響 |
|------|------|
| content blocks 被攤平為純字串（OpenAI 不支援結構化 content blocks） | 資訊遺失 |
| Gemini 不接受某些 JSON Schema 欄位（`additionalProperties`） | 需額外清理 |
| 串流模式下 tool call 可能回退至非串流 | 使用者體驗降級 |
| WebFetch 工具在 Gemini 後端完全失效（Issue #57） | HTTP 成功但模型聲稱無法存取 |

### 問題 4：Extended Thinking 支援薄弱

Extended thinking 是 Anthropic 專有功能。proxy 僅有最低限度的處理（PR #18），非 Anthropic 後端不支援合成 thinking blocks。

### 問題 5：count_tokens 端點

Claude Code 呼叫 `/v1/messages/count_tokens` 做上下文管理。proxy 僅有 stub，替代後端通常未實作此端點。

---

## 四、社群健康度評估

| 指標 | 狀態 | 評價 |
|------|------|------|
| 最後 commit | 2025-11-19 | **3 個月無活動** |
| Open Issues | 37 個 | 多數**零回覆** |
| Closed Issues | 3 個 | 問題關閉率 <8% |
| Open PRs | 16 個 | 多個月未合併（含 GPT-5 支援、Web search 支援） |
| 正式 Release | 0 個 | **無版本管理** |
| License | 未指定 | **企業使用有法律疑慮** |
| 測試套件 | 無 | **零測試覆蓋** |

**判定：專案已進入維護停滯狀態。** 高 star 數反映的是 2025 年中期的社群興趣，而非當前的維護品質。

---

## 五、生態系全景 — 更值得關注的替代方案

調研發現整個 Claude Code 模型路由生態系遠比原始文件認知的更為龐大：

### Tier 1：主要方案（1,000+ stars）

| 專案 | Stars | 語言 | 架構特點 | 最後更新 |
|------|-------|------|---------|---------|
| **musistudio/claude-code-router** | ~28,500 | JS/TS | 本地 proxy + Web UI，按任務類型動態路由，支援 8+ provider | 2026-01 |
| **router-for-me/CLIProxyAPI** | ~11,900 | Go | 反向 proxy — 將多個 CLI 工具包裝為統一 API | 2026-02 |
| **1rgs/claude-code-proxy** | ~3,100 | Python | LiteLLM 轉譯層，單檔設計 | 2025-11 |
| **fuergaosi233/claude-code-proxy** | ~2,100 | Python | 直接 Anthropic→OpenAI 轉換，`BIG_MODEL`/`SMALL_MODEL` 映射 | — |
| **copilot-api** | ~2,000 | — | GitHub Copilot 轉為 OpenAI/Anthropic 相容 API | — |

### Tier 2：值得評估的方案（100-1,000 stars）

| 專案 | Stars | 特色 |
|------|-------|------|
| **claude-balancer** | ~820 | 多帳號負載均衡 + 自動 failover |
| **ccflare** | ~820 | 多帳號智慧負載均衡 |
| **Intelligent API Gateway** | ~697 | Go 實作，端點輪替 + 用量監控 |
| **ccNexus** | ~622 | 智慧 API 端點輪替 |
| **decolua/9router** | ~556 | 三級 fallback（訂閱→預算→免費），含免費無限 provider |
| **maxnowack/anthropic-proxy** | ~399 | JS，廣泛引用 |
| **seifghazi/claude-code-proxy** | ~382 | TS+Go，請求可視化 dashboard + agent 路由 |
| **Fast-Editor/Lynkr** | ~359 | Node.js，Databricks 整合，語意快取，60-80% 成本降低 |
| **starbaser/ccproxy** | ~173 | LiteLLM 上的規則路由引擎，支援 100+ provider |

### 重量級玩家：不是 Proxy 但消除了 Proxy 需求

| 方案 | 說明 |
|------|------|
| **Ollama v0.14.0+** | 原生支援 Anthropic Messages API！設 `ANTHROPIC_BASE_URL=http://localhost:11434` 即可直接用本地模型驅動 Claude Code，無需任何 proxy |
| **OpenRouter 原生整合** | 提供 "Anthropic Skin" 端點，直接設 `ANTHROPIC_BASE_URL=https://openrouter.ai/api` 即可使用 400+ 模型，處理 thinking blocks 和工具呼叫 |
| **LiteLLM 直接使用** | 官方文件有 Claude Code 整合教學，可作為完整 AI Gateway（但 Anthropic 明確聲明不背書其安全性） |

### 商業方案

| 方案 | 定價 | 特色 |
|------|------|------|
| **Portkey** | 企業報價（已融 $15M Series A） | 第一級 Claude Code 整合，多 provider 路由，成本追蹤，治理審計 |
| **Kong AI Gateway** | 企業授權（通常 $50K+/年） | 通用 API 管理平台，支援 Claude Code 流量路由 |
| **OpenRouter** | 按 token 計費 | API 聚合器，400+ 模型，自動 failover，團隊預算管理 |

---

## 六、LiteLLM 作為轉譯層的深度評估

LiteLLM 是 claude-code-proxy 的核心依賴，也是多個 proxy 方案的底層引擎。

### 基本資料

| 項目 | 數據 |
|------|------|
| Stars | ~37,000 |
| Contributors | 1,296+ |
| 維護者 | BerriAI（YC 孵化，$2.1M 融資） |
| 支援 Provider | 100+ |
| 企業客戶 | Netflix, Adobe, Samsara, Lemonade 等 |

### Claude Code + LiteLLM 的已知問題清單

| Issue | 描述 | 狀態 |
|-------|------|------|
| litellm#11358 | Claude Code v1.0.8+ 破壞了 LiteLLM 相容性（「request ended without sending any chunks」） | 2025-06 |
| litellm#13252 | `count_tokens` API 未實作（404） | 已修復但有後續 bug |
| litellm#14236 | 含 tool use 的對話 token counting 失敗 | Open |
| litellm#16711 | Claude Code tool result 格式與 LiteLLM 非 Anthropic 模型不相容 | Open |
| litellm#16962 | Claude Code + Gemini 多重 bug：cache 失敗、token counting 失敗、web search 工具未翻譯 | Open |
| litellm#17904 | Claude Code 工具名稱超過 64 字元導致 OpenAI 拒絕 | Open |
| litellm#17737 | `server_tool_use` 被錯誤轉為 `tool_use`，`web_search_tool_result` 被丟棄 | Open |

### 串流 + Tool Calling 的特殊問題

| 問題 | 影響 |
|------|------|
| 串流 chunk 的 index=-1，缺少 id/name | 客戶端解析崩潰 |
| 事件順序違反 Anthropic 的 `tool_use`/`tool_result` 配對規則 | 多輪對話中斷 |
| 串流 tool call 無參數時返回 `""` 而非 `"{}"` | JSON 解析錯誤 |
| 每個串流 chunk 有不同的 `chatcmpl-` ID | 打破 OpenAI 相容性 |

### 核心風險

**每次 Claude Code 版本更新都可能破壞 LiteLLM 相容性**（如 v1.0.8 事件）。這意味著使用 LiteLLM 作為轉譯層的所有方案（包括 claude-code-proxy）都面臨持續的維護追趕壓力。

---

## 七、與 Claudex + anthropic-bridge 的正面比較

### 定位差異

| 維度 | claude-code-proxy 生態系 | Claudex + anthropic-bridge |
|------|------------------------|---------------------------|
| **解決的問題** | 模型路由（用便宜/不同的模型跑 Claude Code） | 完整工作空間（Web UI + 沙箱 + 模型路由 + session 管理） |
| **架構** | 輕量 proxy（通常單檔） | 全端應用（React + FastAPI + PostgreSQL + Docker 沙箱） |
| **Agent Loop** | 不涉及（僅做 API 轉發） | 保留 Claude Agent SDK 完整 agent loop |
| **Web UI** | 無（仍用 CLI 或自建前端） | 內建完整 Web UI + in-browser VS Code |
| **MCP 支援** | 不涉及 | 內建 MCP Server 管理 |
| **適合誰** | 個人開發者降低 Claude Code 成本 | 團隊需要完整 AI 工作空間 |

### 技術品質比較

| 維度 | 1rgs/claude-code-proxy | Mng-dev-ai/anthropic-bridge | Claudex |
|------|----------------------|---------------------------|---------|
| Stars | 3,100 | 8 | 213 |
| Commits | 42 | 101 | 615 |
| Releases | 0 | 39 | 26 |
| License | **未指定** | MIT | Apache-2.0 |
| 測試 | 無 | 未知 | 有 |
| 最後更新 | 2025-11 | 2026-02 | 2026-02 |
| 維護活躍度 | **停滯** | 活躍 | 活躍 |
| 轉譯層 | LiteLLM（繼承其 bug） | 自建（per-provider 優化） | 透過 anthropic-bridge |

**關鍵洞見**：star 數與維護品質不成正比。claude-code-proxy 的 3,100 stars 反映歷史熱度，但 0 releases、無 license、3 個月停滯、37 個未回覆 issue 使其**不適合作為生產依賴**。

---

## 八、成本節省的實際數據

根據多篇使用者報告的交叉比對：

| 場景 | Claude API 直接成本 | 透過 Router 成本 | 節省 |
|------|-------------------|-----------------|------|
| 典型開發者月用量 | $100-200 | $15-40 | 3-5x |
| 簡單重構/格式化 | $X | ~$0.1X | 90%+ |
| 複雜多檔架構設計 | $X | **品質顯著下降** | 不建議替換 |
| Kimi K2 跑同等任務 | $X | ~$0.2X | 5x |
| DeepSeek 跑同等任務 | $0.05（Claude） | <$0.003 | 17x |

**但注意**：
- 10x 成本節省的宣傳普遍誇大，3-5x 是現實可期的
- 複雜架構任務使用便宜模型品質**顯著下降**
- **Tool calling 是關鍵分水嶺** — 不支援 tool calling 的模型（如 DeepSeek）會破壞 Claude Code 的檔案編輯、git、終端機等核心功能

---

## 九、Anthropic 政策風險更新

### 2026 年 1-2 月事件

- **2026-01-09**：Anthropic 封鎖第三方工具使用 Claude Pro/Max 訂閱 OAuth token
- **2026-02**：更新消費者服務條款，明確禁止在 Claude Code/Claude.ai 以外使用 OAuth token
- HN 大量討論（DHH 稱其「非常不友善客戶」，George Hotz 警告將推動用戶轉向其他 provider）

### 影響範圍

| 使用方式 | 影響 |
|---------|------|
| API key（按 token 計費）→ 任何 proxy | **不受影響** |
| 訂閱 OAuth token → 第三方工具 | **已被封鎖** |
| proxy 路由至非 Anthropic 模型 | **不受影響**（不涉及 Anthropic 服務） |
| Claudex + API key | **不受影響**，但灰色地帶需追蹤 |

---

## 十、對 Ready Market 的具體建議

### claude-code-proxy（1rgs）不建議作為生產依賴

原因：
1. **無 license** — 企業使用有法律風險
2. **專案停滯** — 3 個月無 commit，37 個 issue 無人回應
3. **零測試** — 無法保證行為正確性
4. **無版本管理** — 無法鎖定穩定版本
5. **靜默降級** — model ID 問題未被處理

### 如果目標是「模型路由」，更好的選擇

| 需求 | 推薦方案 | 理由 |
|------|---------|------|
| 最簡單的多模型接入 | **OpenRouter 原生整合** | 零部署，設一個環境變數即可，400+ 模型，按 token 計費 |
| 智慧任務路由（省錢） | **musistudio/claude-code-router**（28.5K stars） | 按任務類型動態切換模型，Web UI 配置，社群最大 |
| 本地模型 | **Ollama v0.14.0+** | 原生 Anthropic API 相容，無需 proxy |
| 企業級 gateway | **LiteLLM** 或 **Portkey** | 成本追蹤、RBAC、審計日誌 |

### 如果目標是「完整 AI 工作空間」

Claudex 仍是目前唯一同時提供 Web UI + Claude Agent SDK agent loop + 模型路由的整合方案。但建議：

1. **分離模型路由層** — 不要依賴 anthropic-bridge（8 stars），改用 OpenRouter 或 claude-code-router 作為路由層
2. **Claudex 負責 Web UI + 沙箱 + session 管理** — 這才是它的不可替代價值
3. **即刻 fork** — 以降低單人維護風險

### 修正後的建議架構

```
Claudex Web UI（React 前端）
  → Claude Agent SDK + Claude Code CLI（agent loop 引擎）
    → 正常營運：直連 Anthropic API / Bedrock / Vertex
    → 成本優化：OpenRouter（原生 Anthropic Skin 端點）
    → 本地推理：Ollama v0.14.0+（原生 Anthropic API 相容）
    → 企業 gateway：LiteLLM Proxy（成本追蹤 + RBAC）
```

關鍵改動：
- 移除 anthropic-bridge 作為單點依賴
- 直接使用 OpenRouter/Ollama 的原生 Anthropic API 相容性
- 省去一層翻譯 = 減少一層故障點

---

## 十一、結論

### 核心發現

1. **claude-code-proxy（1rgs）的 3,100 stars 是虛假信號** — 專案已停滯，無 license、無測試、無版本管理，不適合生產使用

2. **生態系比預期大得多** — claude-code-router（28.5K stars）才是社群主流，且有多個活躍的替代方案

3. **原生整合正在消除 proxy 需求** — Ollama v0.14.0 和 OpenRouter 的 Anthropic Skin 端點讓「翻譯層」變得不再必要

4. **LiteLLM 作為轉譯層是雙刃劍** — 廣度驚人（100+ provider）但 Claude Code 專用場景的 bug 密度很高，且每次 Claude Code 更新都可能破壞相容性

5. **模型路由的真正瓶頸是 tool calling** — 這比 API 格式轉換困難得多，是決定「換模型後 agent 是否還能正常工作」的核心因素

6. **原始文件的 Claudex 推薦方向基本正確** — 但應將模型路由層從 anthropic-bridge 替換為更成熟的方案（OpenRouter 或 claude-code-router）
