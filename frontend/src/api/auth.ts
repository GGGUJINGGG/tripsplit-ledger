import type {
  AuthToken,
  User,
  UserLogin,
  UserRegistration,
} from "../types";
import { apiRequest } from "./client";
import {
  clearAccessToken,
  setAccessToken,
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

  setAccessToken(token.access_token);
  return token;
}

export function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/auth/me");
}

export function logoutUser(): void {
  clearAccessToken();
}