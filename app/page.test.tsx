import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("next/dynamic", () => ({ default: () => function MockEarthGlobe({ onEarthClick }: { onEarthClick?: () => void }) { return <button data-testid="earth-globe" onClick={onEarthClick}>Earth</button>; } }));
vi.mock("../components/LandingHero", () => ({ default: () => <div /> }));
vi.mock("../components/Starfield", () => ({ default: () => <div /> }));
vi.mock("../components/RegionSelector", () => ({ default: ({ isOpen, onSelect }: { isOpen: boolean; onSelect: (region: string) => void }) => isOpen ? <button onClick={() => onSelect("can-gio")}>Select Can Gio</button> : null }));

import Home from "./page";

describe("landing page navigation", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    push.mockReset();
  });

  it("redirects even when the globe completion callback never fires", () => {
    render(<Home />);
    fireEvent.click(screen.getByTestId("earth-globe"));
    fireEvent.click(screen.getByRole("button", { name: "Select Can Gio" }));

    vi.advanceTimersByTime(4600);

    expect(push).toHaveBeenCalledWith("/explorer?region=can-gio");
    vi.useRealTimers();
  });
});
