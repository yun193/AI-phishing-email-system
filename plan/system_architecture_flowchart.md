# AI 釣魚信件偵測系統 - 系統運作流程圖

這份流程圖展示了整個釣魚信件分析系統在終端使用者（或紅隊演練）操作時，資料是如何在系統各個模組之間流動與處理的。流程中的文字已優化，以清楚標示每個模組的具體處理細節。

```mermaid
flowchart TD
    %% 定義節點樣式
    classDef input fill:#e1bee7,stroke:#4a148c,stroke-width:2px,color:#000;
    classDef ui fill:#bbdefb,stroke:#0d47a1,stroke-width:2px,color:#000;
    classDef process fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px,color:#000;
    classDef ai fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000;
    classDef output fill:#ffccbc,stroke:#bf360c,stroke-width:2px,color:#000;

    %% 系統邊界：使用者層
    subgraph UserLayer [使用者操作層]
        U1(["使用者/紅隊測試員<br/>發起測試"]):::input
        U2[/"可疑釣魚信件文本 Payload<br/>(可能包含多層 Base64/URL 編碼與干擾詞)"/]:::input
    end
    U1 -->|輸入惡意混淆文本| U2

    %% 系統邊界：前端應用層
    subgraph Frontend [前端介面層 Streamlit - app.py]
        F1{"UI 介面接收輸入<br/>(檢查字元長度限制防 DoS)"}:::ui
        F3["解碼過程可視化展示區<br/>(並列顯示原始碼與還原後的安全明文)"]:::ui
        F2["最終判斷顯示區<br/>(顯示 Phishing/Safe 標籤與機率數值)"]:::ui
    end
    U2 -->|點擊分析按鈕| F1

    %% 系統邊界：資料處理層
    subgraph DataProcessing [資料前處理層 decoder.py]
        D1["步驟 1：基礎清洗<br/>移除 HTML 標籤、腳本代碼與多餘空白"]:::process
        D2["步驟 2：核心遞迴解碼<br/>深度偵測並解碼 Base64 與 URL<br/>直到字串無編碼特徵為止"]:::process
        D3["步驟 3：惡意特徵提取<br/>透過 Regex 將可疑 IP/超長網域<br/>強制替換為模型專屬 EVIL_URL Token"]:::process
        
        D1 --> D2 --> D3
    end
    F1 -->|遞交 Raw Text| D1
    D2 -.->|回傳每步解碼對比日誌| F3

    %% 系統邊界：AI 推論層
    subgraph InferenceLayer [AI 推論層 inference.py]
        I1["接收標準化明文<br/>(已過濾雜訊並包含重點標記 Token)"]:::ai
        I2(("核心 AI 語言模型<br/>Hugging Face Pipeline<br/>(微調後的 Transformer 模型)")):::ai
        I3["語義與特徵綜合分析<br/>評估文本上下文與被標記的惡意意圖"]:::ai
        I4["結合機率函數計算<br/>產出最終預測機率值與分類標籤"]:::ai
        
        I1 --> I2 --> I3 --> I4
    end
    D3 -->|遞交 Cleaned Text| I1

    %% 系統邊界：輸出呈現
    I4 -->|Return 機率 Probability 與標籤 Label| F2
    F3 -.->|同步呈現可視化介面| F2
```

### 系統運作步驟說明：
1. **輸入 (Input)**：使用者（或攻擊者）將一封包含各種混淆手法（例如 URL 編碼、Base64 隱藏惡意網址）的電子郵件貼入網頁介面，前端預先檢查字元限制防止 DoS 攻擊。
2. **前處理與解碼 (Decoding & Cleaning)**：系統將輸入交給 `decoder.py`。解碼器不僅會自動拔除 HTML 標籤，更透過「遞迴邏輯」持續探測並把 Base64 或 URL 編碼還原成明文。過程中，亦利用正則運算將可疑的惡意網址替換為專屬標籤 `[EVIL_URL]`。
3. **推論分析 (Inference)**：清理過後且特徵明顯的文字，接著被送入 `inference.py`。裡面的 AI 語言模型會讀取整段乾淨的文字與重點 Token 上下文，判斷隱含的釣魚意圖。
4. **結果呈現 (Output)**：最後，Streamlit 前端將會向使用者展示兩個核心資訊：
    - AI 所給出的**最終分類結果 (Phishing/Safe)** 與**信心機率**。
    - 系統在背景做解碼的**過程對比日誌**，包含每被還原一層的內容，讓使用者直接看穿編碼後的真實惡意 Payload。
