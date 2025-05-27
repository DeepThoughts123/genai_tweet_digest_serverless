import '@testing-library/jest-dom'

// Mock Headers API for fetch responses in tests
// @ts-expect-error - We're providing a test implementation
global.Headers = class Headers {
  private headers: Map<string, string>;

  constructor(init?: Record<string, string> | [string, string][] | Headers) {
    this.headers = new Map();
    if (init) {
      if (init instanceof Headers) {
        init.forEach((value, key) => {
          this.headers.set(key.toLowerCase(), value);
        });
      } else if (Array.isArray(init)) {
        init.forEach(([key, value]) => {
          this.headers.set(key.toLowerCase(), value);
        });
      } else {
        Object.entries(init).forEach(([key, value]) => {
          this.headers.set(key.toLowerCase(), value);
        });
      }
    }
  }

  append(name: string, value: string): void {
    this.headers.set(name.toLowerCase(), value);
  }

  delete(name: string): void {
    this.headers.delete(name.toLowerCase());
  }

  get(name: string): string | null {
    return this.headers.get(name.toLowerCase()) || null;
  }

  has(name: string): boolean {
    return this.headers.has(name.toLowerCase());
  }

  set(name: string, value: string): void {
    this.headers.set(name.toLowerCase(), value);
  }

  forEach(callback: (value: string, key: string) => void): void {
    this.headers.forEach(callback);
  }

  entries(): IterableIterator<[string, string]> {
    return this.headers.entries();
  }

  keys(): IterableIterator<string> {
    return this.headers.keys();
  }

  values(): IterableIterator<string> {
    return this.headers.values();
  }

  [Symbol.iterator](): IterableIterator<[string, string]> {
    return this.headers.entries();
  }
};

// Ensure proper Response object with Headers
// @ts-expect-error - We're providing a test implementation  
global.Response = class Response {
  ok: boolean;
  status: number;
  headers: Headers;
  private _body: unknown;

  constructor(body?: unknown, init?: { status?: number; headers?: Record<string, string> }) {
    this._body = body;
    this.status = init?.status || 200;
    this.ok = this.status >= 200 && this.status < 300;
    this.headers = new Headers(init?.headers);
  }

  async json(): Promise<unknown> {
    return typeof this._body === 'string' ? JSON.parse(this._body) : this._body;
  }

  async text(): Promise<string> {
    return typeof this._body === 'string' ? this._body : JSON.stringify(this._body);
  }
}; 