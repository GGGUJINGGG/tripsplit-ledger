import type { ComponentProps } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../../auth/AuthContext";
import { clearAccessToken, setAccessToken } from "../../api/token";
import type { Participant } from "../../types";
import ExpenseForm from "./ExpenseForm";

vi.mock("../../api/auth", () => ({
  getCurrentUser: vi.fn(),
  logoutUser: vi.fn(),
}));

import { getCurrentUser } from "../../api/auth";

const participants: Participant[] = [
  { id: "p1", name: "Alex", user_id: "user-alex", role: "member" },
  { id: "p2", name: "Maya", user_id: "user-maya", role: "member" },
];

function renderForm(props: Partial<ComponentProps<typeof ExpenseForm>>) {
  return render(
    <AuthProvider>
      <ExpenseForm
        participants={participants}
        editingExpense={null}
        isSaving={false}
        onCancelEdit={vi.fn()}
        onSubmit={vi.fn()}
        {...props}
      />
    </AuthProvider>,
  );
}

describe("ExpenseForm validation", () => {
  afterEach(() => {
    clearAccessToken();
    vi.clearAllMocks();
  });

  it("shows an error and does not submit when the title is blank", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    renderForm({ onSubmit });

    await user.type(screen.getByLabelText("Amount"), "10");
    await user.click(screen.getByRole("button", { name: /add expense/i }));

    expect(await screen.findByText("Title is required.")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows an error when the amount is zero or negative", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    renderForm({ onSubmit });

    await user.type(screen.getByLabelText("Title"), "Dinner");
    await user.type(screen.getByLabelText("Amount"), "0");
    await user.click(screen.getByRole("button", { name: /add expense/i }));

    expect(
      await screen.findByText("Amount must be greater than 0."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("requires at least one split participant for a shared expense", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    renderForm({ onSubmit });

    await user.type(screen.getByLabelText("Title"), "Dinner");
    await user.type(screen.getByLabelText("Amount"), "20");
    // Both participants start checked by default; uncheck both.
    await user.click(screen.getByLabelText("Alex"));
    await user.click(screen.getByLabelText("Maya"));
    await user.click(screen.getByRole("button", { name: /add expense/i }));

    expect(
      await screen.findByText("Select at least one person to share this expense."),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a valid shared expense with the entered values", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(true);

    renderForm({ onSubmit });

    await user.type(screen.getByLabelText("Title"), "Dinner");
    await user.type(screen.getByLabelText("Amount"), "42.5");
    await user.click(screen.getByRole("button", { name: /add expense/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const payload = onSubmit.mock.calls[0][0];
    expect(payload).toMatchObject({
      title: "Dinner",
      amount: 42.5,
      paid_by: "p1",
      split_among: ["p1", "p2"],
      expense_type: "shared",
      currency: "USD",
    });
  });

  it("pre-fills the form from editingExpense and shows Save changes", () => {
    renderForm({
      editingExpense: {
        id: "e1",
        trip_id: "trip-1",
        title: "Hotel",
        amount: 120,
        paid_by: "p1",
        split_among: ["p1"],
        expense_type: "personal",
        category: "hotel",
        date: "2026-07-01",
        currency: "USD",
        note: null,
        created_at: "2026-07-01T00:00:00Z",
        updated_at: "2026-07-01T00:00:00Z",
      },
    });

    expect(screen.getByLabelText("Title")).toHaveValue("Hotel");
    expect(screen.getByLabelText("Amount")).toHaveValue(120);
    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });
});

describe("ExpenseForm personal expense payer lock", () => {
  afterEach(() => {
    clearAccessToken();
    vi.clearAllMocks();
  });

  it("locks Paid by to yourself when Type is switched to Personal", async () => {
    const user = userEvent.setup();
    setAccessToken("valid-token");
    vi.mocked(getCurrentUser).mockResolvedValue({
      id: "user-maya",
      email: "maya@example.com",
      display_name: "Maya",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderForm({});

    // Wait for AuthProvider to resolve the logged-in user (Maya).
    await waitFor(() =>
      expect(screen.getByLabelText("Amount")).toBeInTheDocument(),
    );

    await user.selectOptions(screen.getByLabelText("Type"), "personal");

    const paidBySelect = screen.getByLabelText("Paid by") as HTMLSelectElement;
    expect(paidBySelect).toBeDisabled();
    expect(paidBySelect).toHaveValue("p2"); // Maya's participant id
    expect(screen.getByText("Maya", { selector: "option" })).toBeInTheDocument();
    expect(screen.queryByText("Alex", { selector: "option" })).not.toBeInTheDocument();
  });

  it("submits the personal expense with yourself as the payer", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(true);
    setAccessToken("valid-token");
    vi.mocked(getCurrentUser).mockResolvedValue({
      id: "user-alex",
      email: "alex@example.com",
      display_name: "Alex",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderForm({ onSubmit });
    await waitFor(() =>
      expect(screen.getByLabelText("Amount")).toBeInTheDocument(),
    );

    await user.selectOptions(screen.getByLabelText("Type"), "personal");
    await user.type(screen.getByLabelText("Title"), "Coffee");
    await user.type(screen.getByLabelText("Amount"), "5");
    await user.click(screen.getByRole("button", { name: /add expense/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      paid_by: "p1",
      split_among: ["p1"],
      expense_type: "personal",
    });
  });
});
