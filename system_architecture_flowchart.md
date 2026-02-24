# AI 釣魚信件偵測系統 - 系統運作流程圖

這份流程圖展示了整個釣魚信件分析系統在終端使用者（或紅隊演練）操作時，資料是如何在系統各個模組之間流動與處理的。

```mermaid
flowchart TD
    %% 定義節點樣式
    classDef input fill:#e1bee7,stroke:#4a148c,stroke-width:2px;
    classDef ui fill:#bbdefb,stroke:#0d47a1,stroke-width:2px;
    classDef process fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px;
    classDef ai fill:#fff9c4,stroke:#f57f17,stroke-width:2px;
    classDef output fill:#ffccbc,stroke:#bf360c,stroke-width:2px;

    %% 系統邊界：使用者層
    subgraph UserLayer [使用者操作層]
        U1([使用者/紅隊測試員]):::input
        U2[/"可疑釣魚信件文本 payload"/]:::input
        U1 -->|輸入包含混淆/編碼的文本| U2
    end

    %% 系統邊界：前端應用層
    subgraph Frontend [前端介面層 Streamlit - app.py]
        F1{接收輸入字串}:::ui
        F3[解碼過程可視化展示]:::ui
        F2[結果顯示區]:::ui
    end
    U2 -->|點擊分析按鈕| F1

    %% 系統邊界：資料處理層
    subgraph DataProcessing [資料前處理層 decoder.py]
        D1[基礎清洗<br/>移除基礎 HTML 標籤與多餘空白]:::process
        D2[核心解碼器<br/>偵測並執行 Base64 與 URL Decoding]:::process
        D3[特徵提取<br/>將可疑 IP/惡意網域替換為特定 Token]:::process
        
        D1 --> D2 --> D3
    end
    F1 -->|Raw Text| D1
    D2 -.->|回傳解碼前後比對資料| F3

    %% 系統邊界：AI 推論層
    subgraph InferenceLayer [AI 推論層 inference.py]
        I1[接收乾淨/標準化明文]:::ai
        I2(("語言模型<br/>Hugging Face Pipeline<br/>微調後模型")):::ai
        I3[分析上下文與惡意特徵]:::ai
        I4[產出預測機率值與分類標籤]:::ai
        
        I1 --> I2 --> I3 --> I4
    end
    D3 -->|Cleaned Text| I1

    %% 系統邊界：輸出呈現
    I4 -->|Return Probability & Label| F2
    F3 -.-> F2
```

### 系統運作步驟說明：
1. **輸入 (Input)**：使用者（或攻擊者）將一封包含各種混淆手法（例如 URL 編碼、Base64 隱藏惡意網址）的電子郵件貼入網頁介面。
2. **前處理與解碼 (Decoding & Cleaning)**：系統將輸入交給 `decoder.py`。解碼器會自動把 HTML 標籤拔除、把 Base64 或被編碼的 URL 還原成人類可讀的明文，並給予特殊標記（Token）。
3. **推論分析 (Inference)**：處理乾淨且特徵明顯的文字，接著被送入 `inference.py`。裡面的 AI 語言模型會讀取整段文字的上下文，判斷這是否為釣魚信件。
4. **結果呈現 (Output)**：最後，Streamlit 前端將會向使用者展示兩個核心資訊：
    - AI 給出的**分類結果**與**信心機率**。
    - 系統在背景做了解碼的**過程對比**（讓使用者知道背後藏了什麼惡意網址）。
