import { useRef } from "react";
import type { ChangeEvent } from "react";
export function FindingFileControls({
  hasFindings,
  onExport,
  onImport,
}: {
  hasFindings: boolean;
  onExport: () => void;
  onImport: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <>
      {hasFindings && (
        <button className="btn secondary sm" onClick={onExport}>
          Export findings
        </button>
      )}
      <button className="btn secondary sm" onClick={() => input.current?.click()}>
        Import findings
      </button>
      <input
        ref={input}
        type="file"
        accept=".md,text/markdown,text/plain"
        hidden
        onChange={onImport}
      />
    </>
  );
}
