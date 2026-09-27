import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { jsonListValue, SastLeadDetails } from "./SastLeadDetails.jsx";

test("restores proof gaps split into characters before a validator failure", () => {
  const originalGap = "Confirm whether the search parameter reaches the raw SQL query.";
  const failureGap = "Independent validator failed before closing this candidate.";

  render(
    <SastLeadDetails
      lead={{
        proof_gaps_json: JSON.stringify([...originalGap, failureGap]),
      }}
    />,
  );

  const proofGaps = screen.getByText("Proof gaps").parentElement;
  expect(proofGaps.querySelector("pre").textContent).toBe(`${originalGap}\n\n${failureGap}`);
  expect(jsonListValue(JSON.stringify([...originalGap, failureGap]))).toHaveLength(2);
});

test("keeps ordinary proof gap lists intact", () => {
  render(
    <SastLeadDetails
      lead={{ proof_gaps_json: JSON.stringify(["Missing route proof", "No live test"]) }}
    />,
  );

  expect(screen.getByText("Proof gaps").parentElement.querySelector("pre").textContent).toBe(
    "Missing route proof\n\nNo live test",
  );
});
