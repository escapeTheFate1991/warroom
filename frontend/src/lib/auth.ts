/**
 * Authentication utilities for War Room
 * Handles JWT token storage, validation, and API calls
 */

export interface UserOrg {
  id: number;
  name: string;
  slug: string;
}

export interface UserRole {
  id: number;
  name: string;
  permissions: string[];
}

export interface User {
  id: number;
  name: string;
  email: string;
  email_verified: boolean;
  is_superadmin: boolean;
  org?: UserOrg | null;
  role?: UserRole | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

import { API as API_BASE } from "@/lib/api";
const TOKEN_KEY = 'warroom_token';
const USER_KEY = 'warroom_user';

/**
 * Store auth data in localStorage
 */
export function storeAuthData(authResponse: AuthResponse) {
  if (typeof window === 'undefined') return;
  
  localStorage.setItem(TOKEN_KEY, authResponse.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(authResponse.user));
}

/**
 * Get stored auth token
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Get stored user data
 */
export function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  
  const userStr = localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

/**
 * Clear auth data from localStorage
 */
export function clearAuthData() {
  if (typeof window === 'undefined') return;
  
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return getAuthToken() !== null;
}

/**
 * Get authorization headers for API calls
 */
export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Make authenticated API call
 */
export async function apiCall(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
    ...options.headers,
  };

  return fetch(url, { ...options, headers });
}

/**
 * Login user
 */
export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || `Login failed (${response.status})`);
  }

  const authResponse: AuthResponse = await response.json();
  storeAuthData(authResponse);
  return authResponse;
}

/**
 * Sign up new user
 */
export async function signup(name: string, email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || `Signup failed (${response.status})`);
  }

  const authResponse: AuthResponse = await response.json();
  storeAuthData(authResponse);
  return authResponse;
}

/**
 * Logout user
 */
export async function logout(): Promise<void> {
  try {
    await apiCall('/api/auth/logout', { method: 'POST' });
  } catch {
    // Continue with logout even if API call fails
  }
  
  clearAuthData();
  
  // Redirect to login page
  if (typeof window !== 'undefined') {
    window.location.href = '/login';
  }
}

/**
 * Get current user from API
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiCall('/api/auth/me');
  
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthData();
      throw new Error('Authentication expired');
    }
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || `Failed to get user data (${response.status})`);
  }
  
  const user: User | null = await response.json().catch(() => null);
  if (!user) {
    throw new Error(`Failed to get user data (${response.status})`);
  }
  // Update stored user data
  if (typeof window !== 'undefined') {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  
  return user;
}

/**
 * Attempt to refresh the JWT using the current token.
 * Calls POST /api/auth/refresh with the existing JWT in the Authorization header.
 * On success, stores the new token and returns it.
 * On failure, returns null (caller should clear auth and redirect).
 */
export async function refreshToken(): Promise<string | null> {
  const token = getAuthToken();
  if (!token) return null;

  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) return null;

    const data: { access_token: string; token_type: string } = await response.json();
    if (!data.access_token) return null;

    // Store the new token
    if (typeof window !== 'undefined') {
      localStorage.setItem('warroom_token', data.access_token);
    }
    return data.access_token;
  } catch {
    return null;
  }
}

/**
 * Redirect to login if not authenticated
 */
export function requireAuth(): void {
  if (typeof window === 'undefined') return;
  
  if (!isAuthenticated()) {
    window.location.href = '/login';
  }
}