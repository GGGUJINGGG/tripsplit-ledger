import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "./client";
import {
  clearAccessToken,
  clearRefreshToken,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "./token";

type MockResponse = Partial<Response> & { json?: () => Promise<unknown> };

function mockFetchOnce(response: MockResponse) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function mockFetchSequence(responses: MockResponse[]) {
  const fetchMock = vi.fn();
  responses.forEach((response) => {
    fetchMock.mockImplementationOnce(() => Promise.resolve(response));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("apiRequest", () => {
  beforeEach(() => {
    clearAccessToken();
    clearRefreshToken();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("resolves with the parsed JSON body on success", async () => {
    mockFetchOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: "trip-1" }),
    });

    const result = await apiRequest<{ id: string }>("/trips/trip-1");

    expect(result).toEqual({ id: "trip-1" });
  });

  it("returns undefined for a 204 No Content response", async () => {
    mockFetchOnce({ ok: true, status: 204 });

    const result = await apiRequest<void>("/trips/trip-1", { method: "DELETE" });

    expect(result).toBeUndefined();
  });

  it("does not attach an Authorization header when no token is stored", async () => {
    const fetchMock = mockFetchOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await apiRequest("/trips");

    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Headers;
    expect(headers.has("Authorization")).toBe(false);
  });

  it("attaches a Bearer Authorization header when a token is stored", async () => {
    setAccessToken("test-token");
    const fetchMock = mockFetchOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await apiRequest("/trips");

    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("throws an Error using the server's detail message on failure", async () => {
    mockFetchOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: "Trip not found" }),
    });

    await expect(apiRequest("/trips/missing")).rejects.toThrow("Trip not found");
  });

  it("falls back to a generic message when the error body isn't JSON", async () => {
    mockFetchOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("not json")),
    });

    await expect(apiRequest("/trips")).rejects.toThrow("Request failed with status 500");
  });

  it("stringifies array-shaped validation error details", async () => {
    mockFetchOnce({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: [{ msg: "amount must be greater than 0" }],
        }),
    });

    await expect(apiRequest("/trips/trip-1/expenses")).rejects.toThrow(
      /amount must be greater than 0/,
    );
  });

  it("refreshes the access token and retries once after a 401", async () => {
    setAccessToken("expired-access-token");
    setRefreshToken("valid-refresh-token");

    const fetchMock = mockFetchSequence([
      { ok: false, status: 401, json: () => Promise.resolve({ detail: "Unauthorized" }) },
      {
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            access_token: "new-access-token",
            refresh_token: "new-refresh-token",
          }),
      },
      { ok: true, status: 200, json: () => Promise.resolve({ id: "trip-1" }) },
    ]);

    const result = await apiRequest<{ id: string }>("/trips/trip-1");

    expect(result).toEqual({ id: "trip-1" });
    expect(fetchMock).toHaveBeenCalledTimes(3);

    const [refreshUrl, refreshInit] = fetchMock.mock.calls[1];
    expect(refreshUrl).toContain("/auth/refresh");
    expect(JSON.parse(refreshInit.body as string)).toEqual({
      refresh_token: "valid-refresh-token",
    });

    const [, retryInit] = fetchMock.mock.calls[2];
    const retryHeaders = retryInit.headers as Headers;
    expect(retryHeaders.get("Authorization")).toBe("Bearer new-access-token");

    expect(getAccessToken()).toBe("new-access-token");
    expect(getRefreshToken()).toBe("new-refresh-token");
  });

  it("surfaces the original 401 without calling refresh when no refresh token is stored", async () => {
    setAccessToken("expired-access-token");

    const fetchMock = mockFetchSequence([
      { ok: false, status: 401, json: () => Promise.resolve({ detail: "Unauthorized" }) },
    ]);

    await expect(apiRequest("/trips/trip-1")).rejects.toThrow("Unauthorized");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("clears tokens and surfaces the original 401 when the refresh call itself fails", async () => {
    setAccessToken("expired-access-token");
    setRefreshToken("stale-refresh-token");

    mockFetchSequence([
      { ok: false, status: 401, json: () => Promise.resolve({ detail: "Unauthorized" }) },
      { ok: false, status: 401, json: () => Promise.resolve({ detail: "Invalid refresh token" }) },
    ]);

    await expect(apiRequest("/trips/trip-1")).rejects.toThrow("Unauthorized");
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("does not attempt a refresh when the 401 comes from the login endpoint", async () => {
    setRefreshToken("valid-refresh-token");

    const fetchMock = mockFetchSequence([
      { ok: false, status: 401, json: () => Promise.resolve({ detail: "Invalid email or password" }) },
    ]);

    await expect(
      apiRequest("/auth/login", { method: "POST", body: "{}" }),
    ).rejects.toThrow("Invalid email or password");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
