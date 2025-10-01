import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Check if user is trying to access protected routes
  const isProtectedRoute = request.nextUrl.pathname.startsWith('/') && 
                          request.nextUrl.pathname !== '/login'
  
  // Check for auth token in cookies
  const authToken = request.cookies.get('auth_token')
  
  // If accessing protected route without auth, redirect to login
  if (isProtectedRoute && !authToken) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  
  // If accessing login page with auth, redirect to dashboard
  if (request.nextUrl.pathname === '/login' && authToken) {
    return NextResponse.redirect(new URL('/', request.url))
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
