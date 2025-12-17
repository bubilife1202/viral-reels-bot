// 방문자 수 추적 함수 (Netlify Blobs 사용)
import { getStore } from "@netlify/blobs";

export default async (request, context) => {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json"
  };

  // CORS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers });
  }

  try {
    const store = getStore("visitors");
    const today = new Date().toISOString().split('T')[0];

    // 오늘 방문자 수 가져오기
    let todayCount = await store.get(`daily:${today}`, { type: "json" }) || 0;

    // 총 방문자 수 가져오기
    let totalCount = await store.get("total", { type: "json" }) || 0;

    if (request.method === "POST") {
      // 방문자 수 증가
      todayCount++;
      totalCount++;

      await store.setJSON(`daily:${today}`, todayCount);
      await store.setJSON("total", totalCount);
    }

    return new Response(JSON.stringify({
      today: todayCount,
      total: totalCount,
      date: today
    }), { status: 200, headers });

  } catch (error) {
    // Blobs가 없는 경우 (로컬 개발 등) 기본값 반환
    return new Response(JSON.stringify({
      today: 0,
      total: 0,
      date: new Date().toISOString().split('T')[0],
      error: "Visitor tracking unavailable"
    }), { status: 200, headers });
  }
};

export const config = {
  path: "/api/visitor"
};
