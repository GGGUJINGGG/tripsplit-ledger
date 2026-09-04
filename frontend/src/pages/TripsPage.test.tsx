import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import TripsPage from "./TripsPage";

vi.mock("../api/trips", () => ({
  getTrips: vi.fn(),
  createTrip: vi.fn(),
}));
vi.mock("../api/invitations", () => ({
  getMyInvitations: vi.fn(),
  acceptInvitation: vi.fn(),
  declineInvitation: vi.fn(),
}));

import {
  acceptInvitation,
  declineInvitation,
  getMyInvitations,
} from "../api/invitations";
import { getTrips } from "../api/trips";

function renderPage() {
  return render(
    <MemoryRouter>
      <TripsPage />
    </MemoryRouter>,
  );
}

describe("TripsPage pending invitations", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows no pending-invites panel when there are none", async () => {
    vi.mocked(getTrips).mockResolvedValue([]);
    vi.mocked(getMyInvitations).mockResolvedValue([]);

    renderPage();

    await waitFor(() => expect(screen.getByText("No trips yet.")).toBeInTheDocument());
    expect(screen.queryByText("Pending Invites")).not.toBeInTheDocument();
  });

  it("lists a pending invite with accept/decline controls", async () => {
    vi.mocked(getTrips).mockResolvedValue([]);
    vi.mocked(getMyInvitations).mockResolvedValue([
      {
        id: "inv-1",
        trip_id: "trip-1",
        trip_name: "Iceland Road Trip",
        invited_at: "2026-07-01T00:00:00Z",
      },
    ]);

    renderPage();

    expect(
      await screen.findByText('You\'ve been invited to "Iceland Road Trip"'),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /accept invite/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /decline invite/i })).toBeInTheDocument();
  });

  it("accepting an invite removes it from the list and reloads trips", async () => {
    const user = userEvent.setup();
    vi.mocked(getTrips).mockResolvedValue([]);
    vi.mocked(getMyInvitations)
      .mockResolvedValueOnce([
        {
          id: "inv-1",
          trip_id: "trip-1",
          trip_name: "Iceland Road Trip",
          invited_at: "2026-07-01T00:00:00Z",
        },
      ])
      .mockResolvedValueOnce([]);
    vi.mocked(acceptInvitation).mockResolvedValue({
      id: "member-1",
      name: "Me",
      user_id: "user-1",
      role: "member",
    });

    renderPage();

    await screen.findByText('You\'ve been invited to "Iceland Road Trip"');
    await user.click(screen.getByRole("button", { name: /accept invite/i }));

    expect(acceptInvitation).toHaveBeenCalledWith("inv-1");
    await waitFor(() =>
      expect(
        screen.queryByText('You\'ve been invited to "Iceland Road Trip"'),
      ).not.toBeInTheDocument(),
    );
    expect(getTrips).toHaveBeenCalledTimes(2);
  });

  it("declining an invite removes it from the list without reloading trips", async () => {
    const user = userEvent.setup();
    vi.mocked(getTrips).mockResolvedValue([]);
    vi.mocked(getMyInvitations)
      .mockResolvedValueOnce([
        {
          id: "inv-1",
          trip_id: "trip-1",
          trip_name: "Iceland Road Trip",
          invited_at: "2026-07-01T00:00:00Z",
        },
      ])
      .mockResolvedValueOnce([]);
    vi.mocked(declineInvitation).mockResolvedValue(undefined);

    renderPage();

    await screen.findByText('You\'ve been invited to "Iceland Road Trip"');
    await user.click(screen.getByRole("button", { name: /decline invite/i }));

    expect(declineInvitation).toHaveBeenCalledWith("inv-1");
    await waitFor(() =>
      expect(
        screen.queryByText('You\'ve been invited to "Iceland Road Trip"'),
      ).not.toBeInTheDocument(),
    );
    expect(getTrips).toHaveBeenCalledTimes(1);
  });
});
