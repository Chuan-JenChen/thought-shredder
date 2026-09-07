export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { thought, card } = req.body || {};
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    console.error("錯誤：找不到 GEMINI_API_KEY 環境變數");
    return res.status(500).json({ error: "GEMINI_API_KEY is missing" });
  }

  const selectedCard = card || { name: "愚者 (The Fool)", keyword: "重新歸零、勇敢出發、純粹直覺" };

  const prompt = `妳是一位融合「現代心理諮商」與「直覺塔羅」的溫暖心靈閨蜜。
使用者剛剛吐露了今天的心情或煩惱：「${thought || "無特別描述，只是覺得心裡沉甸甸的"}」。
使用者憑自己的直覺，親手抽出的指引牌卡是：「${selectedCard.name}」（核心能量象徵：${selectedCard.keyword}）。

請依據她的心情與她親手抽中的牌義，為她開立一張專屬的「心靈開運處方箋」。
請直接回傳嚴格的 JSON 格式（不要使用 Markdown 標記如 \`\`\`json，只要純 JSON 字串）：
{
  "cardName": "${selectedCard.name}",
  "insight": "1-2句話結合牌義精準同理她的當前狀態與心理盲點",
  "encouragement": "一句充滿力量、撫慰人心的造就勸勉金句",
  "luckyAction": "一件今天或明天適合做的微小轉運事情（例如：買杯熱奶茶放空、提早下班）",
  "avoidAction": "一件今天千萬別碰的情緒踩雷事（例如：在深夜反省自己哪裡不夠好）",
  "luckyOutfit": "建議的穿搭風格、幸運色或隨身小物（例如：穿淺藍或米白色系衣服，搭配小巧銀飾）"
}
字數簡練有力，語氣溫暖日常且有底氣，切忌生硬說教。`;

  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: {
          responseMimeType: "application/json"
        }
      })
    });

    const data = await response.json();

    if (!response.ok || data.error) {
      console.error("Gemini API Error:", data.error);
      return res.status(200).json({
        cardName: selectedCard.name,
        insight: "這件事消耗了妳太多心力，現在最需要的是停下來深呼吸。",
        encouragement: "這些破事不定義妳的價值，好好睡一覺，全世界都會重整。",
        luckyAction: "喝一杯溫水，早點鑽進被窩",
        avoidAction: "深夜反芻白天不開心的細節",
        luckyOutfit: "穿最柔軟舒適的棉質睡衣，以大地色系安撫神經"
      });
    }

    const textContent = data?.candidates?.[0]?.content?.parts?.[0]?.text;
    const parsed = JSON.parse(textContent);
    return res.status(200).json(parsed);

  } catch (error) {
    console.error("伺服器處理失敗:", error);
    return res.status(200).json({
      cardName: selectedCard.name,
      insight: "妳已經很努力在承擔了，先讓緊繃的肩膀放鬆下來吧。",
      encouragement: "放過自己，明天又是全新的一天。",
      luckyAction: "關掉手機螢幕閉目養神 10 分鐘",
      avoidAction: "把別人的情緒怪在自己身上",
      luckyOutfit: "穿戴溫柔米白色或燕麥色系"
    });
  }
}