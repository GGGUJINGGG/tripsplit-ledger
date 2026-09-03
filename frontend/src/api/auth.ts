import type {
  AuthToken,
  User,
  UserLogin,
  UserRegistration,
} from "../types";
import { apiRequest } from "./client";
import {
  clearTokens,
  getRefreshToken,
  setTokens,
} from "./token";


export function registerUser(
  payload: UserRegistration,
): Promise<User> {
  return apiRequest<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function loginUser(
  payload: UserLogin,
): Promise<AuthToken> {
  const token = await apiRequest<AuthToken>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  setTokens(token.access_token, token.refresh_token);
  return token;
}

export function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/auth/me");
}

export function logoutUser(): void {
  const refreshToken = getRefreshToken();

  if (refreshToken) {
    // Best-effort: revoke the refresh token server-side so it can't be
    // replayed later. The user is logged out locally either way.
    apiRequest("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {
      // Ignore — the token will simply expire on its own.
    });
  }

  clearTokens();
}
