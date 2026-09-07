export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { thought, cards } = req.body || {};
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    return res.status(500).json({ error: "GEMINI_API_KEY is missing" });
  }

  const ichingGuaList = [
    { name: "地水師卦", symbol: "䷆", essence: "處變不驚、以退為進、紀律整頓" },
    { name: "水火既濟卦", symbol: "䷾", essence: "事態已定、守成為上、防微杜漸" },
    { name: "地火明夷卦", symbol: "䷣", essence: "韜光養晦、隱藏鋒芒、自保為先" },
    { name: "雷天大壯卦", symbol: "䷡", essence: "聲勢浩大、止住衝動、克制剛烈" },
    { name: "風雷益卦", symbol: "䷩", essence: "借力使力、主動突破、利益共好" },
    { name: "澤火革卦", symbol: "䷰", essence: "徹底變革、斷然割捨、破舊立新" },
    { name: "天風姤卦", symbol: "䷫", essence: "不期而遇、防範小人、冷靜觀察" },
    { name: "水雷屯卦", symbol: "䷂", essence: "萬事起頭難、積蓄力量、切勿躁進" }
  ];

  const randomGua = ichingGuaList[Math.floor(Math.random() * ichingGuaList.length)];
  const selectedCards = cards && cards.length === 3 ? cards : [
    { name: "愚者", keyword: "純粹出發" },
    { name: "節制", keyword: "調和情緒" },
    { name: "世界", keyword: "圓滿完結" }
  ];

  const prompt = `妳是一位融合「西方心理塔羅」與「東方易經哲學」的資深現代諮商師。
使用者剛剛吐露了內心的煩惱或遭遇：「${thought || "覺得生活與職場充滿無力感與內耗"}」。

使用者親手抽出的三張塔羅牌分別是：
1. 過去/根源：${selectedCards[0].name}（${selectedCards[0].keyword}）
2. 現狀/盲點：${selectedCards[1].name}（${selectedCards[1].keyword}）
3. 未來/轉機：${selectedCards[2].name}（${selectedCards[2].keyword}）

搭配推導出的易經卦象為：${randomGua.name} ${randomGua.symbol}（核心哲理：${randomGua.essence}）。

請依據使用者的煩心事，將這三張塔羅的脈絡與易經卦象深度揉合，產出一份專屬的「東西會診解惑處方」。
特別注意：【易經宜忌】絕對不要講生硬的古文玄學，必須【直接緊扣使用者剛才講的具體人事物】給出極為具體的操作指引！

請直接回傳嚴格的 JSON 格式（不要使用 Markdown 標記如 \`\`\`json，只要純 JSON 字串）：
{
  "ichingName": "${randomGua.name} ${randomGua.symbol}",
  "tarotSummary": "用2句話串連這3張塔羅牌，講出使用者過去卡點、現在內耗核心與即將迎來的轉機",
  "ichingWisdom": "將該卦象轉化為一句給使用者的造就勸勉",
  "luckyAction": "【極度貼近使用者情境的宜做事項】（例如：若抱怨主管，寫出『明天把所有工作交付紀錄備份到隨身碟，保持客套不多做辯解』）",
  "avoidAction": "【極度貼近使用者情境的忌做事項】（例如：若抱怨感情，寫出『深夜11點後不要回傳長篇文字訊息自證清白』）",
  "luckyVibe": "建議的幸運色調與一件轉換磁場的小物件/穿搭"
}`;

  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
        generationConfig: { responseMimeType: "application/json" }
      })
    });

    const data = await response.json();
    if (!response.ok || data.error) {
      console.error("Gemini API Error:", data.error);
      return res.status(200).json({
        ichingName: `${randomGua.name} ${randomGua.symbol}`,
        tarotSummary: "妳過去投入了太多心力，現在正處於能量耗竭的轉折期。別急，風向即將轉變。",
        ichingWisdom: "天道有常，不拿別人的混亂折磨自己的心智。",
        luckyAction: "關閉工作群組通知，提早下班洗個熱水澡",
        avoidAction: "在情緒上頭時正面辯解或發社群限動",
        luckyVibe: "淺灰或米白棉質穿搭，搭配溫暖木質香調"
      });
    }

    const textContent = data?.candidates?.[0]?.content?.parts?.[0]?.text;
    return res.status(200).json(JSON.parse(textContent));

  } catch (error) {
    console.error("伺服器處理失敗:", error);
    return res.status(200).json({
      ichingName: `${randomGua.name} ${randomGua.symbol}`,
      tarotSummary: "三張牌顯示妳在迷局中承擔了過多責任，當前的卡頓只是暫時的沉澱。",
      ichingWisdom: "退一步並非示弱，而是讓能量重新歸位。",
      luckyAction: "列出今天最煩的一件事，然後把它從待辦事項劃掉",
      avoidAction: "過度揣摩身邊人的語氣與臉色",
      luckyVibe: "深藍或燕麥色系，佩戴微小金屬配件穩住氣場"
    });
  }
}