import { expect, test, vi } from "vitest";
import { apiBaseUrl, searchPlayers, simulatePlayer } from "@/lib/api/client";

test("simulation uses partial JSON and never enables persistence", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://example.test/api/v1");
  const fetcher = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({}) });
  vi.stubGlobal("fetch", fetcher);
  await simulatePlayer(7, { goals: 21 }, "2025/26");
  const [url, options] = fetcher.mock.calls[0];
  expect(url).toBe(
    "http://example.test/api/v1/players/7/simulate?season=2025%2F26",
  );
  expect(options.method).toBe("POST");
  expect(JSON.parse(options.body)).toEqual({ goals: 21 });
  expect(url).not.toContain("persist");
});
test("configured base removes trailing slash and encodes search", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://example.test/api/v1/");
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ items: [], limit: 8, offset: 0 }),
  });
  vi.stubGlobal("fetch", fetcher);
  expect(apiBaseUrl()).toBe("http://example.test/api/v1");
  expect((await searchPlayers("a & b")).items).toEqual([]);
  expect(fetcher.mock.calls[0][0]).toBe(
    "http://example.test/api/v1/players?search=a+%26+b&limit=8&offset=0",
  );
});
test.each([404, 422, 500, 503])("safe error for %s", async (status) => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://example.test/api/v1");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      json: async () => ({ detail: "private stack trace" }),
    }),
  );
  await expect(searchPlayers("test")).rejects.toMatchObject({ status });
  await expect(searchPlayers("test")).rejects.not.toThrow("private");
});
test("network failure is safe", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://example.test");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("secret")));
  await expect(searchPlayers("test")).rejects.toThrow("Couldn't connect");
});
