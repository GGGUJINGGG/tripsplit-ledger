import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest } from "./client";
import { clearAccessToken, setAccessToken } from "./token";

function mockFetchOnce(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("apiRequest", () => {
  beforeEach(() => {
    clearAccessToken();
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
});
