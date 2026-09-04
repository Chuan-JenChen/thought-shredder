export default async function handler(req, res) {
  // 檢查是否為 POST 請求
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { thought } = req.body;
  const apiKey = process.env.GEMINI_API_KEY;

  // 定義 AI 的人設與系統提示詞
  const systemPrompt = `妳現在是一位充滿同理心、說話直接且溫暖的台灣女性閨蜜。
使用者會告訴妳一件煩心事。妳的任務是：
1. 站在她那邊，用 1 到 2 句話簡單安撫或跟著吐槽。
2. 語氣要像真人（可以使用「真的」、「辛苦了」、「誇張欸」等台灣日常慣用語）。
3. 字數絕對不可超過 40 字，簡短有力。`;

  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: `${systemPrompt}\n\n煩心事：${thought}` }] }]
      })
    });

    const data = await response.json();
    const replyText = data.candidates[0].content.parts[0].text;
    
    res.status(200).json({ reply: replyText });
  } catch (error) {
    console.error(error);
    // 萬一網路或 API 出錯的備用安撫文字
    res.status(200).json({ reply: "沒事的，深呼吸，我們把它碎掉就好。" }); 
  }
}