import { Crumb, PageHeader, Sep } from "../../shared/ui/PageHeader.jsx";

export function BenchmarkScoringGuide() {
  return (
    <>
      <PageHeader
        title={
          <>
            <Crumb href="#/benchmark-lab">Benchmark Lab</Crumb>
            <Sep />
            Scoring and matching
          </>
        }
      />
      <div className="content scroll-content benchmark-page benchmark-simple">
        <div className="card" style={{ maxWidth: 850, padding: 24 }}>
          <h2>How a scan is matched</h2>
          <p>
            Benchmark Lab compares a finished scan with the ground truth assigned to its site or
            API. You can also choose a ground truth file when you create the analysis. Each saved
            analysis keeps a copy of the ground truth and scan findings used at the time.
          </p>
          <p>
            An evaluation model compares every ground truth item with the scan findings. It marks
            each item as <strong>Full</strong> when the same vulnerability and affected behavior
            were found, <strong>Partial</strong> when the detection is meaningful but incomplete, or{" "}
            <strong>Missing</strong> when no scan finding is adequate. Full and partial matches must
            point to one or more findings from that scan. One scan finding can match more than one
            ground truth item.
          </p>
          <p>
            You can review an item in the analysis and change its match, linked findings, and note.
            The saved analysis and its score then use that reviewed decision.
          </p>

          <h2>How the score is calculated</h2>
          <p>
            Each Full or Partial match earns points based on the severity in the saved ground truth.
            Missing items earn no points. A Partial match earns the same points as a Full match.
          </p>
          <table className="table">
            <thead>
              <tr>
                <th>Ground truth severity</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Informational</td>
                <td>0</td>
              </tr>
              <tr>
                <td>Low</td>
                <td>1</td>
              </tr>
              <tr>
                <td>Medium</td>
                <td>2</td>
              </tr>
              <tr>
                <td>High</td>
                <td>3</td>
              </tr>
              <tr>
                <td>Critical</td>
                <td>4</td>
              </tr>
            </tbody>
          </table>
          <p>High and Critical matches earn double points when their ground truth category is:</p>
          <ul>
            <li>A01: Broken Access Control</li>
            <li>A03: Injection</li>
            <li>A04: Insecure Design</li>
            <li>A07: Identification and Authentication Failures</li>
          </ul>
          <p>
            In these categories, High scores 3 × 2 = 6 and Critical scores 4 × 2 = 8. The multiplier
            does not apply to Low, Medium, or Informational items.
          </p>
          <p>
            For example, a Full A01 High match scores 6, a Partial A03 Critical match scores 8, and
            a Full A02 High match scores 3. A Missing item scores 0. Together those items score 17.
          </p>
          <p>
            The score is the sum across ground truth items. The cost/score chart plots that total
            against the scan cost. The cost/matched findings chart instead counts Full and Partial
            items. A score is unavailable when a matched item has no usable severity, or when an
            older published result has no saved match details to recalculate it.
          </p>
        </div>
      </div>
    </>
  );
}
