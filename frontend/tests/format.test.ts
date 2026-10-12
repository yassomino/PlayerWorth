import { expect, test } from "vitest";
import { formatDifference, formatMoney } from "@/lib/format";
test.each([
  [82459040, "€82.5M"],
  [950000, "€950K"],
  [-2100000, "-€2.1M"],
  [0, "€0"],
  [200000000, "€200M"],
])("formats %s", (value, expected) =>
  expect(formatMoney(value as number)).toBe(expected),
);
test("signed differences", () => {
  expect(formatDifference(29286296)).toBe("+€29.3M");
  expect(formatDifference(-70381864)).toBe("-€70.4M");
});
