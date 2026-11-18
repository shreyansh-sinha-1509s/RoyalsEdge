import { useCallback, useEffect, useState } from 'react';

/**
 * Reusable data-fetching hook with cancellation, loading, error, and manual retry.
 */
export function useApiQuery(queryFn, deps = [], { enabled = true } = {}) {
  const [data, setData] = useState(null);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(Boolean(enabled));
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return undefined;
    }
    const controller = new AbortController();
    let active = true;
    setLoading(true);
    setError(null);

    Promise.resolve(queryFn(controller.signal))
      .then((res) => {
        if (!active) return;
        setData(res?.data ?? null);
        setMeta(res?.meta ?? null);
        setLoading(false);
      })
      .catch((err) => {
        if (!active || err?.name === 'AbortError') return;
        setError(err);
        setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, tick]);

  return { data, meta, loading, error, refetch };
}

