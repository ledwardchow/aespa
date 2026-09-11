import { createContext, useContext, useState } from "react";

const FindingsData = createContext(null);

// Shared server data outlives tab navigation. Editing state belongs to the panel.
export function FindingsDataProvider({ children }) {
  const [findings, setFindings] = useState([]);
  const [validateStatus, setValidateStatus] = useState(null);
  const [validateBusy, setValidateBusy] = useState(false);
  return (
    <FindingsData.Provider
      value={{
        findings,
        setFindings,
        validateStatus,
        setValidateStatus,
        validateBusy,
        setValidateBusy,
      }}
    >
      {children}
    </FindingsData.Provider>
  );
}

export function useFindingsData() {
  const value = useContext(FindingsData);
  if (!value) throw new Error("Findings data requires a run provider");
  return value;
}
