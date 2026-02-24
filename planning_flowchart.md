# AI 釣魚信件系統開發計畫流程圖

以下是根據 `planning.md` 所整理的開發流程圖，分為三個階段並以角色進行顏色標示，展現任務之間的前後相依與資料流動：

```mermaid
graph TD
    classDef ai fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef data fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    classDef test fill:#fff3e0,stroke:#e65100,stroke-width:2px;

    subgraph week1 [第一週：MVP 最小可行性架構與基礎解碼]
        A1[Task 1.1<br>環境建置]:::ai
        A2[Task 1.2<br>實作開源推論模組]:::ai
        A3[Task 1.3<br>API 封裝]:::ai
        A1 --> A2 --> A3
        
        B1[Task 1.4<br>取得與預覽資料]:::data
        B2[Task 1.5<br>開發核心解碼器]:::data
        B3[Task 1.6<br>基礎清洗]:::data
        B1 --> B2 --> B3
        
        C1[Task 1.7<br>前端框架架設]:::test
        C2[Task 1.8<br>模組整合]:::test
        C3[Task 1.9<br>建構初始攻擊集]:::test
        C1 --> C2
        A3 --> C2
        B2 --> C2
        C3 --> C2
    end

    subgraph week2 [第二週：模型微調與特徵工程強化]
        B4[Task 2.4<br>大規模資料轉換]:::data
        B5[Task 2.5<br>進階特徵提取]:::data
        B3 --> B4 --> B5
        
        A4[Task 2.1<br>資料集切分]:::ai
        A5[Task 2.2<br>模型微調]:::ai
        A6[Task 2.3<br>效能評估]:::ai
        B5 --> A4 --> A5 --> A6
        
        C4[Task 2.6<br>替換推論引擎]:::test
        C5[Task 2.7<br>UI 體驗優化]:::test
        C2 --> C4
        A6 --> C4
        C4 --> C5
    end

    subgraph week3 [第三週：AI 紅隊演練與系統驗收]
        A7[Task 3.1<br>凍結模型]:::ai
        A6 -.-> A7
        
        B6[Task 3.3<br>建構變異攻擊載荷]:::data
        C6[Task 3.5<br>執行 AI 紅隊演練]:::test
        C5 --> C6
        B6 --> C6
        
        A8[Task 3.2<br>盲點分析與報告]:::ai
        C7[Task 3.6<br>漏洞記錄]:::test
        C6 --> A8
        C6 --> C7
        
        B7[Task 3.4<br>系統架構圖繪製]:::data
        C8[Task 3.7<br>專案總收尾]:::test
        A7 -.-> C8
        C7 --> C8
        B7 --> C8
        A8 --> C8
    end
```

### 🧑‍💻 角色圖例說明：
- 🟦 **藍色節點**：組員 A (AI 工程師) 任務
- 🟩 **綠色節點**：組員 B (資安 / 資料工程師) 任務
- 🟧 **橘色節點**：組員 C (系統整合與紅隊測試) 任務
