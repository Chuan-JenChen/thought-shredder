export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { thought } = req.body || {};
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    return res.status(500).json({ error: "GEMINI_API_KEY is missing" });
  }

  // 22 張經典大阿爾克那塔羅牌庫
  const tarotDeck = [
    { name: "愚者 (The Fool)", keyword: "重新歸零、勇敢出發、純粹直覺" },
    { name: "魔術師 (The Magician)", keyword: "創造力、主動出擊、資源整合" },
    { name: "女祭司 (The High Priestess)", keyword: "沉靜直覺、退一步觀察、以靜制動" },
    { name: "皇后 (The Empress)", keyword: "自我犒賞、豐盛滋養、無條件接納" },
    { name: "皇帝 (The Emperor)", keyword: "確立界線、掌控秩序、理性自律" },
    { name: "教皇 (The Hierophant)", keyword: "心靈指引、遵循規則、尋找共鳴" },
    { name: "戀人 (The Lovers)", keyword: "心之所向、順應和諧、真誠抉擇" },
    { name: "戰車 (The Chariot)", keyword: "堅定前進、克服波折、意志聚焦" },
    { name: "力量 (Strength)", keyword: "以柔克剛、溫柔堅定、自我包容" },
    { name: "隱士 (The Hermit)", keyword: "向內探尋、給自己留白、遠離喧囂" },
    { name: "命運之輪 (Wheel of Fortune)", keyword: "轉機已至、順應變化、不必抗拒" },
    { name: "正義 (Justice)", keyword: "客觀衡量、放下執念、回歸平衡" },
    { name: "倒吊人 (The Hanged Man)", keyword: "換位思考、甘於等待、以退為進" },
    { name: "死神 (Death)", keyword: "告別過去、徹底斷捨離、迎接新生" },
    { name: "節制 (Temperance)", keyword: "調和步調、情緒淨化、尋求平衡" },
    { name: "惡魔 (The Devil)", keyword: "看清束縛、擺脫內耗、拿回自主權" },
    { name: "高塔 (The Tower)", keyword: "打破舊認知、釋放壓力、重獲自由" },
    { name: "星星 (The Star)", keyword: "希望重現、撫平傷口、深層療癒" },
    { name: "月亮 (The Moon)", keyword: "擁抱不安、看清迷霧、順應情緒流動" },
    { name: "太陽 (The Sun)", keyword: "撥雲見日、重拾熱情、光明坦蕩" },
    { name: "審判 (Judgement)", keyword: "聽從內心召喚、釋懷自責、煥然一新" },
    { name: "世界 (The World)", keyword: "圓滿完結、階段達成、安心歇息" }
  ];

  // 隨機抽出一張牌
  const randomCard = tarotDeck[Math.floor(Math.random() * tarotDeck.length)];

  const prompt = `妳是一位融合「現代心理諮商」與「直覺塔羅」的溫暖心靈閨蜜。
使用者剛剛吐露了今天的心情或煩惱：「${thought || "無特別描述，只是覺得心裡沉甸甸的"}」。
今天宇宙為她抽出的牌卡是：「${randomCard.name}」（核心能量象徵：${randomCard.keyword}）。

請依據她的心情與這張牌的象徵意涵，為她開立一張量身打造的「心靈開運處方箋」。
請直接回傳嚴格的 JSON 格式（不要使用 Markdown 標記如 \`\`\`json，只要純 JSON 字串）：
{
  "cardName": "${randomCard.name}",
  "insight": "1-2句話結合牌義精準同理她的當前狀態與心理盲點",
  "encouragement": "一句充滿力量、撫慰人心的造就勸勉金句",
  "luckyAction": "一件今天或明天適合做的微小轉運事情（例如：提早20分鐘下班買杯熱奶茶放空）",
  "avoidAction": "一件今天千萬別碰的情緒踩雷事（例如：在深夜反省自己哪裡不夠好）",
  "luckyOutfit": "建議的穿搭風格、幸運色或隨身小物（例如：穿淺藍或米白色系衣服，搭配小巧銀飾幫助平靜）"
}
字數簡練有力，語氣溫暖日常且有底氣，切忌生硬說教。`;

  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=${apiKey}`, {
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
        cardName: randomCard.name,
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
    console.error("處理失敗:", error);
    return res.status(200).json({
      cardName: randomCard.name,
      insight: "妳已經很努力在承擔了，先讓緊繃的肩膀放鬆下來吧。",
      encouragement: "放過自己，明天又是全新的一天。",
      luckyAction: "關掉手機螢幕閉目養神 10 分鐘",
      avoidAction: "把別人的情緒怪在自己身上",
      luckyOutfit: "穿戴溫柔米白色或燕麥色系"
    });
  }
}