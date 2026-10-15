import { useEffect, useState } from "react";

// Loads a parent record only to show its name in a breadcrumb. Failures fall
// back to null so the caller can show a generic label instead.
export function useRecordName(
  load: (id: number) => Promise<{ name?: string | null } | null | undefined>,
  id: number | null | undefined,
): string | null {
  const [name, setName] = useState<string | null>(null);
  useEffect(() => {
    if (id === null || id === undefined) return undefined;
    let cancelled = false;
    load(id)
      .then((record) => {
        if (!cancelled) setName(record?.name || null);
      })
      .catch(() => {
        if (!cancelled) setName(null);
      });
    return () => {
      cancelled = true;
    };
  }, [load, id]);
  return name;
}
