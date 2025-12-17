// 설정 정보 API (인증 필요)
import { getStore } from "@netlify/blobs";

export default async (request, context) => {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Content-Type": "application/json"
  };

  // CORS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers });
  }

  // 인증 확인
  const authHeader = request.headers.get("Authorization");
  const adminKey = Netlify.env.get("ADMIN_KEY");

  if (!authHeader || authHeader !== `Bearer ${adminKey}`) {
    return new Response(JSON.stringify({
      error: "Unauthorized"
    }), { status: 401, headers });
  }

  try {
    const store = getStore("visitors");

    // 최근 7일간 방문자 통계
    const stats = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      const count = await store.get(`daily:${dateStr}`, { type: "json" }) || 0;
      stats.push({ date: dateStr, visitors: count });
    }

    const totalCount = await store.get("total", { type: "json" }) || 0;

    return new Response(JSON.stringify({
      geminiModel: "gemini-2.5-flash",
      stats: {
        total: totalCount,
        daily: stats
      },
      lastUpdated: new Date().toISOString()
    }), { status: 200, headers });

  } catch (error) {
    return new Response(JSON.stringify({
      geminiModel: "gemini-2.5-flash",
      stats: {
        total: 0,
        daily: []
      },
      error: "Stats unavailable",
      lastUpdated: new Date().toISOString()
    }), { status: 200, headers });
  }
};

export const config = {
  path: "/api/config"
};
