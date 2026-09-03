import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import ForgotPasswordPage from "./ForgotPasswordPage";

vi.mock("../api/auth", () => ({
  requestPasswordReset: vi.fn(),
}));

import { requestPasswordReset } from "../api/auth";

function renderPage() {
  const router = createMemoryRouter(
    [{ path: "/forgot-password", element: <ForgotPasswordPage /> }],
    { initialEntries: ["/forgot-password"] },
  );
  return render(<RouterProvider router={router} />);
}

describe("ForgotPasswordPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows a generic confirmation after a successful submission", async () => {
    const user = userEvent.setup();
    vi.mocked(requestPasswordReset).mockResolvedValue(undefined);

    renderPage();

    await user.type(screen.getByLabelText("Email"), "alex@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(
      await screen.findByText(/password reset link has been sent/i),
    ).toBeInTheDocument();
    expect(requestPasswordReset).toHaveBeenCalledWith("alex@example.com");
  });

  it("shows the same confirmation even for an unregistered email", async () => {
    const user = userEvent.setup();
    // The backend itself always resolves 202 regardless of whether the
    // email is registered — it never rejects here.
    vi.mocked(requestPasswordReset).mockResolvedValue(undefined);

    renderPage();

    await user.type(screen.getByLabelText("Email"), "nobody@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(
      await screen.findByText(/password reset link has been sent/i),
    ).toBeInTheDocument();
  });

  it("shows an error message when the request itself fails", async () => {
    const user = userEvent.setup();
    vi.mocked(requestPasswordReset).mockRejectedValue(
      new Error("Too many attempts. Please try again later."),
    );

    renderPage();

    await user.type(screen.getByLabelText("Email"), "alex@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(
      await screen.findByText("Too many attempts. Please try again later."),
    ).toBeInTheDocument();
  });
});
