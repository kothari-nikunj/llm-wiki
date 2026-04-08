import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { jwtVerify } from 'jose';

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!pathname.startsWith('/wiki')) return NextResponse.next();
  if (pathname === '/wiki/login') return NextResponse.next();
  if (pathname.startsWith('/api/')) return NextResponse.next();

  const token = request.cookies.get('wiki_auth')?.value;
  if (!token) {
    return NextResponse.redirect(
      new URL(`/wiki/login?redirect=${encodeURIComponent(pathname)}`, request.url)
    );
  }

  try {
    const secret = new TextEncoder().encode(process.env.JWT_SECRET);
    await jwtVerify(token, secret);
    return NextResponse.next();
  } catch {
    return NextResponse.redirect(
      new URL(`/wiki/login?redirect=${encodeURIComponent(pathname)}`, request.url)
    );
  }
}

export const config = {
  matcher: '/wiki/:path*',
};
