import { useState, useEffect, useCallback } from "react";
import { API, authFetch } from "@/lib/api";

export interface SocialAccount {
  id: number;
  platform: string; // instagram, facebook, threads, youtube, x, tiktok
  username: string;
  profile_url?: string;
  follower_count: number;
  following_count: number;
  post_count: number;
  connected_at: string;
  last_synced?: string;
  status: "connected" | "expired" | "error";
}

export interface SocialAccountsState {
  accounts: SocialAccount[];
  connected: Record<string, SocialAccount>; // platform -> account
  loading: boolean;
  error: string | null;
}

export interface AuthWindow {
  postMessage: (message: any, origin: string) => void;
  close: () => void;
  closed: boolean;
}

/**
 * Shared hook for managing social media account connections.
 * Handles OAuth flows, token refresh, and connection status.
 */
export function useSocialAccounts() {
  const [state, setState] = useState<SocialAccountsState>({
    accounts: [],
    connected: {},
    loading: true,
    error: null,
  });

  // Load social accounts from API
  const loadAccounts = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const response = await authFetch(`${API}/api/social/accounts`);
      if (response.ok) {
        const accounts: SocialAccount[] = await response.json();
        const connected = accounts.reduce((acc, account) => {
          if (account.status === "connected") {
            acc[account.platform] = account;
          }
          return acc;
        }, {} as Record<string, SocialAccount>);
        
        setState({
          accounts,
          connected,
          loading: false,
          error: null,
        });
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error("Failed to load social accounts:", error);
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : "Failed to load accounts",
      }));
    }
  }, []);

  // Check if a platform is connected
  const isConnected = useCallback((platform: string): boolean => {
    return !!state.connected[platform];
  }, [state.connected]);

  // Get account for a platform
  const getAccount = useCallback((platform: string): SocialAccount | null => {
    return state.connected[platform] || null;
  }, [state.connected]);

  // Start OAuth flow for a platform
  const connect = useCallback(async (platform: string): Promise<boolean> => {
    try {
      // Get OAuth URL from backend
      const response = await authFetch(`${API}/api/social/oauth/meta/authorize?platform=${platform}`);
      if (!response.ok) {
        throw new Error(`Failed to get OAuth URL: ${response.status}`);
      }
      
      const { auth_url } = await response.json();
      
      // Open popup window for OAuth
      const authWindow = window.open(
        auth_url,
        'oauth',
        'width=600,height=700,scrollbars=yes,resizable=yes'
      ) as AuthWindow;

      return new Promise((resolve) => {
        // Listen for OAuth completion message
        const handleMessage = (event: MessageEvent) => {
          if (event.origin !== window.location.origin) return;
          
          if (event.data.type === 'oauth_complete') {
            window.removeEventListener('message', handleMessage);
            authWindow.close();
            
            if (event.data.status === 'connected') {
              loadAccounts(); // Refresh accounts
              resolve(true);
            } else {
              console.error('OAuth failed:', event.data.error);
              resolve(false);
            }
          }
        };

        window.addEventListener('message', handleMessage);

        // Handle popup closed without completion
        const checkClosed = setInterval(() => {
          if (authWindow.closed) {
            clearInterval(checkClosed);
            window.removeEventListener('message', handleMessage);
            resolve(false);
          }
        }, 1000);
      });
    } catch (error) {
      console.error(`Failed to connect ${platform}:`, error);
      return false;
    }
  }, [loadAccounts]);

  // Disconnect a platform
  const disconnect = useCallback(async (platform: string): Promise<boolean> => {
    const account = state.connected[platform];
    if (!account) return true;

    try {
      const response = await authFetch(`${API}/api/social/accounts/${account.id}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        loadAccounts(); // Refresh accounts
        return true;
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error(`Failed to disconnect ${platform}:`, error);
      return false;
    }
  }, [state.connected, loadAccounts]);

  // Refresh token for a platform
  const refreshToken = useCallback(async (platform: string): Promise<boolean> => {
    const account = state.connected[platform];
    if (!account) return false;

    try {
      const response = await authFetch(`${API}/api/social/oauth/refresh/${account.id}`, {
        method: 'POST',
      });
      
      if (response.ok) {
        loadAccounts(); // Refresh accounts
        return true;
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error(`Failed to refresh token for ${platform}:`, error);
      return false;
    }
  }, [state.connected, loadAccounts]);

  // Auto-refresh expired tokens
  useEffect(() => {
    const expiredAccounts = state.accounts.filter(account => account.status === "expired");
    
    expiredAccounts.forEach(account => {
      console.log(`Auto-refreshing expired token for ${account.platform}`);
      refreshToken(account.platform);
    });
  }, [state.accounts, refreshToken]);

  // Load accounts on mount
  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  return {
    // State
    accounts: state.accounts,
    connected: state.connected,
    loading: state.loading,
    error: state.error,
    
    // Actions
    loadAccounts,
    isConnected,
    getAccount,
    connect,
    disconnect,
    refreshToken,
  };
}

// Platform configurations for UI
export const PLATFORM_CONFIGS = {
  instagram: {
    name: "Instagram",
    color: "#E4405F",
    bgColor: "bg-pink-500/10",
    textColor: "text-pink-400",
    borderColor: "border-pink-500/30",
  },
  facebook: {
    name: "Facebook", 
    color: "#1877F2",
    bgColor: "bg-blue-500/10",
    textColor: "text-blue-400",
    borderColor: "border-blue-500/30",
  },
  threads: {
    name: "Threads",
    color: "#000000",
    bgColor: "bg-gray-500/10", 
    textColor: "text-gray-400",
    borderColor: "border-gray-500/30",
  },
  x: {
    name: "X",
    color: "#000000",
    bgColor: "bg-gray-500/10",
    textColor: "text-gray-400", 
    borderColor: "border-gray-500/30",
  },
  youtube: {
    name: "YouTube",
    color: "#FF0000",
    bgColor: "bg-red-500/10",
    textColor: "text-red-400",
    borderColor: "border-red-500/30",
  },
  tiktok: {
    name: "TikTok",
    color: "#000000", 
    bgColor: "bg-gray-500/10",
    textColor: "text-gray-400",
    borderColor: "border-gray-500/30",
  },
} as const;

export type Platform = keyof typeof PLATFORM_CONFIGS;