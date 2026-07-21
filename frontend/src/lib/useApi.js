import { useCallback, useEffect, useRef, useState } from "react";

export function useApi(fetcher, deps = [], { skip = false } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(!skip);
  const seq = useRef(0);

  const run = useCallback(async () => {
    const id = ++seq.current;
    setLoading(true);
    setError(null);
    try {
      const res = await fetcher();
      if (id === seq.current) setData(res);
    } catch (e) {
      if (id === seq.current) setError(e.message || "Something went wrong");
    } finally {
      if (id === seq.current) setLoading(false);
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (skip) return;
    run();
  }, [run, skip]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, error, loading, refetch: run, setData };
}

export function useAsyncAction(fn) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const act = useCallback(
    async (...args) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fn(...args);
        setData(res);
        return res;
      } catch (e) {
        setError(e.message || "Something went wrong");
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [fn]
  );

  return { act, loading, error, data, setError };
}
