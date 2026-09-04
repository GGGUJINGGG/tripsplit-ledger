import "@testing-library/jest-dom/vitest";

// Recharts' ResponsiveContainer measures its size via ResizeObserver
// and offsetWidth/offsetHeight, none of which jsdom implements — without
// these, chart components never report a size and their children (lines,
// bars, legend) never render, even though the app works fine in a real
// browser. Global so every chart test gets it for free.
class ResizeObserverMock implements ResizeObserver {
  private readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }

  observe(target: Element) {
    this.callback(
      [
        {
          target,
          contentRect: { width: 500, height: 280 } as DOMRectReadOnly,
        } as ResizeObserverEntry,
      ],
      this,
    );
  }

  unobserve() {}
  disconnect() {}
}

Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
  configurable: true,
  value: 500,
});
Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
  configurable: true,
  value: 280,
});
globalThis.ResizeObserver = ResizeObserverMock;
