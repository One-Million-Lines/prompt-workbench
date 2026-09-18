import { useEffect, useRef, useState } from 'react';

/** Returns a debounced copy of `value`, updated after `delayMs` of stability. */
export function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

/**
 * Returns a stable debounced callback. The latest callback ref is always used,
 * so it is safe to pass inline functions.
 */
export function useDebouncedCallback<A extends unknown[]>(
  fn: (...args: A) => void,
  delayMs: number,
): (...args: A) => void {
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const timer = useRef<number | undefined>(undefined);

  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
    },
    [],
  );

  return (...args: A) => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => fnRef.current(...args), delayMs);
  };
}
