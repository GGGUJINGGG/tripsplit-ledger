import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearAccessToken, setAccessToken } from "../api/token";
import { AuthProvider } from "./AuthContext";
import ProtectedRoute from "./ProtectedRoute";

vi.mock("../api/auth", () => ({
  getCurrentUser: vi.fn(),
  logoutUser: vi.fn(),
}));

import { getCurrentUser } from "../api/auth";

function renderProtected() {
  const router = createMemoryRouter(
    [
      { path: "/login", element: <p>login page</p> },
      {
        element: <ProtectedRoute />,
        children: [{ path: "/", element: <p>protected content</p> }],
      },
    ],
    { initialEntries: ["/"] },
  );

  return render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
}

describe("ProtectedRoute", () => {
  afterEach(() => {
    clearAccessToken();
    vi.clearAllMocks();
  });

  it("redirects to /login when there is no authenticated user", async () => {
    renderProtected();

    await waitFor(() => expect(screen.getByText("login page")).toBeInTheDocument());
  });

  it("renders the protected content once the user loads", async () => {
    setAccessToken("valid-token");
    vi.mocked(getCurrentUser).mockResolvedValue({
      id: "u1",
      email: "alex@example.com",
      display_name: "Alex",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderProtected();

    await waitFor(() =>
      expect(screen.getByText("protected content")).toBeInTheDocument(),
    );
  });
});
