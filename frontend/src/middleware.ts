import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const response = NextResponse.next();
  if (!request.cookies.get("NEXT_LOCALE")) {
    response.cookies.set("NEXT_LOCALE", "zh", { path: "/", sameSite: "lax" });
  }
  return response;
}

export const config = {
  matcher: [
    "/((?!api|_next|fonts|favicon.ico|.*\\..*).*)",
  ],
};
