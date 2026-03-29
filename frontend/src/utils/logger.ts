type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  category: string;
  message: string;
  data?: Record<string, unknown>;
}

class Logger {
  private category: string;
  private static entries: LogEntry[] = [];
  private static maxEntries = 1000;

  constructor(category: string) {
    this.category = category;
  }

  private log(level: LogLevel, message: string, data?: Record<string, unknown>) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      category: this.category,
      message,
      data,
    };

    Logger.entries.push(entry);
    if (Logger.entries.length > Logger.maxEntries) {
      Logger.entries = Logger.entries.slice(-Logger.maxEntries);
    }

    const prefix = `[${entry.timestamp}] [${level.toUpperCase()}] [${this.category}]`;
    switch (level) {
      case 'debug':
        console.debug(prefix, message, data ?? '');
        break;
      case 'info':
        console.info(prefix, message, data ?? '');
        break;
      case 'warn':
        console.warn(prefix, message, data ?? '');
        break;
      case 'error':
        console.error(prefix, message, data ?? '');
        break;
    }
  }

  debug(message: string, data?: Record<string, unknown>) { this.log('debug', message, data); }
  info(message: string, data?: Record<string, unknown>) { this.log('info', message, data); }
  warn(message: string, data?: Record<string, unknown>) { this.log('warn', message, data); }
  error(message: string, data?: Record<string, unknown>) { this.log('error', message, data); }

  static getEntries(): LogEntry[] { return [...Logger.entries]; }
  static clear() { Logger.entries = []; }
}

export function createLogger(category: string): Logger {
  return new Logger(category);
}

export { Logger };
export type { LogEntry, LogLevel };
