import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import RefreshFab from "./RefreshFab";

describe("RefreshFab", () => {
  it("calls onRefresh when clicked", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(<RefreshFab isRefreshing={false} onRefresh={onRefresh} />);

    await user.click(screen.getByRole("button", { name: /refresh trip data/i }));

    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("disables itself while a refresh is in flight", () => {
    render(<RefreshFab isRefreshing={true} onRefresh={vi.fn()} />);

    expect(screen.getByRole("button", { name: /refresh trip data/i })).toBeDisabled();
  });
});
