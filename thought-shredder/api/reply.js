export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { thought, cards } = req.body || {};
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    return res.status(500).json({ error: "伺服器環境變數缺少 GEMINI_API_KEY" });
  }

  // 易經核心轉化卦庫
  const ichingGuaList = [
    { name: "地水師卦", symbol: "䷆", essence: "處變不驚、整頓自律、以退為進" },
    { name: "水火既濟卦", symbol: "䷾", essence: "事態已定、守成為上、防微杜漸" },
    { name: "地火明夷卦", symbol: "䷣", essence: "韜光養晦、收斂鋒芒、暗中積蓄" },
    { name: "雷天大壯卦", symbol: "䷡", essence: "聲勢浩大、切忌剛愎、克制衝動" },
    { name: "風雷益卦", symbol: "䷩", essence: "借力使力、主動突破、利益共好" },
    { name: "澤火革卦", symbol: "䷰", essence: "果斷變革、打破舊習、破舊立新" },
    { name: "天風姤卦", symbol: "䷫", essence: "邂逅突發、防範暗箭、謹慎觀察" },
    { name: "水雷屯卦", symbol: "䷂", essence: "萬事起頭、厚積薄發、切勿急躁" }
  ];

  const randomGua = ichingGuaList[Math.floor(Math.random() * ichingGuaList.length)];
  const card1 = cards?.[0] || { name: "力量", keyword: "以柔克剛" };
  const card2 = cards?.[1] || { name: "惡魔", keyword: "慾望束縛" };
  const card3 = cards?.[2] || { name: "愚者", keyword: "純粹出發" };

  const prompt = `妳是一位融合「西方現代心理塔羅」與「東方易經哲理」的毒舌又溫暖的當代諮商師。
使用者的煩心事或情緒是：「${thought || "無特定文字，覺得身心俱疲、職場或生活卡住"}」。

使用者抽出的三張塔羅牌（過去、現在、未來）：
1. 過去根源：${card1.name}（能量：${card1.keyword}）
2. 現狀盲點：${card2.name}（能量：${card2.keyword}）
3. 未來轉機：${card3.name}（能量：${card3.keyword}）

推算出的易經卦象為：${randomGua.name} ${randomGua.symbol}（象徵：${randomGua.essence}）。

【嚴格指令】：
1. 禁止給任何模板化或罐頭空話！每一次生成必須【完全客製化】。
2. 塔羅診斷必須具體點出「${card1.name}」、「${card2.name}」與「${card3.name}」如何在她的心事中產生作用。
3. 【宜做】與【忌做】必須極度接地氣，緊扣她所描述的「${thought || "當前卡點"}」，給出具體生活行動指引。

請直接回傳純 JSON 字串（禁止使用 Markdown 程式碼區塊標記如 \`\`\`json，禁止任何開頭結尾額外文字）：
{
  "ichingName": "${randomGua.name} ${randomGua.symbol}",
  "ichingWisdom": "結合${randomGua.name}卦象與她的煩惱，給出一句直擊靈魂、讓她徹底轉念的造就金句",
  "tarotSummary": "用2-3句話串連 ${card1.name}、${card2.name}、${card3.name}，解析她從過去怎麼走到現在卡關，接下來該如何翻篇",
  "luckyAction": "一項今天或明天立即可執行的具體行動（必須貼合她的心事與卦象，禁止空泛）",
  "avoidAction": "一項今天千萬別踩雷的情緒衝動行為（必須貼合她的心事與卦象，禁止空泛）",
  "luckyVibe": "建議的專屬開運色調與一件轉變磁場的隨身小物或穿搭"
}`;

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=${apiKey}`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: {
          responseMimeType: "application/json",
          temperature: 0.9
        }
      })
    });

    const data = await response.json();

    if (!response.ok) {
      console.error("Gemini API 回傳錯誤碼:", response.status, data);
      return res.status(500).json({ 
        error: "Gemini API 請求失敗", 
        details: data?.error?.message || "請確認 Vercel 後台 GEMINI_API_KEY 是否有效" 
      });
    }

    const rawText = data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!rawText) {
      throw new Error("Gemini 沒有回傳文字內容");
    }

    const cleanJson = rawText.replace(/```json/g, '').replace(/```/g, '').trim();
    const parsed = JSON.parse(cleanJson);
    return res.status(200).json(parsed);

  } catch (err) {
    console.error("處理出錯:", err);
    return res.status(500).json({ error: "AI 生成失敗", message: err.message });
  }
}