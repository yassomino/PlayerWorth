import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import ErrorPage from "@/app/error";
import NotFound from "@/app/not-found";

test("error recovery retries without exposing internal details", () => {
  const retry = vi.fn();
  render(
    <ErrorPage error={new Error("private connection detail")} retry={retry} />,
  );
  expect(screen.queryByText(/private connection/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(retry).toHaveBeenCalledOnce();
  expect(screen.getByRole("link")).toHaveAttribute("href", "/");
});

test("unknown routes offer a real home recovery link", () => {
  render(<NotFound />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "Page not found",
  );
  expect(screen.getByRole("link")).toHaveAttribute("href", "/");
});
