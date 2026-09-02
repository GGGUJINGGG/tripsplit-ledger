import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearAccessToken, setAccessToken } from "../api/token";
import { AuthProvider, useAuth } from "./AuthContext";

vi.mock("../api/auth", () => ({
  getCurrentUser: vi.fn(),
  logoutUser: vi.fn(),
}));

import { getCurrentUser, logoutUser } from "../api/auth";

function AuthProbe() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <p>loading</p>;
  return <p>{user ? `logged in as ${user.display_name}` : "logged out"}</p>;
}

describe("AuthProvider", () => {
  afterEach(() => {
    clearAccessToken();
    vi.clearAllMocks();
  });

  it("finishes loading with no user when there is no stored token", async () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByText("logged out")).toBeInTheDocument());
    expect(getCurrentUser).not.toHaveBeenCalled();
  });

  it("loads the current user when a token is stored and valid", async () => {
    setAccessToken("valid-token");
    vi.mocked(getCurrentUser).mockResolvedValue({
      id: "u1",
      email: "alex@example.com",
      display_name: "Alex",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(screen.getByText("logged in as Alex")).toBeInTheDocument(),
    );
  });

  it("logs out when the stored token is rejected by the server", async () => {
    setAccessToken("expired-token");
    vi.mocked(getCurrentUser).mockRejectedValue(new Error("401 Unauthorized"));

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByText("logged out")).toBeInTheDocument());
    expect(logoutUser).toHaveBeenCalledTimes(1);
  });
});
