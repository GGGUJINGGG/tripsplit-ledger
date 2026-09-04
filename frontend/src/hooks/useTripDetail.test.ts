import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DashboardSummary, Trip } from "../types";
import { useTripDetail } from "./useTripDetail";

vi.mock("../api/trips", () => ({ getTrip: vi.fn() }));
vi.mock("../api/settlements", () => ({ getSettlements: vi.fn() }));
vi.mock("../api/dashboard", () => ({ getDashboard: vi.fn() }));
vi.mock("../api/participants", () => ({
  createParticipant: vi.fn(),
  deleteParticipant: vi.fn(),
}));
vi.mock("../api/expenses", () => ({
  createExpense: vi.fn(),
  updateExpense: vi.fn(),
  deleteExpense: vi.fn(),
}));

import { getDashboard } from "../api/dashboard";
import { getSettlements } from "../api/settlements";
import { getTrip } from "../api/trips";

function buildTrip(overrides: Partial<Trip> = {}): Trip {
  return {
    id: "trip-1",
    name: "Iceland Road Trip",
    start_date: "2026-07-01",
    end_date: null,
    participants: [
      { id: "p1", name: "Alex", role: "owner" },
      { id: "p2", name: "Maya", role: "member" },
    ],
    expenses: [
      {
        id: "e1",
        trip_id: "trip-1",
        title: "Hotel",
        amount: 100,
        paid_by: "p1",
        split_among: ["p1", "p2"],
        expense_type: "shared",
        category: "hotel",
        date: "2026-07-01",
        currency: "USD",
        note: null,
        created_at: "2026-07-01T00:00:00Z",
        updated_at: "2026-07-01T00:00:00Z",
      },
    ],
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
    ...overrides,
  };
}

function buildDashboard(overrides: Partial<DashboardSummary> = {}): DashboardSummary {
  return {
    total_trip_spending: 100,
    spending_by_category: [],
    spending_by_day: [],
    paid_by_person: [{ participant_id: "p1", name: "Alex", amount: 100 }],
    owed_by_person: [
      { participant_id: "p1", name: "Alex", amount: 50 },
      { participant_id: "p2", name: "Maya", amount: 50 },
    ],
    net_balances: [
      { participant_id: "p1", name: "Alex", balance: 50 },
      { participant_id: "p2", name: "Maya", balance: -50 },
    ],
    ...overrides,
  };
}

describe("useTripDetail", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("sources shared responsibility and net balance from the /dashboard response, not from client-side splitting", async () => {
    vi.mocked(getTrip).mockResolvedValue(buildTrip());
    vi.mocked(getSettlements).mockResolvedValue({ settlements: [] });
    vi.mocked(getDashboard).mockResolvedValue(buildDashboard());

    const { result } = renderHook(() => useTripDetail("trip-1"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const alex = result.current.participantSpendingSummary.find(
      (item) => item.participant.id === "p1",
    );
    const maya = result.current.participantSpendingSummary.find(
      (item) => item.participant.id === "p2",
    );

    // These values come straight from the mocked dashboard response
    // (50/50, +50/-50) rather than being recomputed from expense.split_among
    // in the hook itself.
    expect(alex?.sharedResponsibility).toEqual([{ currency: "USD", amount: 50 }]);
    expect(alex?.netBalances).toEqual([{ currency: "USD", amount: 50 }]);
    expect(maya?.sharedResponsibility).toEqual([{ currency: "USD", amount: 50 }]);
    expect(maya?.netBalances).toEqual([{ currency: "USD", amount: -50 }]);
  });

  it("does not attribute a currency to shared responsibility or net balance for mixed-currency trips", async () => {
    vi.mocked(getTrip).mockResolvedValue(
      buildTrip({
        expenses: [
          {
            id: "e1",
            trip_id: "trip-1",
            title: "Hotel",
            amount: 100,
            paid_by: "p1",
            split_among: ["p1", "p2"],
            expense_type: "shared",
            category: "hotel",
            date: "2026-07-01",
            currency: "USD",
            note: null,
            created_at: "2026-07-01T00:00:00Z",
            updated_at: "2026-07-01T00:00:00Z",
          },
          {
            id: "e2",
            trip_id: "trip-1",
            title: "Dinner",
            amount: 40,
            paid_by: "p2",
            split_among: ["p1", "p2"],
            expense_type: "shared",
            category: "food",
            date: "2026-07-01",
            currency: "EUR",
            note: null,
            created_at: "2026-07-01T00:00:00Z",
            updated_at: "2026-07-01T00:00:00Z",
          },
        ],
      }),
    );
    vi.mocked(getSettlements).mockResolvedValue({ settlements: [] });
    // The backend's own dashboard math isn't currency-segmented, so its
    // numbers can't be safely labeled with one currency for mixed trips.
    vi.mocked(getDashboard).mockResolvedValue(
      buildDashboard({
        owed_by_person: [
          { participant_id: "p1", name: "Alex", amount: 70 },
          { participant_id: "p2", name: "Maya", amount: 70 },
        ],
      }),
    );

    const { result } = renderHook(() => useTripDetail("trip-1"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.settlementCurrency).toBeNull();
    for (const item of result.current.participantSpendingSummary) {
      expect(item.sharedResponsibility).toEqual([]);
      expect(item.netBalances).toEqual([]);
    }
  });

  it("still refreshes trip and dashboard when /settlements 409s on a mixed-currency trip", async () => {
    const trip = buildTrip({
      expenses: [
        {
          id: "e1",
          trip_id: "trip-1",
          title: "Hotel",
          amount: 100,
          paid_by: "p1",
          split_among: ["p1", "p2"],
          expense_type: "shared",
          category: "hotel",
          date: "2026-07-01",
          currency: "USD",
          note: null,
          created_at: "2026-07-01T00:00:00Z",
          updated_at: "2026-07-01T00:00:00Z",
        },
        {
          id: "e2",
          trip_id: "trip-1",
          title: "Parking",
          amount: 20,
          paid_by: "p2",
          split_among: ["p1", "p2"],
          expense_type: "shared",
          category: "transportation",
          date: "2026-07-01",
          currency: "CNY",
          note: null,
          created_at: "2026-07-01T00:00:00Z",
          updated_at: "2026-07-01T00:00:00Z",
        },
      ],
    });
    vi.mocked(getTrip).mockResolvedValue(trip);
    // The real backend returns 409 here for mixed-currency trips.
    vi.mocked(getSettlements).mockRejectedValue(
      new Error("Trip has shared expenses in multiple currencies; cannot generate settlements"),
    );
    vi.mocked(getDashboard).mockResolvedValue(buildDashboard());

    const { result } = renderHook(() => useTripDetail("trip-1"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // The 409 from /settlements must not prevent trip/dashboard from loading.
    expect(result.current.trip).toEqual(trip);
    expect(result.current.error).toBeNull();
    expect(result.current.settlements).toEqual([]);
    expect(
      result.current.spendingByCurrency.find((item) => item.currency === "CNY")?.amount,
    ).toBe(20);
  });
});
