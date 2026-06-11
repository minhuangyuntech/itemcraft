# ItemCraft 接手與測試指南

最後整理：2026-06-11

## 1. 專案概況

ItemCraft 是 Django + SQLite + Bootstrap 5 的 AI 輔助命題系統 MVP。主要用途是管理四選一題庫、匯入既有 Excel/CSV、整理命題參考資料，並透過 OpenAI-compatible API 或 Ollama 進行命題、審題與受控資料庫操作。

目前仍屬開發版，適合在本機或測試主機使用。正式部署前需補強 API Key 加密、權限分級、背景工作、檔案儲存與操作審計。

## 2. 開發環境

專案目錄：

```powershell
D:\projects\ItemCraft
```

Python 虛擬環境已在：

```powershell
D:\projects\ItemCraft\venv
```

啟動方式：

```powershell
cd D:\projects\ItemCraft
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

網站入口：

```text
http://127.0.0.1:8000/
```

若沒有管理者帳號：

```powershell
.\venv\Scripts\python.exe manage.py createsuperuser
```

基本檢查：

```powershell
.\venv\Scripts\python.exe manage.py check
node --check static\js\question-form.js
```

## 3. 主要功能狀態

### 首頁與登入

- `/` 是公開首頁。
- 管理者登入後才能進入工作台與題庫管理。
- 目前使用 Django staff 權限控管，需 `is_staff=True`。

### 工作台

路徑：

```text
/dashboard/
```

功能：

- 顯示題目數、參考來源/檔案數、最近匯入。
- AI 對話框可選 API 來源、模型、參考來源、參考檔案。
- 可勾選「提供題庫資料表給 AI 讀取」。
- 可設定讀取題目數，預設 50，最多 200。
- 可勾選「允許 AI 直接修改題庫」。
- AI 執行時前端會顯示「AI 思考中」，送出按鈕 disabled，並提供中斷按鈕。

### 題庫

路徑：

```text
/questions/
```

功能：

- 題庫列表前方有編號。
- 可依類型、狀態與關鍵字篩選。
- 顯示題幹、類型、狀態、完成狀態、答案、難易度、更新時間。

### 題目編輯

路徑：

```text
/questions/new/
/questions/<id>/edit/
```

欄位：

- 類型：`既有基礎`、`既有進階`、`公務基礎`、`公務進階`
- 狀態：`調整`、`新命`
- 原AIE領域範疇：`資料隱私、資料安全與合規`、`資料偏見與公平性`
- 難易度：`基礎`、`進階`
- 題幹
- 選項 A/B/C/D
- 答案
- 解析
- 主層面：預設 `AI政策法制`
- 次層面：`AI法規與資安風險管理`、`AI應用下的倫理準則與智慧財產權實務`
- 認證內容說明會依次層面自動填入
- 分類依據
- 已完成鎖定

特殊功能：

- 題幹欄位旁有 `拆解 A-D 選項` 按鈕。
- 可貼上包含 `A.`、`B.`、`C.`、`D.` 的完整題目並自動拆解。
- 題目標記 `已完成鎖定` 後，人工與 AI 都不能再修改。

### 匯入 Excel / CSV

路徑：

```text
/import/
```

支援：

- `.xlsx`
- `.xls`
- `.csv`

會嘗試依欄位名稱自動對應，例如：

- 類型
- 狀態
- 原AIE領域範疇
- 題目內容
- 答案
- 新解析 / 解析
- 難易度
- 主層面
- 次層面
- 認證內容說明
- 分類依據

注意：目前匯入邏輯偏 MVP，錯誤列只計數，尚未提供逐列錯誤報告。

### 參考資料

路徑：

```text
/references/
```

功能：

- 新增來源網址。
- 填寫引用資訊。
- 上傳參考檔案。

### 設定

路徑：

```text
/settings/
```

功能：

- 管理多個 AI API 來源。
- 每個 API 來源可設定名稱、Provider、Base URL、API Key、啟用狀態。
- 可先按 `載入 Model`，再從下拉選單選擇預設模型，最後儲存。
- 已存在 API 來源可編輯或刪除。
- 每個 API 來源可按 `測試` 驗證設定。
- 管理下拉選單項目。
- 建立與還原 SQLite 備份。
- 匯出與匯入資料包。

## 4. AI API 規格

目前採 OpenAI-compatible API：

```text
GET  /models
POST /chat/completions
```

OpenAI Base URL：

```text
https://api.openai.com/v1
```

Ollama Windows Base URL：

```text
http://localhost:11434/v1
```

Ollama API Key 可填任意字串，例如：

```text
ollama
```

模型相容性：

- OpenAI `gpt-5` 系列不送自訂 `temperature`，避免 `unsupported_value`。
- 一般 OpenAI chat model 仍可送 `temperature=0.4`。
- Ollama 模型如 `gemma3:latest`、`mistral:latest` 會被視為可用 chat model。

## 5. AI 讀取與編輯資料庫

AI 可讀取題庫摘要，內容包含：

- 題目 ID
- 是否完成鎖定
- 類型、狀態、難易度
- 題幹與四個選項
- 答案與解析
- 主層面、次層面
- 認證內容說明
- 分類依據

AI 也會讀取命題參考資料表 `ItemWritingReference`。

允許 AI 修改題庫時，AI 必須輸出 JSON actions，例如：

```json
{
  "actions": [
    {
      "action": "create_question",
      "fields": {
        "stem": "題幹",
        "choice_a": "選項 A",
        "choice_b": "選項 B",
        "choice_c": "選項 C",
        "choice_d": "選項 D",
        "answer": "A",
        "revised_explanation": "解析"
      }
    },
    {
      "action": "update_question",
      "id": 1,
      "fields": {
        "stem": "更新後題幹"
      }
    },
    {
      "action": "mark_completed",
      "id": 1
    }
  ]
}
```

目前允許的 action：

- `create_question`
- `update_question`
- `mark_completed`

安全規則：

- 執行 AI 資料庫修改前，系統會自動建立 SQLite 備份。
- `is_completed=True` 的題目不能被 AI 修改。
- 每次 AI 資料庫操作會寫入 `AIDatabaseOperation` 紀錄。

## 6. 命題參考資料

資料表：

```text
ItemWritingReference
```

目前已建立兩個次層面的命題參考。

### AI法規與資安風險管理

包含：

- AI法規與資安風險管理命題總原則
- 24.資安規範與資料保護
- 25.AI法規與資安風險管理實務
- 26.生成式AI使用限制與適法性

### AI應用下的倫理準則與智慧財產權實務

包含：

- AI應用下的倫理準則與智慧財產權實務命題總原則
- 27.最終問責與行政倫理
- 28.智財權、授權條款與使用揭露
- 29.資料可信度與透明度

## 7. 資料匯出與移轉

設定頁提供資料包匯出與匯入。

目前已匯出一份：

```text
exports/itemcraft-content-bundle.json
```

匯出內容包含：

- `OptionGroup`
- `OptionItem`
- `ReferenceSource`
- `ReferenceFile`
- `ItemWritingReference`
- `Question`

預設不包含：

- AI API Key
- 備份紀錄
- AI 操作紀錄

匯入時：

- 先建立 SQLite 備份。
- 再用 JSON fixture 匯入資料。

另一個環境建議流程：

```powershell
git clone git@github.com-minhuangyuntech:minhuangyuntech/itemcraft.git
cd itemcraft
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py runserver
```

登入後到 `設定` 匯入 `itemcraft-content-bundle.json`。

## 8. 重要資料模型

主要 model 位於：

```text
questions/models.py
```

核心 model：

- `Question`
- `OptionGroup`
- `OptionItem`
- `ReferenceSource`
- `ReferenceFile`
- `ItemWritingReference`
- `AIProviderSetting`
- `AIModel`
- `ImportJob`
- `DatabaseBackup`
- `AIDatabaseOperation`

輔助模組：

- `questions/importer.py`：Excel/CSV 匯入
- `questions/ai_client.py`：OpenAI-compatible API 呼叫
- `questions/ai_db_actions.py`：AI JSON actions 套用到資料庫
- `questions/backup.py`：SQLite 備份與還原
- `questions/question_context.py`：建立 AI 可讀取的題庫與命題參考上下文
- `questions/data_portability.py`：內容資料包匯入/匯出

## 9. 測試建議

### 基礎頁面

- 首頁可公開瀏覽。
- 未登入不能進 `/dashboard/`、`/questions/`、`/settings/`。
- staff 帳號登入後可進工作台。

### 題目流程

- 新增題目時四個下拉選單有預設值。
- 貼上含 A-D 選項的題幹後可正確拆解。
- 標記已完成後不能再儲存修改。
- 題庫列表顯示編號與完成狀態。

### AI 設定

- OpenAI 可載入模型。
- OpenAI `gpt-5` 可送出，不應出現 temperature unsupported。
- Ollama 可載入模型並測試。
- 切換 API 來源後，工作台模型下拉只顯示該來源模型。

### AI 工作台

- 送出後顯示 AI 思考中。
- 送出按鈕 disabled。
- 中斷按鈕可取消前端等待。
- 勾選題庫讀取後，AI 能列出題幹。
- 勾選允許修改後，JSON actions 可新增或更新題目。
- 已完成題目應被略過。

### 備份與匯入匯出

- 手動備份可建立檔案。
- 匯入資料包前會自動備份。
- 匯出資料包可下載 JSON。
- 新環境 migrate 後可匯入資料包。

## 10. 已知限制與後續工作

- API Key 目前明文儲存在 SQLite，正式環境需加密。
- AI 修改資料庫目前直接執行 JSON actions，建議下一版加入「預覽與確認」流程。
- 匯入 Excel/CSV 尚未提供逐列錯誤詳情。
- 參考檔案目前只保存檔案路徑，尚未抽取全文或做 RAG。
- AI 中斷目前主要是取消前端等待；後端同步 request 仍可能已送出。
- Bootstrap UI 仍是 MVP，可再改善表格分頁、批次操作與資料量大時的效能。
- SQLite 適合開發測試；正式多人使用建議改 PostgreSQL。

