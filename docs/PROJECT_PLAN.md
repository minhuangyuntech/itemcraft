# ItemCraft AI 命題網站 App 規劃

建立日期：2026-06-09

## 1. 專案目標

ItemCraft 是一個協助命題者整理題庫、匯入既有試題、上傳參考資料、設定引用來源，並透過 AI API 輔助產生、改寫、解析與分類題目的網站 App。系統需支援資料庫保存、多人登入、欄位客製、題目版本管理，以及後續部署到一般雲端主機或校內主機。

## 2. 建議技術選型

### 推薦方案：Django + PostgreSQL

Django 合適，而且很適合作為第一版主架構。

建議使用：

- 後端：Django 5.2 LTS
- API：Django Ninja 或 Django REST Framework
- 前端：Django Templates + HTMX + Alpine.js；若未來需要更複雜互動，再升級 React 或 Vue
- 資料庫：PostgreSQL
- 背景工作：Celery + Redis
- 檔案儲存：本機 media 目錄起步，正式環境可改 S3 相容物件儲存
- 匯入 Excel/CSV：pandas + openpyxl
- AI API：後端統一封裝 provider gateway，支援 OpenAI、Azure OpenAI、Anthropic、Google Gemini 或自訂 OpenAI-compatible endpoint
- 部署：Docker Compose，Nginx + Gunicorn/Uvicorn + PostgreSQL + Redis

### 為什麼 Django 合適

- Django ORM、Admin、Auth、Form、File Upload 都很成熟，命題系統需要大量資料維護，能少寫很多基礎設施。
- PostgreSQL 搭配 Django ORM 易於處理題目、分類、來源、匯入紀錄、AI 生成紀錄、版本歷史等關聯資料。
- Django Admin 可先作為內部管理後台，前台再逐步打造專用工作介面。
- Django 5.2 是 LTS，官方文件說明其為長期支援版本，安全更新至少三年，適合教育或內部工具長期維護。
- 官方部署 checklist 完整，對 SECRET_KEY、DEBUG、ALLOWED_HOSTS、資料庫、靜態檔與 media 檔案都有明確注意事項。

參考：

- Django 5.2 release notes: https://docs.djangoproject.com/en/6.1/releases/5.2/
- Django deployment checklist: https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/
- Next.js route handlers / API routes: https://nextjs.org/docs
- FastAPI deployment docs: https://fastapi.tiangolo.com/deployment/

### 替代方案比較

| 方案 | 優點 | 缺點 | 適合情境 |
| --- | --- | --- | --- |
| Django + PostgreSQL | 資料庫、權限、後台、檔案、表單完整；部署穩定 | 前端若要高度 SPA 需額外整合 | 最推薦，適合本專案 |
| FastAPI + React | API 輕量、型別清楚、前後端分離 | 需要自行組 auth/admin/form/file/import 管理 | 團隊偏 API-first 或已有 React 經驗 |
| Next.js full-stack | 前端體驗佳，部署到 Vercel 容易 | 資料匯入、檔案處理、管理後台與長任務需額外設計 | 偏展示與輕量 SaaS |
| Laravel + MySQL/PostgreSQL | 表單、後台、部署成熟 | 若 AI/資料處理偏 Python，整合成本較高 | 團隊偏 PHP |

## 3. 題目欄位規格

依照附圖，第一版建議支援以下欄位：

| 欄位 | 說明 | 型態 |
| --- | --- | --- |
| 類型 | 題目類型，可自訂下拉選單 | 可設定選項 |
| 狀態 | 題目狀態，可自訂下拉選單 | 可設定選項 |
| 原 AI 領域範疇 | 原始領域或知識範疇 | 文字 / 下拉可擴充 |
| 題目內容 | 原題題幹與 4 個選項 | 結構化欄位 |
| 答案 | 原題答案 | A/B/C/D |
| 新題目內容 | AI 或人工改寫後題幹與 4 個選項 | 結構化欄位 |
| 新答案 | 新題答案 | A/B/C/D |
| 新解析 | 新題解析 | 長文字 |
| 難易度 | 題目難易度 | 下拉選單 |
| 主層面 | 主要能力面向 | 下拉 / 文字 |
| 次層面 | 次要能力面向 | 下拉 / 文字 |
| 認證內容說明 | 對應認證、課綱或測驗說明 | 長文字 |
| 分類依據 | 分類或命題依據 | 長文字 |

### 題目輸入介面

題目內容不建議只用一個大型文字框，應拆成：

- 題幹
- 選項 A
- 選項 B
- 選項 C
- 選項 D
- 答案 radio / segmented control
- 解析
- 來源引用

操作設計：

- 左側：題目清單與篩選
- 中央：題目編輯器
- 右側：AI 輔助面板與引用來源
- 題目與新題目可並排比較
- 支援一鍵「以原題產生新題」、「產生解析」、「檢查答案一致性」、「依來源重寫」

## 4. 自訂下拉選單

至少支援「類型」與「狀態」自訂，建議所有分類欄位都抽象成可設定選單。

資料表概念：

- OptionGroup：例如 type、status、difficulty、main_dimension、sub_dimension
- OptionItem：選項名稱、顏色、排序、是否啟用

好處：

- 使用者可在設定頁新增「既有基礎」、「新命」、「調整」、「審核中」等選項。
- 匯入資料時可自動建立未知選項，或提示使用者對應到既有選項。
- 未來不同考試或專案可擁有不同選單組。

## 5. Excel / CSV 匯入功能

匯入流程：

1. 使用者上傳 `.xlsx`、`.xls` 或 `.csv`。
2. 系統讀取標題列與前 20 筆資料，顯示預覽。
3. 自動比對欄位名稱，例如「類型」、「狀態」、「題目」、「題幹」、「選項A」、「答案」、「新解析」。
4. 無法辨識的欄位讓使用者手動選擇對應。
5. 系統驗證必填欄位、答案格式、選項數量與重複題目。
6. 匯入前顯示摘要：新增幾筆、更新幾筆、錯誤幾筆。
7. 寫入 ImportJob、ImportRowError，方便追蹤。

欄位對應策略：

- 精準比對：欄位名稱完全相同。
- 同義詞比對：例如「題目(包含選項)」、「題目內容」、「題幹」。
- 模糊比對：去空白、去括號、大小寫正規化。
- AI 輔助比對：使用者允許時，可讓 AI 判斷欄位用途，但最後需人工確認。

## 6. AI 功能規劃

### 設定頁

使用者可設定：

- Provider：OpenAI、Azure OpenAI、Anthropic、Gemini、OpenAI-compatible
- API Key
- Base URL
- Model
- Temperature
- Max tokens
- 是否允許使用上傳參考資料
- 預設提示詞模板

安全建議：

- API Key 必須加密後存放，不以明文寫入資料庫。
- 後端呼叫 AI API，前端不直接接觸 API Key。
- 每次 AI 呼叫保存 request 摘要、使用模型、token 用量、輸出結果與操作者，但避免保存完整 API Key 或敏感原文。

### AI 輔助命題功能

- 依原題改寫新題
- 依參考資料產生題目
- 產生四選一選項
- 產生答案與解析
- 檢查題幹與答案是否一致
- 檢查題目是否過度依賴未引用來源
- 依「主層面 / 次層面 / 認證內容說明」建議分類
- 產生分類依據

### 引用與來源

每個題目可連結：

- 上傳參考檔案
- 引用網址
- 法規名稱
- 條文或章節
- 擷取片段
- 存取日期

若使用 RAG，可先做簡化版：

1. 上傳 PDF、DOCX、TXT、CSV。
2. 後端抽取文字。
3. 依段落切分並建立 ReferenceChunk。
4. AI 產生題目時只附上相關段落。
5. 輸出時要求 AI 列出引用來源 ID。

進階版可加入向量資料庫：

- PostgreSQL + pgvector
- 或 Chroma / Qdrant

第一版若以易部署為主，建議 PostgreSQL + pgvector。

## 7. 核心資料模型草案

```text
User
Project
Question
QuestionVersion
Choice
OptionGroup
OptionItem
ReferenceSource
ReferenceFile
ReferenceChunk
Citation
ImportJob
ImportRowError
AIProviderSetting
AIRequestLog
```

Question 主要欄位：

- project
- type_option
- status_option
- original_domain
- stem
- choice_a
- choice_b
- choice_c
- choice_d
- answer
- revised_stem
- revised_choice_a
- revised_choice_b
- revised_choice_c
- revised_choice_d
- revised_answer
- revised_explanation
- difficulty_option
- main_dimension
- sub_dimension
- certification_note
- classification_basis
- created_by
- updated_by
- created_at
- updated_at

QuestionVersion：

- question
- snapshot_json
- change_note
- source：manual、import、ai
- created_by
- created_at

## 8. 頁面與功能模組

### 題庫列表

- 搜尋題幹、解析、分類依據
- 依類型、狀態、難易度、主層面篩選
- 批次匯出 CSV / Excel
- 批次改狀態
- 批次 AI 檢查

### 題目編輯器

- 題幹與 4 選項獨立輸入
- 原題與新題並排
- 答案選擇
- 解析輸入
- 分類欄位
- 引用來源連結
- 版本歷史

### AI 工作台

- 選擇題目或來源
- 選擇提示詞模板
- 產生新題、解析、分類
- 顯示 AI 輸出與差異比對
- 使用者確認後才寫入題目

### 匯入頁

- 上傳檔案
- 欄位自動對應
- 預覽與錯誤檢查
- 匯入摘要
- 匯入紀錄查詢

### 參考資料庫

- 上傳檔案
- 新增來源網址
- 設定法規名稱、章節、存取日期
- 查看抽取文字與可引用片段

### 設定頁

- AI Provider/API Key
- 自訂下拉選單
- 題目欄位顯示設定
- 匯入欄位同義詞
- 使用者與權限

## 9. 權限設計

建議角色：

- Admin：系統管理、使用者、選單、AI 設定
- Editor：新增、修改、匯入、使用 AI
- Reviewer：審核題目、改狀態、留言
- Viewer：只讀

題目狀態範例：

- 草稿
- AI 生成
- 人工調整
- 待審核
- 已通過
- 退回修改
- 停用

## 10. 部署架構

第一版 Docker Compose：

```text
nginx
django-web
celery-worker
postgres
redis
```

正式環境注意：

- 開啟 HTTPS
- DEBUG=False
- SECRET_KEY 使用環境變數
- API Key 使用加密欄位
- media 檔案定期備份
- PostgreSQL 定期備份
- 上傳檔案限制副檔名與大小
- AI request 設 token 與費用上限

## 11. 開發里程碑

### Phase 0：規格確認

- 確認欄位名稱
- 確認角色權限
- 確認是否多人使用
- 確認部署主機環境
- 確認 AI provider

### Phase 1：MVP

- Django 專案初始化
- 使用者登入
- 題目 CRUD
- 類型與狀態自訂選單
- 題庫列表與篩選
- PostgreSQL 連線

### Phase 2：匯入與匯出

- Excel / CSV 上傳
- 欄位自動對應
- 匯入預覽與錯誤報告
- 匯出題庫

### Phase 3：AI 輔助

- API Key 設定
- AI provider gateway
- 產生新題
- 產生解析
- 答案一致性檢查
- AI request log

### Phase 4：引用來源

- 參考檔案上傳
- 來源網址管理
- 引用片段管理
- AI 依來源產生題目

### Phase 5：審核與版本

- 題目版本歷史
- 審核流程
- 批次操作
- 權限細分

## 12. 初步結論

Django 非常合適作為 ItemCraft 的主架構。這個專案的重點不是單純展示頁，而是資料表單、權限、檔案、匯入、後台管理、AI API 呼叫與資料庫互動；Django 的內建能力能讓第一版更快落地，也便於部署到一般 Linux 主機、Docker 主機或雲端平台。

建議第一版不要一開始採用大型前端 SPA。先用 Django Templates + HTMX 做出高效率的題庫與編輯介面，等 AI 工作台或即時協作變得更複雜時，再將特定頁面局部改成 React/Vue。

