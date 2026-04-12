import { useState, useEffect, useRef } from "react";

const cache = new Map<string, string>();

/**
 * Fetch and cache a markdown file from public/docs/.
 * Returns { content, loading, error }.
 */
export function useMarkdown(path: string) {
  const [content, setContent] = useState<string | null>(() => cache.get(path) ?? null);
  const [loading, setLoading] = useState(!cache.has(path));
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (cache.has(path)) {
      setContent(cache.get(path)!);
      setLoading(false);
      setError(null);
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);

    fetch(path, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
        return res.text();
      })
      .then((text) => {
        cache.set(path, text);
        setContent(text);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [path]);

  return { content, loading, error };
}
