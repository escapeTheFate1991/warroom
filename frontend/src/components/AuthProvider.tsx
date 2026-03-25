"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { User, getStoredUser, getCurrentUser, clearAuthData, isAuthenticated } from "@/lib/auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const initAuth = async () => {
      // Check if we're authenticated
      if (!isAuthenticated()) {
        setLoading(false);
        router.push("/login");
        return;
      }

      // Get stored user data first
      const storedUser = getStoredUser();
      if (storedUser) {
        setUser(storedUser);
      }

      // Verify auth with server and get fresh user data
      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } catch (error) {
        console.error("Auth verification failed:", error);
        clearAuthData();
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, [router]);

  const login = (userData: User) => {
    setUser(userData);
  };

  const logout = () => {
    clearAuthData();
    setUser(null);
    router.push("/login");
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
  };

  // Show structure while checking auth (no blocking spinner)
  if (loading) {
    return (
      <div className="min-h-screen bg-warroom-bg flex">
        <div className="w-60 bg-warroom-surface border-r border-warroom-border animate-pulse">
          <div className="p-4 space-y-3">
            <div className="h-6 bg-warroom-border rounded w-3/4" />
            <div className="h-4 bg-warroom-border rounded w-1/2" />
            <div className="h-4 bg-warroom-border rounded w-2/3" />
          </div>
        </div>
        <div className="flex-1 flex flex-col">
          <div className="h-14 bg-warroom-surface border-b border-warroom-border animate-pulse">
            <div className="h-full flex items-center justify-between px-6">
              <div className="h-6 bg-warroom-border rounded w-32" />
              <div className="h-8 w-8 bg-warroom-border rounded-full" />
            </div>
          </div>
          <div className="flex-1 p-6">
            <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4 animate-pulse">
              <div className="h-6 bg-warroom-border rounded w-1/3 mb-3" />
              <div className="space-y-2">
                <div className="h-4 bg-warroom-border rounded w-full" />
                <div className="h-4 bg-warroom-border rounded w-3/4" />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // If not authenticated, don't render children (router will handle redirect)
  if (!user) {
    return null;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}