import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  getCurrentUser,
  logoutUser,
} from "../api/auth";
import { getAccessToken } from "../api/token";
import type { User } from "../types";


interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  refreshUser: () => Promise<void>;
  logout: () => void;
}


const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
);


interface AuthProviderProps {
  children: ReactNode;
}


export function AuthProvider({
  children,
}: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  async function refreshUser(): Promise<void> {
    const currentUser = await getCurrentUser();
    setUser(currentUser);
  }

  function logout(): void {
    logoutUser();
    setUser(null);
  }

  useEffect(() => {
    if (!getAccessToken()) {
      setIsLoading(false);
      return;
    }

    refreshUser()
      .catch(() => {
        logout();
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        refreshUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error(
      "useAuth must be used inside AuthProvider",
    );
  }

  return context;
}