import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../auth/AuthContext";
import ProtectedRoute from "../auth/ProtectedRoute";
import { clearAccessToken } from "../api/token";
import LoginPage from "./LoginPage";

vi.mock("../api/auth", () => ({
  loginUser: vi.fn(),
  getCurrentUser: vi.fn(),
  logoutUser: vi.fn(),
}));

import { getCurrentUser, loginUser } from "../api/auth";

describe("Login flow", () => {
  afterEach(() => {
    clearAccessToken();
    vi.clearAllMocks();
  });

  it("logs the user in and lands on the page they were trying to reach", async () => {
    const user = userEvent.setup();

    vi.mocked(loginUser).mockResolvedValue({
      access_token: "new-token",
      token_type: "bearer",
    });
    vi.mocked(getCurrentUser).mockResolvedValue({
      id: "u1",
      email: "alex@example.com",
      display_name: "Alex",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    const router = createMemoryRouter(
      [
        { path: "/login", element: <LoginPage /> },
        {
          element: <ProtectedRoute />,
          children: [{ path: "/", element: <p>Trip Ledger</p> }],
        },
      ],
      { initialEntries: ["/"] },
    );

    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    // Unauthenticated visit to "/" redirects to the login page.
    await waitFor(() => expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument());

    await user.type(screen.getByLabelText("Email"), "alex@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery-staple");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => expect(screen.getByText("Trip Ledger")).toBeInTheDocument());

    expect(loginUser).toHaveBeenCalledWith({
      email: "alex@example.com",
      password: "correct-horse-battery-staple",
    });
  });

  it("shows the server error message when login fails", async () => {
    const user = userEvent.setup();
    vi.mocked(loginUser).mockRejectedValue(new Error("Invalid email or password"));

    const router = createMemoryRouter([{ path: "/login", element: <LoginPage /> }], {
      initialEntries: ["/login"],
    });

    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await user.type(screen.getByLabelText("Email"), "alex@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("Invalid email or password")).toBeInTheDocument();
  });
});
