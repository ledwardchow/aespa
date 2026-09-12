import { lazy } from "react";
const lazyNamed = (loader, name) =>
  lazy(() => loader().then((module) => ({ default: module[name] })));

export const routes = {
  list: {
    section: "sites",
    Component: lazyNamed(() => import("../features/sites/SitesList.jsx"), "SitesList"),
    props: () => ({}),
  },
  "site-new": {
    section: "sites",
    Component: lazyNamed(() => import("../features/sites/SiteForm.jsx"), "SiteForm"),
    props: () => ({ key: "new" }),
  },
  "site-edit": {
    section: "sites",
    Component: lazyNamed(() => import("../features/sites/SiteForm.jsx"), "SiteForm"),
    props: (route) => ({ key: route.id, siteId: route.id }),
  },
  "site-detail": {
    section: "sites",
    Component: lazyNamed(() => import("../features/sites/SiteDetail.jsx"), "SiteDetail"),
    props: (route) => ({ key: route.id, siteId: route.id }),
  },
  "api-list": {
    section: "apis",
    Component: lazyNamed(
      () => import("../features/api-collections/ApiCollectionsList.jsx"),
      "ApiCollectionsList",
    ),
    props: () => ({}),
  },
  "api-new": {
    section: "apis",
    Component: lazyNamed(
      () => import("../features/api-collections/ApiCollectionForm.jsx"),
      "ApiCollectionForm",
    ),
    props: () => ({ key: "api-new" }),
  },
  "api-edit": {
    section: "apis",
    Component: lazyNamed(
      () => import("../features/api-collections/ApiCollectionForm.jsx"),
      "ApiCollectionForm",
    ),
    props: (route) => ({ key: route.id, collectionId: route.id }),
  },
  "api-detail": {
    section: "apis",
    Component: lazyNamed(
      () => import("../features/api-collections/ApiCollectionDetail.jsx"),
      "ApiCollectionDetail",
    ),
    props: (route) => ({ key: route.id, collectionId: route.id, initialTab: route.tab }),
  },
  "api-files": {
    section: "apis",
    Component: lazyNamed(
      () => import("../features/api-collections/ApiFilesManager.jsx"),
      "ApiFilesManager",
    ),
    props: (route) => ({ key: route.id, collectionId: route.id }),
  },
  "api-run-new": {
    section: "apis",
    Component: lazyNamed(() => import("../features/api-runs/ApiTestRunForm.jsx"), "ApiTestRunForm"),
    props: (route) => ({ key: route.id, collectionId: route.id }),
  },
  "api-run-detail": {
    section: "apis",
    Component: lazyNamed(
      () => import("../features/api-runs/ApiTestRunDetail.jsx"),
      "ApiTestRunDetail",
    ),
    props: (route) => ({
      key: route.id,
      runId: route.id,
      initialTab: route.tab,
      initialFindingRef: route.findingRef,
      initialTrafficCoverage: route.trafficCoverage,
    }),
  },
  "sast-list": {
    section: "sast",
    Component: lazyNamed(
      () => import("../features/sast-runs/SastRunsListPage.jsx"),
      "SastRunsListPage",
    ),
    props: () => ({}),
  },
  "sast-run-new": {
    section: "sast",
    Component: lazyNamed(() => import("../features/sast-runs/SastRunForm.jsx"), "SastRunForm"),
    props: () => ({ key: "sast-new" }),
  },
  "sast-run-detail": {
    section: "sast",
    Component: lazyNamed(
      () => import("../features/sast-runs/SastRunDetail.jsx"),
      "SastRunDetailExperience",
    ),
    props: (route) => ({
      key: route.id,
      runId: route.id,
      initialTab: route.tab,
      initialLeadRef: route.leadRef,
    }),
  },
  "app-list": {
    section: "applications",
    Component: lazyNamed(
      () => import("../features/applications/ApplicationsList.jsx"),
      "ApplicationsList",
    ),
    props: () => ({}),
  },
  "app-new": {
    section: "applications",
    Component: lazyNamed(
      () => import("../features/applications/ApplicationForm.jsx"),
      "ApplicationForm",
    ),
    props: () => ({ key: "app-new" }),
  },
  "app-edit": {
    section: "applications",
    Component: lazyNamed(
      () => import("../features/applications/ApplicationForm.jsx"),
      "ApplicationForm",
    ),
    props: (route) => ({ key: route.id, applicationId: route.id }),
  },
  "app-detail": {
    section: "applications",
    Component: lazyNamed(
      () => import("../features/applications/ApplicationDetail.jsx"),
      "ApplicationDetail",
    ),
    props: (route) => ({ key: route.id, applicationId: route.id, initialTab: route.tab }),
  },
  "campaign-new": {
    section: "applications",
    Component: lazyNamed(
      () => import("../features/campaigns/CampaignNewForm.jsx"),
      "CampaignNewForm",
    ),
    props: (route) => ({ key: route.id, applicationId: route.id }),
  },
  "campaign-detail": {
    section: "applications",
    Component: lazyNamed(
      () => import("../features/campaigns/CampaignDetail.jsx"),
      "CampaignDetail",
    ),
    props: (route) => ({
      key: `${route.id}-${route.campaignId}`,
      applicationId: route.id,
      campaignId: route.campaignId,
      initialTab: route.tab,
      initialFindingRef: route.findingRef,
    }),
  },
  "active-jobs": {
    section: "active-jobs",
    Component: lazyNamed(() => import("../features/active-jobs/ActiveJobs.jsx"), "ActiveJobsPage"),
    props: () => ({}),
  },
  stats: {
    section: "stats",
    Component: lazyNamed(() => import("../features/statistics/Statistics.jsx"), "StatisticsPage"),
    props: () => ({}),
  },
  "run-new": {
    section: "sites",
    Component: lazyNamed(() => import("../features/sites/TestRunForm.jsx"), "TestRunForm"),
    props: (route) => ({ key: route.siteId, siteId: route.siteId }),
  },
  "run-detail": {
    section: "sites",
    Component: lazyNamed(() => import("../features/web-runs/TestRunDetail.jsx"), "TestRunDetail"),
    props: (route, preferences) => ({
      key: route.id,
      runId: route.id,
      showDeepScan: preferences.showDeepScan,
      initialTab: route.tab,
      initialFindingRef: route.findingRef,
      initialLeadRef: route.leadRef,
      initialTrafficCoverage: route.trafficCoverage,
    }),
  },
  settings: {
    section: "settings",
    Component: lazyNamed(() => import("../features/settings/SettingsPage.jsx"), "SettingsPage"),
    props: () => ({}),
  },
  "scan-policy": {
    section: "scan-policy",
    Component: lazyNamed(() => import("../features/settings/ScanPolicyPage.jsx"), "ScanPolicyPage"),
    props: (_route, preferences) => ({ showDeepScan: preferences.showDeepScan }),
  },
  "external-integrations": {
    section: "external-integrations",
    Component: lazyNamed(
      () => import("../features/settings/ExternalIntegrationsPage.jsx"),
      "ExternalIntegrationsPage",
    ),
    props: () => ({}),
  },
  debug: {
    section: "debug",
    Component: lazyNamed(() => import("../features/settings/DebugPage.jsx"), "DebugPage"),
    props: (_route, preferences) => ({
      showUsername: preferences.showUsername,
      setShowUsername: preferences.setShowUsername,
      showApplications: preferences.showApplications,
      setShowApplications: preferences.setShowApplications,
      showDeepScan: preferences.showDeepScan,
      setShowDeepScan: preferences.setShowDeepScan,
      username: preferences.username,
      reportingDebugCfg: preferences.reportingDebugCfg,
      setReportingDebugCfg: preferences.setReportingDebugCfg,
      benchmarkLabCfg: preferences.benchmarkLabCfg,
      setBenchmarkLabCfg: preferences.setBenchmarkLabCfg,
    }),
  },
  "reporting-debug": {
    section: "reporting-debug",
    Component: lazyNamed(
      () => import("../features/settings/ReportingDebugPage.jsx"),
      "ReportingDebugPage",
    ),
    props: () => ({}),
  },
  "benchmark-lab": {
    section: "benchmark-lab",
    Component: lazyNamed(
      () => import("../features/benchmark-lab/BenchmarkLabPage.jsx"),
      "BenchmarkLabPage",
    ),
    props: () => ({}),
  },
  "benchmark-evaluation-new": {
    section: "benchmark-lab",
    Component: lazyNamed(
      () => import("../features/benchmark-lab/BenchmarkEvaluationForm.jsx"),
      "BenchmarkEvaluationForm",
    ),
    props: () => ({ key: "new" }),
  },
  "benchmark-evaluation-detail": {
    section: "benchmark-lab",
    Component: lazyNamed(
      () => import("../features/benchmark-lab/BenchmarkEvaluationDetail.jsx"),
      "BenchmarkEvaluationDetail",
    ),
    props: (route) => ({ key: route.id, evaluationId: route.id, initialTab: route.tab }),
  },
  "benchmark-comparison-detail": {
    section: "benchmark-lab",
    Component: lazyNamed(
      () => import("../features/benchmark-lab/BenchmarkComparisonDetail.jsx"),
      "BenchmarkComparisonDetail",
    ),
    props: (route) => ({ key: route.id, comparisonId: route.id }),
  },
  "alice-popout": {
    section: "alice-popout",
    Component: lazyNamed(
      () => import("../features/web-runs/AliceChatPopout.jsx"),
      "AliceChatPopout",
    ),
    props: (route) => ({ runId: route.id }),
  },
};
