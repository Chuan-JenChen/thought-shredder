export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { thought } = req.body || {};
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    console.error("錯誤：找不到 GEMINI_API_KEY 環境變數");
    return res.status(200).json({ reply: "沒事的，深呼吸，我們把它碎掉就好。" });
  }

  const systemPrompt = `妳現在是一位充滿同理心、說話直接且溫暖的台灣女性閨蜜。
使用者會告訴妳一件煩心事。妳的任務是：
1. 站在她那邊，用 1 到 2 句話簡單安撫或跟著吐槽。
2. 語氣要像真人（可以使用「真的」、「辛苦了」、「誇張欸」等台灣日常慣用語）。
3. 字數絕對不可超過 40 字，簡短有力。`;

  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: `${systemPrompt}\n\n煩心事：${thought}` }] }]
      })
    });

    const data = await response.json();

    if (!response.ok || data.error) {
      console.error("Gemini API 回傳錯誤狀態:", response.status, JSON.stringify(data.error || data));
      return res.status(200).json({ reply: "沒事的，深呼吸，我們把它碎掉就好。" });
    }

    const replyText = data?.candidates?.[0]?.content?.parts?.[0]?.text;

    if (!replyText) {
      console.error("Gemini API 未包含文字內容:", JSON.stringify(data));
      return res.status(200).json({ reply: "沒事的，深呼吸，我們把它碎掉就好。" });
    }

    return res.status(200).json({ reply: replyText });
  } catch (error) {
    console.error("伺服器端錯誤:", error);
    return res.status(200).json({ reply: "沒事的，深呼吸，我們把它碎掉就好。" });
  }
}