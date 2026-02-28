# AI Agent 架構方案審核意見書

審核日期：2026-02-28
審核重點：前端 UI 方案可行性與客製化能力

---

## 一、總結評價

方案的整體技術判斷方向正確——Claude Agent SDK 的 agent loop 品質確實是目前業界最成熟的，MCP 封裝業務工具作為長期投資也合理。但在**前端 UI 選型**上，推薦 Claudex 作為核心方案存在重大風險，且遺漏了更成熟的替代方案。

**結論：建議不採用 Claudex 作為 UI 層，改採分層架構，UI 層獨立選型。**

---

## 二、Claudex 實際狀態（事實查核）

方案中對 Claudex 的描述有多處需要修正：

### 2.1 專案成熟度遠低於預期

| 指標 | Claudex | OpenHands（對比） | CUI（對比） |
|------|---------|-------------------|-------------|
| GitHub Stars | 216 | 32,000+ | 1,100 |
| Contributors | ~1-3 人 | 188+ 人 | 4 人 |
| 版本 | v0.1.29 | 1.4（Production） | — |
| 授權 | Apache 2.0 | MIT | — |

**關鍵風險：Bus factor = 1。** 主要維護者為單一開發者（Michael Gendy），雖然 commit 頻率高（626 commits），但以 216 stars 的社群規模，一旦維護者停止更新，專案即進入孤兒狀態。

### 2.2「in-browser VS Code」的實際情況

方案描述 Claudex「含 in-browser VS Code terminal sandbox」，這是**行銷性語言**，實際組成為：

- **Monaco Editor**：VS Code 的編輯器元件（不是完整 VS Code）
- **xterm.js**：瀏覽器端終端機模擬器
- **VNC viewer**：遠端桌面存取

這三者組合提供了「類 IDE 體驗」，但不等於完整的 VS Code。真正的 browser-based VS Code 是 code-server 或 GitHub Codespaces 等級的產品。

### 2.3 沙箱環境依賴外部付費服務

Claudex 的沙箱執行依賴 **E2B.dev**（付費雲端沙箱服務），Docker 是免費替代方案但功能受限。方案中完全未提及此成本。

### 2.4「唯一同時滿足條件」不準確

方案聲稱 Claudex 是「目前唯一同時滿足以下條件的開源方案」，但至少以下專案也滿足類似條件：

- **CUI（wbopan/cui）**：1,100 stars，支援 Claude Code + 多模型路由，支援平行背景 Agent，推播通知
- **CloudCLI（siteboon/claudecodeui）**：完整 Web UI，含 shell terminal、檔案總管、Git explorer
- **Claudia GUI（claudia.so）**：Y Combinator 投資的桌面應用，Tauri 2 + React 18

---

## 三、前端 UI 深度分析

既然需求是「功能強大、可客製化的 UI」，以下是各方案的 UI 架構比較：

### 3.1 Claudex 前端架構

```
技術棧：React 19 + Vite + Tailwind CSS + TypeScript（55.2%）
狀態管理：React Context + Zustand 混用
設計系統：全灰階（monochromatic），無品牌色
元件載入：React.lazy() + Suspense 動態載入重型元件
```

**客製化能力評估：**

| 面向 | 評分 | 說明 |
|------|------|------|
| 設計系統修改 | ⚠️ 中等 | 全灰階設計深度嵌入 Tailwind token，加入品牌色需重寫 token 系統 |
| 元件擴展 | ⚠️ 中等 | 是完整應用而非元件庫，擴展等於 fork 後修改 |
| 佈局自訂 | ⚠️ 中等 | Context 架構清晰但高度耦合於特定佈局 |
| API 整合 | ✅ 較好 | FastAPI 後端，REST 介面清楚 |
| 內部 API 穩定性 | ❌ 低 | v0.1.x 階段，內部 API 隨時可能變動 |

**核心問題：Claudex 是一個完整的應用程式，不是一個 UI 框架或元件庫。「客製化」意味著 fork 整個專案然後在裡面改，而不是 import 元件來組裝。**

### 3.2 更適合的 UI 方案

根據「功能強大、可客製化」的需求，以下方案更值得評估：

#### 方案 A：OpenHands 前端（推薦評估）

```
技術棧：React + React Router v7 + Vite 7.3 + TanStack Query
元件庫：@openhands/ui（npm 獨立發佈）
設計系統：TypeScript + Tailwind CSS
國際化：內建 i18n 支援
```

**優勢：**
- 前端元件庫獨立發佈到 npm（`@openhands/ui`），可單獨引用
- 32,000+ stars 的社群保證了長期維護
- 完整的 sandbox IDE（真正的 VS Code IDE + terminal + browser）
- MIT 授權（核心部分），商業使用無虞
- 支援任意 LLM 後端，包括 Claude

**劣勢：**
- 不是專門為 Claude Agent SDK 設計的，整合需要額外工作
- 有自己的 agent loop，與 Claude Agent SDK 的 agent loop 存在架構衝突
- enterprise 目錄需付費授權

#### 方案 B：自建 UI，使用 Vercel AI SDK（最大客製化彈性）

```
技術棧：React / Next.js + Vercel AI SDK + AI Elements
設計系統：完全自訂（shadcn/ui + Tailwind 或其他）
```

**優勢：**
- 最大程度的客製化自由度——從零開始，完全符合業務需求
- Vercel AI SDK 提供 streaming、tool use、multi-step agent 的 React hooks
- AI Elements 提供預製的 agent UI 元件（可選用或不用）
- 可深度整合 Claude Agent SDK 的 TypeScript 版本
- 設計系統完全自主，品牌識別不受限

**劣勢：**
- 開發工作量最大（預估 4-6 週純 UI 開發）
- 需要自行處理 sandbox、terminal、file editor 等重型元件

#### 方案 C：Chainlit（最快上線，Python 生態系友善）

```
技術棧：Python 後端 + 自動生成 Web UI
通訊：FastAPI + WebSocket
設計：可用 custom CSS + custom React 元件擴展
```

**優勢：**
- 與現有 amux 的 Python 技術棧一致
- 開箱即用的 agent 對話 UI，含中間步驟視覺化
- 原生 streaming、多模態支援（圖片、PDF、音訊）
- 直接整合 Claude API，同時支援 LangChain、LlamaIndex
- 最快的原型到上線時間

**劣勢：**
- 深度客製化受限（畢竟是 Python 框架生成的 UI）
- 前端元件不如純 React 方案靈活
- UI 風格偏向「對話式」，不適合需要重度 IDE 功能的場景

---

## 四、建議架構：分層解耦

不應該讓 UI 選型綁死 Agent 引擎選型。建議將架構拆為三層，各層獨立選型：

```
┌─────────────────────────────────────────────────┐
│  Layer 3: 前端 UI                                │
│  → 獨立選型，不綁定特定 agent SDK               │
│  → 推薦：Vercel AI SDK 自建（最大彈性）         │
│     或 OpenHands @openhands/ui（最快 IDE 體驗）  │
├─────────────────────────────────────────────────┤
│  Layer 2: Agent API Gateway                      │
│  → REST/WebSocket API，統一對外介面             │
│  → 封裝 agent session 管理、streaming、權限     │
├─────────────────────────────────────────────────┤
│  Layer 1: Agent Runtime                          │
│  → Claude Agent SDK（主要）                     │
│  → anthropic-bridge（模型路由 / failover）      │
│  → 確定性 pipeline（降級方案）                  │
├─────────────────────────────────────────────────┤
│  Layer 0: 業務能力                               │
│                                                  │
│  Skills（流程知識層 — "how"）                    │
│  → 網站架構生成流程（SKILL.md）                 │
│  → SEO 分析工作流程（SKILL.md）                 │
│  → 內容產出規範與流程（SKILL.md）               │
│  → 業務規則、品質標準、SOP                      │
│                                                  │
│  MCP Servers（系統連接層 — "what"）              │
│  → 客戶產品目錄 API（資料存取）                 │
│  → SEO 工具 API（Ahrefs, GSC 等）               │
│  → CMS 寫入介面                                 │
│  → 內部資料庫查詢                               │
└─────────────────────────────────────────────────┘
```

### Skills vs MCP Servers：原方案的重大遺漏

原方案將所有業務工具統一歸類為 MCP Servers，這混淆了兩個本質不同的層次：

| 維度 | Skills | MCP Servers |
|------|--------|-------------|
| 本質 | 流程知識（domain expertise） | 系統連接（tool access） |
| 回答的問題 | **怎麼做**（How） | **能用什麼**（What） |
| 實作方式 | SKILL.md（Markdown + YAML frontmatter） | 編譯程式碼（Node.js, Python） |
| 確定性 | 非確定性（Claude 推理執行） | 確定性（同輸入 = 同輸出） |
| 開發成本 | 極低（寫 Markdown） | 中等（寫程式碼 + 部署） |
| 可移植性 | Claude Code 生態系內 | 跨平台（任何支援 MCP 的 SDK） |

**正確的分工模式：**

以「網站架構生成」為例：
- **Skill**（`/.claude/skills/site-architecture/SKILL.md`）定義：
  - 生成流程的 SOP（先分析客戶產品 → 規劃 URL 結構 → 產生 sitemap → 生成頁面內容）
  - 品質標準（每頁至少 3 個內部連結、H1 必須含主關鍵字等）
  - 例外處理規則（產品數 < 10 時用單層架構、> 100 時用分類架構）
- **MCP Server** 提供：
  - `fetch_product_catalog(customer_id)` — 從客戶系統拉產品資料
  - `check_keyword_volume(keywords[])` — 查詢關鍵字搜尋量
  - `write_to_cms(pages[])` — 將生成的頁面寫入 CMS

Skill 負責**編排**（告訴 Claude 按什麼順序、什麼規則做事），MCP Server 負責**執行**（提供具體的資料存取能力）。

**這區分至關重要，因為：**
1. **降級策略更精確**：模型切換時，Skills 可能需要調整（不同模型理解 Markdown 指令的能力不同），但 MCP Servers 完全不受影響
2. **團隊分工更清楚**：業務人員可以維護 Skills（寫 Markdown），工程師維護 MCP Servers（寫程式碼）
3. **迭代速度不同**：業務規則變動時改 SKILL.md 即可，不需要重新部署任何服務

### 為什麼不用 Claudex 的全家桶？

Claudex 把 Layer 1-3 全部綁在一起。這意味著：

1. **UI 修改被 agent 引擎綁架**：想改 UI 就得 fork 整個專案，連後端一起維護
2. **升級風險集中**：Claudex 升級可能同時影響 UI + 後端 + agent 引擎
3. **無法獨立替換任何一層**：如果未來 UI 需求超出 Claudex 能力，遷移成本極高
4. **v0.1.x 的穩定性風險**：在單一維護者的 v0.1 專案上構建核心產品，風險過高

### 分層架構的好處

1. **UI 可獨立迭代**：前端團隊可以不碰 agent 引擎就改進使用者體驗
2. **Agent 引擎可替換**：Claude Agent SDK 升級或替換不影響前端
3. **業務工具跨平台**：MCP Servers 在任何架構下都能用
4. **漸進式交付**：可以先用簡單 UI（如 Chainlit）驗證業務，再換成自建 UI

---

## 五、方案中其他觀察

### 5.1 正確的判斷

- ✅ Claude Agent SDK 的 agent loop 品質是核心價值，不只是模型本身
- ✅ MCP 封裝業務工具是正確的長期投資（但應搭配 Skills，見第四節）
- ✅ 分級 failover 策略（同模型異基礎設施 → 異模型 → 確定性 pipeline）思路清晰
- ✅ anthropic-bridge 確實是真實存在的專案，可用於模型路由

### 5.2 需要補充的風險

- ⚠️ **anthropic-bridge 也是小型社群專案**（同一作者 Mng-dev-ai），bus factor 同樣是 1
- ⚠️ **E2B 沙箱成本未列入估算**，如果需要雲端沙箱，這是持續性費用
- ⚠️ **「1 位全端工程師投入 8 週」的估算偏樂觀**，如果要 fork Claudex 並客製化 UI 到符合品牌需求，光是理解 626 commits 的 codebase 就需要 1-2 週
- ⚠️ **缺少前端效能指標**：方案未定義 UI 的效能要求（首屏載入時間、streaming 延遲、並發使用者數）

### 5.3 anthropic-bridge 的補充說明

anthropic-bridge 實際上有多個同名專案：

| 專案 | 語言 | 功能 |
|------|------|------|
| Mng-dev-ai/anthropic-bridge | Python | Anthropic API → OpenRouter |
| marcodelpin/anthropic-bridge | Node.js | Anthropic API → OpenAI 格式 → OpenRouter |
| mukiwu/anthropic-api-bridge | Python/FastAPI | Anthropic API → 本地 LLM（Ollama, LM Studio） |

方案中未指明使用哪一個。如果是 Mng-dev-ai 的版本（與 Claudex 同作者），則整個技術棧的 bus factor 集中在同一人身上，風險進一步放大。

---

## 六、修訂建議

### 如果堅持快速上線（4 週內）

```
UI：Chainlit（Python 生態，與 amux 一致）
Agent：Claude Agent SDK（Python 版）
模型路由：anthropic-bridge（但需評估 fork 維護的意願）
業務流程：Skills（SKILL.md — 網站架構生成 SOP、SEO 分析流程、內容規範）
業務連接：MCP Servers（客戶資料 API、SEO 工具 API、CMS 介面）
```

### 如果追求「功能強大、可客製化」（推薦）

```
UI：Vercel AI SDK + shadcn/ui 自建（6-8 週）
   或 fork OpenHands @openhands/ui 元件（4-6 週）
Agent API：自建 API Gateway（FastAPI or Next.js API Routes）
Agent Runtime：Claude Agent SDK（TypeScript 版，與前端同語言）
模型路由：自建簡易 proxy 或 使用 OpenRouter 直接路由
業務流程：Skills（SKILL.md — 可由業務人員維護的 Markdown 工作流程定義）
業務連接：MCP Servers（確定性的資料存取與外部系統整合）
```

### 如果要同時評估多方案（建議的 Phase 1）

在 Phase 1 的 2 週 POC 期間，不只測 Claudex，同時 spike 測試：

1. **Claudex** — 安裝、體驗、評估客製化難度
2. **OpenHands** — 安裝、體驗其 IDE UI、評估 Claude 整合度
3. **Vercel AI SDK + Claude Agent SDK (TS)** — 花 2-3 天做一個最小 prototype

三個方案平行比較，用同一個業務場景（如「網站架構生成」）作為 benchmark，再做最終決策。

---

## 七、結論

| 維度 | 原方案（Claudex） | 建議修訂 |
|------|-------------------|----------|
| UI 成熟度 | v0.1.x, 216 stars | 選用更成熟方案或自建 |
| 客製化能力 | 中等（需 fork 整個應用） | 高（分層架構，UI 獨立選型） |
| Bus factor | 1（Claudex + anthropic-bridge 同一作者） | 分散（使用多個獨立專案） |
| 架構耦合度 | 高（UI + Agent + Backend 綁定） | 低（三層解耦） |
| 上線時間 | 8 週（樂觀） | 8-10 週（含 UI 自建，但更穩固） |
| 長期維護風險 | 高 | 低 |

**核心建議：**

1. **Agent Runtime 層**（Claude Agent SDK + failover 策略）判斷正確，可採用
2. **UI 層**應獨立選型，不要綁定在 Claudex 這個小型社群專案上
3. **業務工具層**應拆分為 Skills（流程知識）+ MCP Servers（系統連接），而非全部歸類為 MCP — 這讓業務人員能用 Markdown 維護工作流程，工程師專注於 API 整合
