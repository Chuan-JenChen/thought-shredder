export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { thought, cards } = req.body || {};
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    return res.status(500).json({ error: "伺服器環境變數缺少 GEMINI_API_KEY" });
  }

  const card1 = cards?.[0] || { name: "力量", keyword: "以柔克剛" };
  const card2 = cards?.[1] || { name: "惡魔", keyword: "慾望束縛" };
  const card3 = cards?.[2] || { name: "愚者", keyword: "純粹出發" };

  const prompt = `妳是使用者最親近、護短到極點、講話超有梗、一針見血的「惡魔毒舌閨蜜」。
她剛剛在深夜跟妳倒苦水，打出這段真心話：「${thought || "覺得生活跟工作一團糟，整個人快被破事氣死"}」。

她剛剛在妳面前依序抽出的 3 張牌：
- 過去根源：${card1.name}（代表她過去到底受了什麼鳥氣/當了什麼爛好人）
- 現在盲點：${card2.name}（代表她現在卡在哪個自我內耗的死胡同）
- 未來轉機：${card3.name}（代表接下來她怎麼反殺翻盤）

【嚴格指令】：
1. 嚴禁任何八股老氣詞彙（如「卦象」、「宜」、「忌」、「氣場」），禁止罐頭模板！
2. 語氣要像深夜在居酒屋聽她抱怨後，妳拍桌子替她出氣的口氣，口語、辛辣、人間清醒、Threads/IG 當代幽默感。
3. 【vibeTitle 今日劇本】：請依據她剛才打的具體文字，現場幫她量身下一個超貼切、超有梗的 8-12 字局勢標題（例如：『已讀不回 · 爛人退散局』、『老娘不伺候 · 掀桌翻盤局』、『封鎖刪除 · 換批小鮮肉局』）。
4. 每一欄位都必須【極度具體地針對她打的內容開噴與指引】，禁止空洞廢話。

請直接回傳純 JSON 字串（禁止包含 Markdown 代碼標籤 \`\`\`json）：
{
  "vibeTitle": "針對她輸入的破事，由妳現場客製命名的局勢標題（例如：老娘不幹了 · 職場裝死大勝局）",
  "soulSlap": "一句罵醒她、讓她忍不住笑出來又覺得被狠狠挺到的毒舌護短金句",
  "sisterAnalysis": "結合 ${card1.name}、${card2.name}、${card3.name}，用講八卦的口吻跟她拆解：妳之前就是太好欺負了，現在卡在什麼盲點，後面這張牌教妳怎麼帥氣翻篇",
  "doThis": "今晚或明天立刻去幹的一件最解氣、最爽、讓對方吃鱉的具體小事",
  "dontDoThis": "今晚千萬不能做的掉價、自我感動、或替爛人擦屁股的蠢事",
  "outfitVibe": "建議的戰袍/妝容/氣場指南（例如：全黑墨鏡酷妹裝，讓討厭的人連看妳一眼都覺得自己不配）"
}`;

  // 設定模型優先順序清單：首選優先，遇到 High Demand 自動切換備選
  const candidateModels = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
  ];

  let lastError = null;

  for (const model of candidateModels) {
    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: prompt }] }],
          generationConfig: {
            responseMimeType: "application/json",
            temperature: 1.0
          }
        })
      });

      const data = await response.json();

      // 若遇到 High Demand 或非 200，記錄後自動嘗試下一個模型
      if (!response.ok) {
        console.warn(`[API] 模型 ${model} 請求受限 (${response.status})，切換備用模型...`, data?.error?.message);
        lastError = data?.error?.message || `HTTP ${response.status}`;
        continue;
      }

      const rawText = data?.candidates?.[0]?.content?.parts?.[0]?.text;
      if (!rawText) {
        lastError = "模型回傳空內容";
        continue;
      }

      const cleanJson = rawText.replace(/```json/g, '').replace(/```/g, '').trim();
      const parsed = JSON.parse(cleanJson);
      return res.status(200).json(parsed);

    } catch (err) {
      console.warn(`[API] 模型 ${model} 調用異常:`, err.message);
      lastError = err.message;
    }
  }

  // 若備選模型皆暫時堵塞，回傳乾淨錯誤
  return res.status(503).json({
    error: "AI 閨蜜連線壅塞",
    details: `目前 Google API 流量偏高 (${lastError})，請稍候再點擊重試！`
  });
}