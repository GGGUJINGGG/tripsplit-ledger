import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ParticipantsPanel from "./ParticipantsPanel";

describe("ParticipantsPanel invite form", () => {
  it("invites by email and shows a confirmation on success", async () => {
    const user = userEvent.setup();
    const onInvite = vi.fn().mockResolvedValue(true);

    render(
      <ParticipantsPanel
        participants={[{ id: "p1", name: "Alex", role: "owner" }]}
        isSaving={false}
        onAdd={vi.fn()}
        onInvite={onInvite}
        onRemove={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText("Invite by email"), "maya@example.com");
    await user.click(screen.getByRole("button", { name: "Send invite" }));

    expect(onInvite).toHaveBeenCalledWith("maya@example.com");
    expect(
      await screen.findByText("Invited maya@example.com to this trip."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Invite by email")).toHaveValue("");
  });

  it("does not show a confirmation when the invite fails", async () => {
    const user = userEvent.setup();
    const onInvite = vi.fn().mockResolvedValue(false);

    render(
      <ParticipantsPanel
        participants={[{ id: "p1", name: "Alex", role: "owner" }]}
        isSaving={false}
        onAdd={vi.fn()}
        onInvite={onInvite}
        onRemove={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText("Invite by email"), "notauser@example.com");
    await user.click(screen.getByRole("button", { name: "Send invite" }));

    expect(onInvite).toHaveBeenCalledWith("notauser@example.com");
    expect(screen.queryByText(/Invited/)).not.toBeInTheDocument();
    // The failed attempt's email stays in the field so the user can see what they typed.
    expect(screen.getByLabelText("Invite by email")).toHaveValue("notauser@example.com");
  });
});
