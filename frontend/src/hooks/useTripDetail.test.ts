import { act, renderHook, waitFor } from "@testing-library/react";
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
vi.mock("../api/payments", () => ({
  createPayment: vi.fn(),
  deletePayment: vi.fn(),
}));

import { getDashboard } from "../api/dashboard";
import { createPayment, deletePayment } from "../api/payments";
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
    payments: [],
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

  it("recordPayment creates the payment then refreshes the trip", async () => {
    const trip = buildTrip();
    vi.mocked(getTrip).mockResolvedValue(trip);
    vi.mocked(getSettlements).mockResolvedValue({ settlements: [] });
    vi.mocked(getDashboard).mockResolvedValue(buildDashboard());
    vi.mocked(createPayment).mockResolvedValue({
      id: "payment-1",
      trip_id: "trip-1",
      from_participant: "p2",
      to_participant: "p1",
      amount: 50,
      currency: "USD",
      date: "2026-07-02",
      note: null,
      created_at: "2026-07-02T00:00:00Z",
      updated_at: "2026-07-02T00:00:00Z",
    });

    const { result } = renderHook(() => useTripDetail("trip-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const succeeded = await result.current.recordPayment({
      from_participant: "p2",
      to_participant: "p1",
      amount: 50,
      currency: "USD",
      date: "2026-07-02",
    });

    expect(succeeded).toBe(true);
    expect(createPayment).toHaveBeenCalledWith("trip-1", {
      from_participant: "p2",
      to_participant: "p1",
      amount: 50,
      currency: "USD",
      date: "2026-07-02",
    });
    // Recording a payment must refresh trip/dashboard data, same as saving
    // an expense does.
    expect(getTrip).toHaveBeenCalledTimes(2);
  });

  it("removePayment deletes the payment then refreshes the trip", async () => {
    const trip = buildTrip();
    vi.mocked(getTrip).mockResolvedValue(trip);
    vi.mocked(getSettlements).mockResolvedValue({ settlements: [] });
    vi.mocked(getDashboard).mockResolvedValue(buildDashboard());
    vi.mocked(deletePayment).mockResolvedValue(undefined);

    const { result } = renderHook(() => useTripDetail("trip-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const succeeded = await result.current.removePayment("payment-1");

    expect(succeeded).toBe(true);
    expect(deletePayment).toHaveBeenCalledWith("trip-1", "payment-1");
    expect(getTrip).toHaveBeenCalledTimes(2);
  });

  it("groups daily spending by date and currency, sorted chronologically", async () => {
    const trip = buildTrip({
      expenses: [
        {
          id: "e1",
          trip_id: "trip-1",
          title: "Dinner",
          amount: 40,
          paid_by: "p1",
          split_among: ["p1", "p2"],
          expense_type: "shared",
          category: "food",
          date: "2026-07-02",
          currency: "USD",
          note: null,
          created_at: "2026-07-02T00:00:00Z",
          updated_at: "2026-07-02T00:00:00Z",
        },
        {
          id: "e2",
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
          id: "e3",
          trip_id: "trip-1",
          title: "Taxi",
          amount: 20,
          paid_by: "p1",
          split_among: ["p1"],
          expense_type: "personal",
          category: "transportation",
          date: "2026-07-01",
          currency: "USD",
          note: null,
          created_at: "2026-07-01T01:00:00Z",
          updated_at: "2026-07-01T01:00:00Z",
        },
        {
          id: "e4",
          trip_id: "trip-1",
          title: "Parking",
          amount: 30,
          paid_by: "p1",
          split_among: ["p1", "p2"],
          expense_type: "shared",
          category: "transportation",
          date: "2026-07-01",
          currency: "CNY",
          note: null,
          created_at: "2026-07-01T02:00:00Z",
          updated_at: "2026-07-01T02:00:00Z",
        },
      ],
    });
    vi.mocked(getTrip).mockResolvedValue(trip);
    vi.mocked(getSettlements).mockResolvedValue({ settlements: [] });
    vi.mocked(getDashboard).mockResolvedValue(buildDashboard());

    const { result } = renderHook(() => useTripDetail("trip-1"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.dailySpendingByCurrency).toEqual([
      { date: "2026-07-01", currency: "USD", amount: 120 },
      { date: "2026-07-01", currency: "CNY", amount: 30 },
      { date: "2026-07-02", currency: "USD", amount: 40 },
    ]);
  });

  describe("refresh on tab visibility", () => {
    afterEach(() => {
      Object.defineProperty(document, "visibilityState", {
        value: "visible",
        configurable: true,
      });
    });

    it("quietly reloads the trip when the tab becomes visible again", async () => {
      vi.mocked(getTrip).mockResolvedValue(buildTrip());
      vi.mocked(getSettlements).mockResolvedValue({ settlements: [] });
      vi.mocked(getDashboard).mockResolvedValue(buildDashboard());

      const { result } = renderHook(() => useTripDetail("trip-1"));
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(getTrip).toHaveBeenCalledTimes(1);

      document.dispatchEvent(new Event("visibilitychange"));

      await waitFor(() => expect(getTrip).toHaveBeenCalledTimes(2));
      // Silent refresh: no loading spinner for a background revalidation.
      expect(result.current.isLoading).toBe(false);
    });

    it("does not reload while the tab is hidden", async () => {
      vi.mocked(getTrip).mockResolvedValue(buildTrip());
      vi.mocked(getSettlements).mockResolvedValue({ settlements: [] });
      vi.mocked(getDashboard).mockResolvedValue(buildDashboard());

      const { result } = renderHook(() => useTripDetail("trip-1"));
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(getTrip).toHaveBeenCalledTimes(1);

      Object.defineProperty(document, "visibilityState", {
        value: "hidden",
        configurable: true,
      });
      document.dispatchEvent(new Event("visibilitychange"));

      expect(getTrip).toHaveBeenCalledTimes(1);
    });
  });

  describe("refreshTrip", () => {
    it("reloads the trip and toggles isRefreshing around the request", async () => {
      vi.mocked(getTrip).mockResolvedValue(buildTrip());
      vi.mocked(getSettlements).mockResolvedValue({ settlements: [] });
      vi.mocked(getDashboard).mockResolvedValue(buildDashboard());

      const { result } = renderHook(() => useTripDetail("trip-1"));
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(getTrip).toHaveBeenCalledTimes(1);
      expect(result.current.isRefreshing).toBe(false);

      let refreshPromise!: Promise<void>;
      act(() => {
        refreshPromise = result.current.refreshTrip();
      });
      expect(result.current.isRefreshing).toBe(true);
      await act(() => refreshPromise);

      expect(getTrip).toHaveBeenCalledTimes(2);
      expect(result.current.isRefreshing).toBe(false);
      // A manual refresh is still a "quiet" reload — no full-page spinner.
      expect(result.current.isLoading).toBe(false);
    });
  });
});
