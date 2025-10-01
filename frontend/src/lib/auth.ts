/**
 * Authentication utilities for client-side
 */

export interface User {
  user_id: string
  name: string
  role: string
}

export const getStoredUser = (): User | null => {
  if (typeof window === 'undefined') return null
  
  try {
    const userStr = localStorage.getItem('user')
    return userStr ? JSON.parse(userStr) : null
  } catch {
    return null
  }
}

export const setStoredUser = (user: User): void => {
  if (typeof window === 'undefined') return
  localStorage.setItem('user', JSON.stringify(user))
}

export const removeStoredUser = (): void => {
  if (typeof window === 'undefined') return
  localStorage.removeItem('user')
}

export const isAuthenticated = (): boolean => {
  return getStoredUser() !== null
}

export const logout = async (): Promise<void> => {
  try {
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
    })
  } catch (error) {
    console.error('Logout error:', error)
  } finally {
    removeStoredUser()
    window.location.href = '/login'
  }
}

export const checkAuth = async (): Promise<User | null> => {
  try {
    const response = await fetch('/api/auth/me', {
      credentials: 'include',
    })
    
    if (response.ok) {
      const user = await response.json()
      setStoredUser(user)
      return user
    } else {
      removeStoredUser()
      return null
    }
  } catch (error) {
    console.error('Auth check error:', error)
    removeStoredUser()
    return null
  }
}
