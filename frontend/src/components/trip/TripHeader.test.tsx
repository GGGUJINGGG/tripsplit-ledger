import type { ComponentProps } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { Trip } from "../../types";
import TripHeader from "./TripHeader";

const trip: Trip = {
  id: "trip-1",
  name: "Iceland Road Trip",
  start_date: "2026-07-01",
  end_date: "2026-07-10",
  participants: [
    { id: "p1", name: "Alex", user_id: "user-alex", role: "owner" },
    { id: "p2", name: "Maya", user_id: "user-maya", role: "member" },
  ],
  expenses: [],
  payments: [],
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

function renderHeader(props: Partial<ComponentProps<typeof TripHeader>> = {}) {
  return render(
    <MemoryRouter>
      <TripHeader
        trip={trip}
        currentUserId="user-alex"
        isSaving={false}
        onRename={vi.fn().mockResolvedValue(true)}
        onDelete={vi.fn()}
        {...props}
      />
    </MemoryRouter>,
  );
}

describe("TripHeader", () => {
  it("shows edit and delete controls to the trip owner", () => {
    renderHeader({ currentUserId: "user-alex" });

    expect(screen.getByRole("button", { name: /edit trip/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete trip/i })).toBeInTheDocument();
  });

  it("hides edit and delete controls from a non-owner member", () => {
    renderHeader({ currentUserId: "user-maya" });

    expect(screen.queryByRole("button", { name: /edit trip/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /delete trip/i })).not.toBeInTheDocument();
  });

  it("submits the edited name and dates, then exits edit mode on success", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn().mockResolvedValue(true);
    renderHeader({ onRename });

    await user.click(screen.getByRole("button", { name: /edit trip/i }));

    const nameInput = screen.getByLabelText("Trip name");
    await user.clear(nameInput);
    await user.type(nameInput, "Renamed Trip");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(onRename).toHaveBeenCalledWith({
      name: "Renamed Trip",
      start_date: "2026-07-01",
      end_date: "2026-07-10",
    });
    expect(await screen.findByRole("heading", { name: "Iceland Road Trip" })).toBeInTheDocument();
  });

  it("stays in edit mode when the save fails", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn().mockResolvedValue(false);
    renderHeader({ onRename });

    await user.click(screen.getByRole("button", { name: /edit trip/i }));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByRole("button", { name: "Save changes" })).toBeInTheDocument();
  });

  it("returns to the read-only view on cancel without saving", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();
    renderHeader({ onRename });

    await user.click(screen.getByRole("button", { name: /edit trip/i }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onRename).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "Iceland Road Trip" })).toBeInTheDocument();
  });

  it("calls onDelete when the delete button is clicked", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    renderHeader({ onDelete });

    await user.click(screen.getByRole("button", { name: /delete trip/i }));

    expect(onDelete).toHaveBeenCalledTimes(1);
  });
});
