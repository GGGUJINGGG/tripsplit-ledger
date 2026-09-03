import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import ResetPasswordPage from "./ResetPasswordPage";

vi.mock("../api/auth", () => ({
  resetPassword: vi.fn(),
}));

import { resetPassword } from "../api/auth";

function renderPage(path: string) {
  const router = createMemoryRouter(
    [{ path: "/reset-password", element: <ResetPasswordPage /> }],
    { initialEntries: [path] },
  );
  return render(<RouterProvider router={router} />);
}

describe("ResetPasswordPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows a message asking to request a new link when the token is missing", () => {
    renderPage("/reset-password");

    expect(
      screen.getByText(/this reset link is invalid or missing its token/i),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("New password")).not.toBeInTheDocument();
  });

  it("submits the token from the URL along with the new password", async () => {
    const user = userEvent.setup();
    vi.mocked(resetPassword).mockResolvedValue(undefined);

    renderPage("/reset-password?token=abc123");

    await user.type(
      screen.getByLabelText(/^New password/),
      "brand-new-password-456",
    );
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "brand-new-password-456",
    );
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(resetPassword).toHaveBeenCalledWith(
      "abc123",
      "brand-new-password-456",
    );
    expect(await screen.findByText(/your password has been reset/i)).toBeInTheDocument();
  });

  it("rejects mismatched passwords before calling the API", async () => {
    const user = userEvent.setup();

    renderPage("/reset-password?token=abc123");

    await user.type(
      screen.getByLabelText(/^New password/),
      "brand-new-password-456",
    );
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "a-different-password-789",
    );
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(await screen.findByText("Passwords do not match")).toBeInTheDocument();
    expect(resetPassword).not.toHaveBeenCalled();
  });

  it("shows the server error message when the token is invalid or expired", async () => {
    const user = userEvent.setup();
    vi.mocked(resetPassword).mockRejectedValue(
      new Error("Invalid or expired reset token"),
    );

    renderPage("/reset-password?token=expired-token");

    await user.type(
      screen.getByLabelText(/^New password/),
      "brand-new-password-456",
    );
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "brand-new-password-456",
    );
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(
      await screen.findByText("Invalid or expired reset token"),
    ).toBeInTheDocument();
  });
});
