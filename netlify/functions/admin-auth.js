// Admin 인증 함수
export default async (request, context) => {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json"
  };

  // CORS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers });
  }

  if (request.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers
    });
  }

  try {
    const body = await request.json();
    const { key } = body;

    // 환경변수에서 Admin 키 가져오기
    const adminKey = Netlify.env.get("ADMIN_KEY");

    if (!adminKey) {
      return new Response(JSON.stringify({
        success: false,
        error: "Admin key not configured"
      }), { status: 500, headers });
    }

    if (key === adminKey) {
      return new Response(JSON.stringify({
        success: true,
        message: "Authentication successful"
      }), { status: 200, headers });
    } else {
      return new Response(JSON.stringify({
        success: false,
        error: "Invalid admin key"
      }), { status: 401, headers });
    }

  } catch (error) {
    return new Response(JSON.stringify({
      success: false,
      error: "Invalid request"
    }), { status: 400, headers });
  }
};

export const config = {
  path: "/api/admin-auth"
};
