export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const { thought } = req.body;
  const apiKey = process.env.GEMINI_API_KEY;

  const systemPrompt = `妳現在是一位充滿同理心、說話直接且溫暖的台灣女性閨蜜。
使用者會告訴妳一件煩心事。妳的任務是：
1. 站在她那邊，用 1 到 2 句話簡單安撫或跟著吐槽。
2. 語氣要像真人（可以使用「真的」、「辛苦了」、「誇張欸」等台灣日常慣用語）。
3. 字數絕對不可超過 40 字，簡短有力。`;

  try {
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key=${apiKey}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: `${systemPrompt}\n\n煩心事：${thought}` }] }]
      })
    });

    if (!response.ok) {
      return res.status(200).send("沒事的，深呼吸，我們把它碎掉就好。");
    }

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const json = JSON.parse(line.substring(6));
            const text = json?.candidates?.[0]?.content?.parts?.[0]?.text;
            if (text) {
              res.write(text);
            }
          } catch (e) {
            // 忽略未完成的 JSON 片段
          }
        }
      }
    }
    res.end();
  } catch (error) {
    res.status(200).send("沒事的，深呼吸，我們把它碎掉就好。");
  }
}