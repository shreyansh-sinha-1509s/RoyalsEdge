class MemoryCache {
  constructor(defaultTtlMs = 5 * 60 * 1000) {
    this.defaultTtlMs = defaultTtlMs;
    this.store = new Map();
    this.hits = 0;
    this.misses = 0;
    this.lastClearedAt = null;
  }

  get(key) {
    const entry = this.store.get(key);
    if (!entry) {
      this.misses += 1;
      return undefined;
    }
    if (Date.now() > entry.expiresAt) {
      this.store.delete(key);
      this.misses += 1;
      return undefined;
    }
    this.hits += 1;
    return entry.value;
  }

  set(key, value, ttlMs = this.defaultTtlMs) {
    this.store.set(key, { value, expiresAt: Date.now() + ttlMs });
  }

  async getOrSet(key, factory, ttlMs = this.defaultTtlMs) {
    const cached = this.get(key);
    if (cached !== undefined) return cached;
    const value = await factory();
    this.set(key, value, ttlMs);
    return value;
  }

  clear() {
    const clearedKeys = this.store.size;
    this.store.clear();
    this.lastClearedAt = new Date().toISOString();
    return clearedKeys;
  }

  stats() {
    return {
      entries: this.store.size,
      hits: this.hits,
      misses: this.misses,
      lastClearedAt: this.lastClearedAt,
    };
  }
}

export const appCache = new MemoryCache();

