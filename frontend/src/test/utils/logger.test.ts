import { describe, it, expect, beforeEach, vi } from "vitest";
import { createLogger, Logger } from "../../utils/logger";

describe("Logger", () => {
  beforeEach(() => {
    Logger.clear();
    vi.restoreAllMocks();
  });

  it("creates a logger with a category", () => {
    const logger = createLogger("TestCategory");
    expect(logger).toBeDefined();
  });

  it("logs debug messages", () => {
    const spy = vi.spyOn(console, "debug").mockImplementation(() => {});
    const logger = createLogger("Test");
    logger.debug("debug message");

    expect(spy).toHaveBeenCalledOnce();
    expect(spy.mock.calls[0][1]).toBe("debug message");
  });

  it("logs info messages", () => {
    const spy = vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = createLogger("Test");
    logger.info("info message");

    expect(spy).toHaveBeenCalledOnce();
    expect(spy.mock.calls[0][1]).toBe("info message");
  });

  it("logs warn messages", () => {
    const spy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const logger = createLogger("Test");
    logger.warn("warn message");

    expect(spy).toHaveBeenCalledOnce();
    expect(spy.mock.calls[0][1]).toBe("warn message");
  });

  it("logs error messages", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const logger = createLogger("Test");
    logger.error("error message");

    expect(spy).toHaveBeenCalledOnce();
    expect(spy.mock.calls[0][1]).toBe("error message");
  });

  it("includes data in log entries", () => {
    const spy = vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = createLogger("Test");
    const data = { key: "value" };
    logger.info("with data", data);

    expect(spy).toHaveBeenCalledOnce();
    expect(spy.mock.calls[0][2]).toEqual(data);
  });

  it("stores entries in static collection", () => {
    vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = createLogger("Test");
    logger.info("first");
    logger.info("second");

    const entries = Logger.getEntries();
    expect(entries).toHaveLength(2);
    expect(entries[0].message).toBe("first");
    expect(entries[1].message).toBe("second");
  });

  it("entries have correct structure", () => {
    vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = createLogger("MyCategory");
    logger.info("test message", { foo: "bar" });

    const entries = Logger.getEntries();
    expect(entries).toHaveLength(1);
    expect(entries[0]).toEqual(
      expect.objectContaining({
        level: "info",
        category: "MyCategory",
        message: "test message",
        data: { foo: "bar" },
      })
    );
    expect(entries[0].timestamp).toBeDefined();
  });

  it("clears entries", () => {
    vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = createLogger("Test");
    logger.info("one");
    logger.info("two");
    expect(Logger.getEntries()).toHaveLength(2);

    Logger.clear();
    expect(Logger.getEntries()).toHaveLength(0);
  });

  it("caps entries at maxEntries", () => {
    vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = createLogger("Test");

    // Logger.maxEntries is 1000, log 1005 entries
    for (let i = 0; i < 1005; i++) {
      logger.info(`entry-${i}`);
    }

    const entries = Logger.getEntries();
    expect(entries.length).toBeLessThanOrEqual(1000);
    // The oldest entries should have been trimmed
    expect(entries[0].message).toBe("entry-5");
    expect(entries[entries.length - 1].message).toBe("entry-1004");
  });

  it("getEntries returns a copy", () => {
    vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = createLogger("Test");
    logger.info("test");

    const entries1 = Logger.getEntries();
    const entries2 = Logger.getEntries();
    expect(entries1).toEqual(entries2);
    expect(entries1).not.toBe(entries2);
  });

  it("logs empty string for data when data is undefined", () => {
    const spy = vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = createLogger("Test");
    logger.info("no data");

    expect(spy.mock.calls[0][2]).toBe("");
  });

  it("uses correct prefix format", () => {
    const spy = vi.spyOn(console, "info").mockImplementation(() => {});
    const logger = createLogger("MyApp");
    logger.info("hello");

    const prefix = spy.mock.calls[0][0] as string;
    expect(prefix).toMatch(/^\[.*\] \[INFO\] \[MyApp\]$/);
  });

  it("multiple loggers share the same entries store", () => {
    vi.spyOn(console, "info").mockImplementation(() => {});
    const logger1 = createLogger("Logger1");
    const logger2 = createLogger("Logger2");

    logger1.info("from logger1");
    logger2.info("from logger2");

    const entries = Logger.getEntries();
    expect(entries).toHaveLength(2);
    expect(entries[0].category).toBe("Logger1");
    expect(entries[1].category).toBe("Logger2");
  });
});
