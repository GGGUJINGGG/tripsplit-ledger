import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Participant } from "../../types";
import ExpenseForm from "./ExpenseForm";

const participants: Participant[] = [
  { id: "p1", name: "Alex" },
  { id: "p2", name: "Maya" },
];

describe("ExpenseForm validation", () => {
  it("shows an error and does not submit when the title is blank", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(
      <ExpenseForm
        participants={participants}
        editingExpense={null}
        isSaving={false}
        onCancelEdit={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText("Amount"), "10");
    await user.click(screen.getByRole("button", { name: /add expense/i }));

    expect(await screen.findByText("Title is required.")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows an error when the amount is zero or negative", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(
      <ExpenseForm
        participants={participants}
        editingExpense={null}
        isSaving={false}
        onCancelEdit={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

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

    render(
      <ExpenseForm
        participants={participants}
        editingExpense={null}
        isSaving={false}
        onCancelEdit={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

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

    render(
      <ExpenseForm
        participants={participants}
        editingExpense={null}
        isSaving={false}
        onCancelEdit={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

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
    render(
      <ExpenseForm
        participants={participants}
        editingExpense={{
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
        }}
        isSaving={false}
        onCancelEdit={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Title")).toHaveValue("Hotel");
    expect(screen.getByLabelText("Amount")).toHaveValue(120);
    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });
});
