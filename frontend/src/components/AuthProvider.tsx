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

  // Show loading spinner while checking auth
  if (loading) {
    return (
      <div className="min-h-screen bg-warroom-bg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-warroom-accent border-t-transparent" />
      </div>
    );
  }

  // If not authenticated, don't render children (router will handle redirect)
  if (!user) {
    return null;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}