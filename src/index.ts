import puppeteer from "@cloudflare/puppeteer";

const DOMAINS = {
  MAIN: "doujindesu.tv",
  IMG: "desu.photos"
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const isAsset = url.pathname.match(/\.(webp|jpg|jpeg|png|gif|svg|mp4|css|js)$/i);
    const targetHost = isAsset ? DOMAINS.IMG : DOMAINS.MAIN;
    const targetUrl = new URL(url.pathname + url.search, `https://${targetHost}`);

    // --- LOGIKA 1: ASSET LANSUNG FETCH (Efisien) ---
    if (isAsset) {
      const assetHeaders = new Headers(request.headers);
      assetHeaders.set("Host", targetHost);
      assetHeaders.set("Referer", `https://${DOMAINS.MAIN}/`);
      
      const response = await fetch(targetUrl.toString(), {
        method: request.method,
        headers: assetHeaders,
        redirect: "manual"
      });
      
      // Berikan header CORS agar asset bisa dimuat di browser user
      const newHeaders = new Headers(response.headers);
      newHeaders.set("Access-Control-Allow-Origin", "*");
      return new Response(response.body, { ...response, headers: newHeaders });
    }

    // --- LOGIKA 2: HTML MENGGUNAKAN PUPPETEER (Bypass) ---
    let browser;
    try {
      // Launch browser menggunakan binding (env.MYBROWSER)
      browser = await puppeteer.launch(env.MYBROWSER);
      const page = await browser.newPage();

      // Set User Agent agar tidak terlihat seperti headless default
      await page.setUserAgent(request.headers.get("user-agent") || "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36");

      // Buka halaman target
      await page.goto(targetUrl.toString(), { 
        waitUntil: "networkidle2", // Tunggu sampai tidak ada request network lagi
        timeout: 30000 
      });

      // Ambil konten HTML setelah diproses browser (sudah lolos challenge)
      let html = await page.content();

      // --- LOGIKA 3: SELECTIVE REWRITE (Manual Replacement) ---
      // Karena Cheerio tidak built-in di Worker, kita gunakan Regex global yang aman
      // Ini mengganti https://domain.tv/path menjadi /path agar tetap lewat proxy
      for (const domain of Object.values(DOMAINS)) {
        const regex = new RegExp(`https://${domain}`, 'g');
        html = html.replace(regex, "");
      }

      await browser.close();

      return new Response(html, {
        headers: { 
          "Content-Type": "text/html;charset=UTF-8",
          "Access-Control-Allow-Origin": "*" 
        }
      });

    } catch (err) {
      if (browser) await browser.close();
      return new Response(`Puppeteer Bridge Error: ${err.message}`, { status: 502 });
    }
  }
};
