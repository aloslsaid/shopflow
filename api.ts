
const API = (
  (import.meta as any).env?.VITE_API || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

async function request(
  path: string,
  method: string,
  token?: string,
  body?: unknown
) {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;

  try {
    response = await fetch(`${API}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error(
      `تعذر الاتصال بالباك إند (${API}). تحقق من تشغيل FastAPI وإعدادات CORS.`
    );
  }

  const raw = await response.text();

  let data: any = {};

  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = { detail: raw || response.statusText };
  }

  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail
          .map((item: any) => item.msg || JSON.stringify(item))
          .join("، ")
      : data.detail || response.statusText || `HTTP ${response.status}`;

    throw new Error(String(detail));
  }

  return data;
}

export function api(
  path: string,
  token: string,
  method = "GET",
  body?: unknown
) {
  return request(path, method, token, body);
}

export async function login(
  email: string,
  password: string
): Promise<string> {
  const data = await request("/auth/login", "POST", undefined, {
    email,
    password,
  });

  if (!data?.token) {
    throw new Error("الخادم لم يرجع رمز تسجيل الدخول.");
  }

  return data.token;
}
