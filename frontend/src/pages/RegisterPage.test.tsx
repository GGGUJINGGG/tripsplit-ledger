import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../auth/AuthContext";
import RegisterPage from "./RegisterPage";

vi.mock("../api/auth", () => ({
  registerUser: vi.fn(),
  loginUser: vi.fn(),
  getCurrentUser: vi.fn(),
  logoutUser: vi.fn(),
}));

function renderPage(path: string) {
  const router = createMemoryRouter(
    [{ path: "/register", element: <RegisterPage /> }],
    { initialEntries: [path] },
  );
  return render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
}

describe("RegisterPage invite prefill", () => {
  it("starts with an empty email and the generic message when there is no invite", () => {
    renderPage("/register");

    expect(screen.getByLabelText("Email")).toHaveValue("");
    expect(
      screen.getByText("Register to create and manage shared trips."),
    ).toBeInTheDocument();
  });

  it("prefills the email and shows the invite message from a ?email= query param", () => {
    renderPage("/register?email=invitee%40example.com");

    expect(screen.getByLabelText("Email")).toHaveValue("invitee@example.com");
    expect(
      screen.getByText(
        "You've been invited to a trip — create your account to join.",
      ),
    ).toBeInTheDocument();
  });
});
