# LiteLLM 深度研究報告 — 作為 Claude Code 轉譯層的適用性評估

> 查核日期：2026-02-27
> 方法：Web 搜尋、GitHub Issue/PR 分析、原始碼審閱、社群報告交叉比對

---

## 一、LiteLLM 基本資料

### 1.1 專案概覽

| 項目 | 數據 |
|------|------|
| 全名 | LiteLLM — Call 100+ LLM APIs in OpenAI format |
| 倉庫 | [github.com/BerriAI/litellm](https://github.com/BerriAI/litellm) |
| 維護者 | BerriAI, Inc. |
| 創辦人 | Krrish Dholakia, Ishaan Jaffer |
| Stars | ~37,000 |
| Contributors | 1,296+ |
| Releases | 持續發布（每週多次） |
| License | MIT（企業友善） |
| 語言 | Python |
| 融資 | Y Combinator 孵化，$2.1M 種子輪 |
| 企業客戶 | Netflix, Adobe, Samsara, Lemonade 等 |

### 1.2 核心能力

LiteLLM 提供兩種使用模式：

1. **Python SDK** — `litellm.completion()` / `litellm.acompletion()` 統一呼叫介面
2. **Proxy Server（AI Gateway）** — 獨立部署的 HTTP 服務，提供 OpenAI 相容端點 + Anthropic `/v1/messages` 端點

支援 100+ LLM Provider，包含 OpenAI、Anthropic、Google Vertex AI、AWS Bedrock、Azure、Cohere、HuggingFace、VLLM、NVIDIA NIM 等。

### 1.3 成熟度評估

| 指標 | 評價 |
|------|------|
| Star 數（37K） | 同類最高，遠超其他 LLM gateway |
| Contributor 數（1,296+） | 非常活躍的開源社群 |
| 發布頻率 | 每週多次，維護積極 |
| 企業採用 | Netflix、Adobe 等大型企業生產使用 |
| YC 背書 | 融資穩定，短期不會消失 |
| 文件品質 | 完整的 [docs.litellm.ai](https://docs.litellm.ai/docs/) |

**判定：LiteLLM 是目前最成熟的 LLM API 統一層，企業可用。**

---

## 二、Anthropic 格式轉譯能力

### 2.1 架構概述

LiteLLM 的轉譯分為兩個方向：

```
方向 A（主要）：OpenAI 格式 → 各 Provider 原生格式
  - litellm.completion(model="anthropic/claude-sonnet-4-20250514", ...)
  - 內部轉為 Anthropic Messages API

方向 B（Proxy 專用）：Anthropic 格式 → OpenAI 格式 → 其他 Provider
  - POST /v1/messages（接收 Anthropic 格式）
  - 透過 Anthropic Adapter 轉為 OpenAI 格式
  - 再由各 Provider 的 transformation 模組轉為目標格式
```

### 2.2 核心轉換映射

| Anthropic 格式 | OpenAI 格式 | 轉換品質 |
|---------------|------------|---------|
| `system` 參數（頂層） | `messages[0].role = "system"` | 良好 |
| `content` blocks（text/image/tool_use/tool_result） | `content` 字串或 `tool_calls` 陣列 | **有邊緣問題** |
| `tool.input_schema` | `function.parameters` | 良好 |
| `max_tokens`（必填） | `max_tokens`（選填） | 良好 |
| `stop_sequences` | `stop` | 良好 |
| `metadata.user_id` | `user` | 良好 |
| `stream` | `stream` | 良好 |

### 2.3 已知轉換缺陷

#### 缺陷 A：content blocks 攤平（Significant）

Anthropic 的 `content` 是結構化 blocks 陣列（可混合 text、image、tool_use、tool_result），OpenAI 的 `content` 主要是字串。轉換時複合 content 可能遺失結構資訊。

#### 缺陷 B：system prompt 處理差異

Anthropic 的 `system` 為獨立頂層參數（支援陣列格式），OpenAI 則是 messages 陣列中的 `system` role。多段 system prompt 的轉換可能合併為單一訊息。

#### 缺陷 C：stop_reason 映射不完整

| Anthropic `stop_reason` | OpenAI `finish_reason` | 映射狀態 |
|------------------------|----------------------|---------|
| `end_turn` | `stop` | 已映射 |
| `max_tokens` | `length` | 已映射 |
| `tool_use` | `tool_calls` | 已映射 |
| `stop_sequence` | `stop` | 已映射（但遺失具體 sequence） |

#### 缺陷 D：Usage 計算不一致

Anthropic 有 `cache_creation_input_tokens` 和 `cache_read_input_tokens` 兩個 cache 相關欄位，OpenAI 無對應概念。轉換後 prompt caching 統計遺失。

---

## 三、Tool Calling 轉譯保真度

### 3.1 工具定義轉換

**Anthropic → OpenAI 方向：**

```json
// Anthropic 格式
{
  "name": "get_weather",
  "description": "Get weather for a location",
  "input_schema": {
    "type": "object",
    "properties": { "location": { "type": "string" } },
    "required": ["location"]
  }
}

// 轉為 OpenAI 格式
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get weather for a location",
    "parameters": {
      "type": "object",
      "properties": { "location": { "type": "string" } },
      "required": ["location"]
    }
  }
}
```

此基本轉換**品質良好**。

### 3.2 工具呼叫回應轉換

**Anthropic 的 `tool_use` block → OpenAI 的 `tool_calls` 陣列：**

```json
// Anthropic 回應中的 tool_use block
{
  "type": "tool_use",
  "id": "toolu_01A09q90qw90lq917835lq9",
  "name": "get_weather",
  "input": { "location": "San Francisco" }
}

// 轉為 OpenAI 格式
{
  "tool_calls": [{
    "id": "toolu_01A09q90qw90lq917835lq9",
    "type": "function",
    "function": {
      "name": "get_weather",
      "arguments": "{\"location\": \"San Francisco\"}"
    }
  }]
}
```

注意：OpenAI 的 `arguments` 是**字串化的 JSON**，Anthropic 的 `input` 是**原生 JSON 物件**。此序列化/反序列化是常見的邊緣問題來源。

### 3.3 已知的 Tool Calling 邊緣案例

#### 邊緣案例 1：工具名稱長度限制（[Issue #17904](https://github.com/BerriAI/litellm/issues/17904)）

**問題**：OpenAI 對 function name 有 **64 字元上限**，Anthropic 無此限制。Claude Code 定義的工具名稱（如長描述性名稱）經常超過此限制。

**影響**：LiteLLM 直接傳遞工具名稱，不做截斷。當路由到 OpenAI 模型時，請求被拒絕並報 `ContextWindowExceededError`（誤導性的錯誤訊息）。

**狀態**：Open（截至 2026-02）

#### 邊緣案例 2：多重 tool_result 格式（[Issue #16711](https://github.com/BerriAI/litellm/issues/16711)）

**問題**：Claude Code 有時對單一 `tool_use_id` 發送多個 `tool_result` blocks。Anthropic API 允許此行為，但 LiteLLM 在轉換為 OpenAI 格式時無法正確處理。

**狀態**：已透過 [PR #17632](https://github.com/BerriAI/litellm/pull/17632) 修復

#### 邊緣案例 3：Gemini JSON Schema 不相容

**問題**：Gemini 不接受某些標準 JSON Schema 欄位（如 `additionalProperties`）。當工具定義包含這些欄位時，轉發至 Gemini 會失敗。

**緩解**：LiteLLM 的 Vertex/Gemini transformation 模組有 schema 清理邏輯，但並非所有欄位都被處理。

#### 邊緣案例 4：串流中的 tool call 解析

| 問題 | 影響 |
|------|------|
| 串流 chunk 的 `index = -1`，缺少 `id` / `name` | 客戶端解析崩潰 |
| 事件順序違反 Anthropic 的 `tool_use` / `tool_result` 配對規則 | 多輪對話中斷 |
| 串流 tool call 無參數時返回 `""` 而非 `"{}"` | JSON 解析錯誤 |
| 每個串流 chunk 有不同的 `chatcmpl-` ID | 打破 OpenAI 相容性 |

#### 邊緣案例 5：Parallel Tool Calls 與重複 ID

某些 provider 返回的 parallel tool calls 包含重複的 tool call ID。LiteLLM 有去重邏輯，但極端案例仍可能漏處理。

#### 邊緣案例 6：`server_tool_use` 與 `web_search_tool_result`（[Issue #17737](https://github.com/BerriAI/litellm/issues/17737)）

**問題**：LiteLLM 將 `server_tool_use` 錯誤轉為 `tool_use`，且完全丟棄 `web_search_tool_result` block。

**影響**：Claude Code 的 web search 功能在非 Anthropic 後端完全失效。

---

## 四、Extended Thinking / Reasoning 支援

### 4.1 LiteLLM 的 Reasoning 支援概覽

LiteLLM 聲稱支援以下模型的 reasoning/thinking：

| Provider | 模型 | 參數 | 轉換方式 |
|----------|------|------|---------|
| Anthropic | Claude Sonnet/Opus（thinking 模式） | `thinking={"type": "enabled", "budget_tokens": N}` | 原生透傳 |
| OpenAI | o1, o3, o4-mini | `reasoning_effort` | 原生透傳 |
| DeepSeek | DeepSeek R1 | `reasoning_effort` | 透過 `reasoning_effort` |
| Google | Gemini 2.5 Pro/Flash（thinking） | `thinking={"type": "enabled", "budget_tokens": N}` | 轉為 Gemini `thinkingConfig` |

### 4.2 核心問題：Thinking + Tool Calling 的致命衝突

這是 LiteLLM 作為 Claude Code 轉譯層**最嚴重的問題**。

#### 問題描述

Anthropic API 要求：當 `thinking` 啟用時，每個 assistant 回應的 `tool_calls` 訊息**必須**以 `thinking` block 開頭。如果下一輪對話的 assistant 訊息缺少 `thinking_blocks`，API 會返回 400 錯誤：

```
"messages.1.content.0.type: Expected 'thinking' or 'redacted_thinking',
but found 'text'. When 'thinking' is enabled, a final assistant message
must start with a thinking block."
```

#### 為什麼 LiteLLM 觸發此問題

1. OpenAI 相容客戶端（包含非 Anthropic 後端返回的回應）不包含 `thinking_blocks`
2. LiteLLM 在轉譯回 Anthropic 格式時，若上游 provider 不支援 thinking，無法合成 thinking blocks
3. Claude Code 的 sub-agent 機制頻繁觸發多輪 tool calling，放大此問題

#### 受影響場景

| 場景 | 狀態 |
|------|------|
| Claude Code 主對話（thinking 啟用） | **功能正常**（直連 Anthropic 時） |
| Claude Code 主對話 → LiteLLM → 非 Anthropic 模型 | **thinking 必須停用** |
| Claude Code sub-agent → LiteLLM → 任何模型 | **已知 bug**（[Issue #4852](https://github.com/anthropics/claude-code/issues/4852)） |
| OpenAI Agents SDK → LiteLLM → Claude thinking | **已知 bug**（[Issue #765](https://github.com/openai/openai-agents-python/issues/765)） |
| Open WebUI → LiteLLM → Claude thinking + tools | **已知 bug**（[Issue #20464](https://github.com/open-webui/open-webui/issues/20464)） |

#### 官方緩解：`modify_params = True`

LiteLLM 提供了一個全域設定：

```python
# Python SDK
import litellm
litellm.modify_params = True

# Proxy YAML 配置
litellm_settings:
  modify_params: true
```

啟用後，LiteLLM 會偵測到 assistant 訊息缺少 `thinking_blocks`，自動**對該輪對話停用 thinking**。

**代價**：該輪回應**不會使用 extended thinking**，推理品質可能下降。這是「避免 400 錯誤」vs「保持推理品質」的取捨。

### 4.3 跨 Provider Thinking 轉譯

LiteLLM **不支援**將 Anthropic 的 `thinking` blocks 轉譯為其他模型的 reasoning 格式（如 OpenAI 的 `reasoning_effort`、Gemini 的 `thinkingConfig`）。每個 provider 的 reasoning 機制獨立配置，彼此不互通。

**結論**：LiteLLM 的 thinking 支援是 per-provider 的原生透傳，不是跨 provider 的通用抽象層。

---

## 五、Claude Code + LiteLLM 的已知問題彙整

### 5.1 GitHub Issue 完整清單

| Issue | 描述 | 嚴重度 | 狀態 |
|-------|------|--------|------|
| [litellm#11358](https://github.com/BerriAI/litellm/issues/11358) | Claude Code v1.0.8+ 破壞 LiteLLM 相容性（「request ended without sending any chunks」） | Critical | Closed |
| [litellm#13749](https://github.com/BerriAI/litellm/issues/13749) | 圖片上傳報 500 錯誤（`litellm.BadRequestError`） | High | Open |
| [litellm#14478](https://github.com/BerriAI/litellm/issues/14478) | Bedrock passthrough 端點 `/v1/messages/count_tokens` 返回 400 | Medium | Closed |
| [litellm#16711](https://github.com/BerriAI/litellm/issues/16711) | Claude Code tool result 格式不相容（多 tool_result per ID） | High | Closed（PR #17632） |
| [litellm#16718](https://github.com/BerriAI/litellm/issues/16718) | Claude Code v2.0.42 `input_examples` 欄位不被接受 | High | Open |
| [litellm#17904](https://github.com/BerriAI/litellm/issues/17904) | 工具名稱超 64 字元導致 OpenAI 拒絕 | High | Open |
| [litellm#17737](https://github.com/BerriAI/litellm/issues/17737) | `server_tool_use` 被錯誤轉為 `tool_use`，`web_search_tool_result` 被丟棄 | Medium | Open |
| [claude-code#4852](https://github.com/anthropics/claude-code/issues/4852) | Sub-agent 透過 LiteLLM 執行失敗 | High | Open |
| [claude-code#2205](https://github.com/anthropics/claude-code/issues/2205) | 本地 HTTP proxy + LiteLLM gateway 連線錯誤 | Medium | Open |

### 5.2 反覆出現的模式

1. **每次 Claude Code 大版本更新都可能破壞 LiteLLM 相容性** — v1.0.8（2025-06）和 v2.0.42 是兩次已知的破壞事件
2. **Tool calling 是最脆弱的翻譯層** — 多數 bug 集中在 tool_use/tool_result 格式轉換
3. **Streaming + Tool calling 組合是高風險區** — chunk 解析、事件排序、ID 一致性問題頻發
4. **Sub-agent 是 Claude Code 透過 LiteLLM 最難支援的功能** — 涉及巢狀多輪 tool calling + thinking

### 5.3 LiteLLM 的 `additional_drop_params` 應對

LiteLLM 提供了 `additional_drop_params` 機制，可用 JSONPath 語法移除不支援的欄位：

```yaml
# 解決 Claude Code v2.0.42 的 input_examples 問題
litellm_settings:
  additional_drop_params:
    - "tools[*].input_examples"
```

這是一個有效但脆弱的策略 — 每次 Claude Code 新增欄位都需要手動更新 drop list。

---

## 六、LiteLLM Proxy Server 直接作為 Claude Code 的 AI Gateway

### 6.1 LiteLLM 官方支援

LiteLLM Proxy 提供 `/v1/messages` Anthropic 相容端點，可直接被 Claude Code 使用：

```bash
# 啟動 LiteLLM Proxy
litellm --config config.yaml

# 設定 Claude Code 使用 LiteLLM
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_API_KEY=sk-1234  # LiteLLM 的 virtual key
```

### 6.2 LiteLLM Proxy vs claude-code-proxy 比較

| 維度 | LiteLLM Proxy 直接使用 | 1rgs/claude-code-proxy |
|------|----------------------|----------------------|
| **維護** | BerriAI 團隊 + 1,296 contributors | 單人，已停滯 3 個月 |
| **Provider 數** | 100+ | 4（OpenAI, Gemini, Vertex, Anthropic） |
| **企業功能** | RBAC, 成本追蹤, 審計日誌, 速率限制, 虛擬 key | 無 |
| **License** | MIT | 未指定 |
| **測試** | 完整測試套件 | 無 |
| **Tool calling 修復速度** | 通常 1-2 週內有 PR | 無人回應 |
| **Claude Code 專注度** | 低（通用 gateway） | 高（專為 Claude Code 設計） |
| **部署複雜度** | 中（需 config.yaml + Redis 可選 + PostgreSQL 可選） | 低（`pip install` + 單檔） |

### 6.3 LiteLLM Proxy 的 Claude Code 專用配置範例

```yaml
model_list:
  - model_name: claude-sonnet-4-20250514
    litellm_params:
      model: openai/gpt-4.1
      api_key: sk-xxx
  - model_name: claude-haiku-3-5-20241022
    litellm_params:
      model: openai/gpt-4.1-mini
      api_key: sk-xxx

litellm_settings:
  modify_params: true
  drop_params: true
  additional_drop_params:
    - "tools[*].input_examples"

general_settings:
  master_key: sk-1234
```

### 6.4 Trade-offs

#### 優勢（vs 不用 proxy）
- **成本追蹤** — 知道每個 session/user 花了多少錢
- **多模型路由** — 可按模型名稱映射到不同 provider
- **Failover** — 可配置 fallback 模型
- **RBAC** — 團隊成員使用虛擬 key，管理員控制存取
- **審計** — 所有請求/回應可 log

#### 劣勢（vs 直連 Anthropic）
- **額外故障點** — proxy 掛掉 = 全部掛掉
- **延遲增加** — 多一次 hop（通常 5-20ms）
- **Claude Code 更新可能破壞** — 已發生過兩次
- **Thinking 降級** — `modify_params=true` 時部分回合無 thinking
- **Tool calling bug** — 多個 open issues（見第五章）
- **Anthropic 不背書** — 官方文件明確聲明「LiteLLM is a community project. Anthropic does not verify the security of the LiteLLM proxy, including that it does not store or transmit API keys inappropriately.」

### 6.5 是否還需要 claude-code-proxy？

**結論：如果只是要多模型路由，LiteLLM Proxy 直接使用比 claude-code-proxy 更好。**

claude-code-proxy 的核心價值是「簡單」（單檔 Python），但 LiteLLM Proxy 的維護品質、企業功能、社群支援遠超之。除非有極端的簡化需求（如不想裝 LiteLLM 的完整依賴），否則不建議在 LiteLLM 之上再疊一層 claude-code-proxy。

---

## 七、企業就緒度評估

### 7.1 企業客戶

根據 LiteLLM 官方資料與公開案例：

| 客戶 | 規模 | 使用場景 |
|------|------|---------|
| Netflix | 大型 | AI Gateway |
| Adobe | 大型 | LLM 路由 + 成本管理 |
| Samsara | 中大型 | 多模型管理 |
| Lemonade | 中型 | AI 應用 API 管理 |

### 7.2 企業功能清單

| 功能 | 狀態 |
|------|------|
| RBAC（角色控制） | 支援 |
| Virtual Keys（虛擬 API key） | 支援 |
| 成本追蹤（per user / per key） | 支援 |
| 速率限制 | 支援 |
| Guardrails | 支援 |
| 審計日誌 | 支援 |
| SSO / SAML | 企業版 |
| SLA | 企業版 |
| 自託管 | 支援（Docker / K8s） |
| 託管服務 | 有（LiteLLM Cloud） |

### 7.3 企業風險

| 風險 | 嚴重度 | 說明 |
|------|--------|------|
| 早期創業公司（$2.1M 融資） | 中 | 相比 Portkey（$15M）規模較小 |
| 每次 Claude Code 更新可能破壞 | 高 | 已發生兩次，是持續風險 |
| Anthropic 不背書安全性 | 中 | 需自行審計 API key 處理邏輯 |
| 社群維護的 Provider 適配器品質不均 | 中 | 主流 Provider（OpenAI/Anthropic/Gemini）品質高，長尾 provider 品質參差 |

---

## 八、綜合建議

### 8.1 LiteLLM 適合的場景

| 場景 | 推薦度 | 理由 |
|------|--------|------|
| 多 Provider 統一呼叫（SDK 用途） | **強烈推薦** | 核心能力，品質最佳 |
| AI Gateway（企業成本管理/RBAC） | **推薦** | 企業功能完整 |
| Claude Code → OpenAI 模型路由 | **謹慎使用** | Tool calling bug 密度高，thinking 支援有限 |
| Claude Code sub-agent 路由 | **不推薦** | 已知 bug，解決困難 |
| Claude Code + Thinking + Tool Calling | **不推薦** | 致命衝突，`modify_params` 只是降級方案 |

### 8.2 如果使用 LiteLLM 作為 Claude Code 轉譯層

1. **必須設定 `modify_params: true`** — 否則 thinking + tool calling 會 400
2. **必須設定 `drop_params: true` + `additional_drop_params`** — 對抗 Claude Code 版本更新新增的不相容欄位
3. **釘選 Claude Code 版本** — 不要自動更新，每次更新前先在 staging 驗證
4. **釘選 LiteLLM 版本** — 同理
5. **監控 tool calling 成功率** — 這是最容易出問題的地方
6. **準備 fallback 到 Anthropic 直連** — 當 LiteLLM 翻譯層出問題時的逃生路線

### 8.3 替代方案建議

如果目標是「讓 Claude Code 使用非 Anthropic 模型」：

| 方案 | 適用場景 | 優劣 |
|------|---------|------|
| **OpenRouter Anthropic Skin** | 最簡單的多模型存取 | 零部署，但依賴第三方服務 |
| **Ollama v0.14.0+** | 本地模型 | 原生 Anthropic API 相容，零翻譯層 |
| **LiteLLM Proxy** | 企業 AI Gateway | 功能最全，但 Claude Code 專用 bug 多 |
| **nielspeter/claude-code-proxy** | 輕量 Go proxy | 活躍開發，自動學習模型參數，但社群較小 |
| **kiyo-e/claude-code-proxy** | 多部署目標 | Cloudflare Workers / Docker / npm，有 GitHub Actions 整合 |

---

## 九、資料來源

### GitHub Issues
- [BerriAI/litellm#11358](https://github.com/BerriAI/litellm/issues/11358) — Latest Claude Code doesn't work with LiteLLM
- [BerriAI/litellm#13749](https://github.com/BerriAI/litellm/issues/13749) — Image upload error with Claude Code
- [BerriAI/litellm#16711](https://github.com/BerriAI/litellm/issues/16711) — Tool result incompatibility
- [BerriAI/litellm#16718](https://github.com/BerriAI/litellm/issues/16718) — Claude Code v2.0.42 input_examples error
- [BerriAI/litellm#17904](https://github.com/BerriAI/litellm/issues/17904) — Tool name 64-char limit
- [anthropics/claude-code#4852](https://github.com/anthropics/claude-code/issues/4852) — Sub-agent execution with LiteLLM
- [anthropics/claude-code#2205](https://github.com/anthropics/claude-code/issues/2205) — Connection error with LiteLLM gateway
- [open-webui/open-webui#20464](https://github.com/open-webui/open-webui/issues/20464) — Extended Thinking + Tool Use via LiteLLM
- [openai/openai-agents-python#765](https://github.com/openai/openai-agents-python/issues/765) — Tool calling with LiteLLM + Claude thinking

### 官方文件
- [LiteLLM Docs](https://docs.litellm.ai/docs/)
- [LiteLLM Anthropic Provider](https://docs.litellm.ai/docs/providers/anthropic)
- [LiteLLM Reasoning Content](https://docs.litellm.ai/docs/reasoning_content)
- [LiteLLM Function Calling](https://docs.litellm.ai/docs/completion/function_call)
- [LiteLLM Drop Params](https://docs.litellm.ai/docs/completion/drop_params)

### 社群專案
- [1rgs/claude-code-proxy](https://github.com/1rgs/claude-code-proxy)
- [nielspeter/claude-code-proxy](https://github.com/nielspeter/claude-code-proxy)
- [kiyo-e/claude-code-proxy](https://github.com/kiyo-e/claude-code-proxy)
- [starbaser/ccproxy](https://github.com/starbaser/ccproxy)
- [CJHwong/anthropic-proxy-litellm](https://github.com/CJHwong/anthropic-proxy-litellm)

### 分析工具
- [DeepWiki — Tool Calling and Function Integration](https://deepwiki.com/BerriAI/litellm/8.1-tool-calling-and-function-integration)
- [DeepWiki — Reasoning and Extended Thinking](https://deepwiki.com/BerriAI/litellm/8.6-reasoning-and-extended-thinking)
