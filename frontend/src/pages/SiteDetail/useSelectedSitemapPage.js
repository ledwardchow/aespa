import { useEffect, useState } from "react";
import { api } from "../../lib/api";

/** Loads the detail and per-user views for the sitemap node currently selected. */
export function useSelectedSitemapPage(runId) {
  const [selectedNode, setSelectedNode] = useState(null);
  const [pageDetail, setPageDetail] = useState(null);
  const [pageViews, setPageViews] = useState([]);

  useEffect(() => {
    if (!selectedNode) {
      setPageDetail(null);
      setPageViews([]);
      return;
    }

    let cancelled = false;
    const pageId = selectedNode.id;
    setPageDetail(null);
    setPageViews([]);
    api.getPage(runId, pageId).then(detail => {
      if (!cancelled && selectedNode.id === pageId) setPageDetail(detail);
    }).catch(() => {});
    api.getPageViews(runId, pageId).then(views => {
      if (!cancelled && selectedNode.id === pageId) setPageViews(views);
    }).catch(() => {
      if (!cancelled) setPageViews([]);
    });
    return () => {
      cancelled = true;
    };
  }, [runId, selectedNode]);

  return { selectedNode, setSelectedNode, pageDetail, pageViews };
}
