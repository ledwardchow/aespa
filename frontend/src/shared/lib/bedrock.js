export const BEDROCK_DEFAULT_REGIONS = {
  bedrock: "ap-southeast-2",
  bedrock_mantle: "us-east-2",
};

export const BEDROCK_REGIONS = {
  bedrock: [
    ["us-east-2", "US East (Ohio)"],
    ["us-east-1", "US East (N. Virginia)"],
    ["us-west-2", "US West (Oregon)"],
    ["ap-south-2", "Asia Pacific (Hyderabad)"],
    ["ap-south-1", "Asia Pacific (Mumbai)"],
    ["ap-northeast-3", "Asia Pacific (Osaka)"],
    ["ap-northeast-2", "Asia Pacific (Seoul)"],
    ["ap-southeast-1", "Asia Pacific (Singapore)"],
    ["ap-southeast-2", "Asia Pacific (Sydney)"],
    ["ap-northeast-1", "Asia Pacific (Tokyo)"],
    ["ca-central-1", "Canada (Central)"],
    ["eu-central-1", "Europe (Frankfurt)"],
    ["eu-west-1", "Europe (Ireland)"],
    ["eu-west-2", "Europe (London)"],
    ["eu-south-1", "Europe (Milan)"],
    ["eu-west-3", "Europe (Paris)"],
    ["eu-south-2", "Europe (Spain)"],
    ["eu-north-1", "Europe (Stockholm)"],
    ["eu-central-2", "Europe (Zurich)"],
    ["sa-east-1", "South America (São Paulo)"],
    ["us-gov-east-1", "AWS GovCloud (US-East)"],
    ["us-gov-west-1", "AWS GovCloud (US-West)"],
  ],
  bedrock_mantle: [
    ["us-east-2", "US East (Ohio)"],
    ["us-east-1", "US East (N. Virginia)"],
    ["us-west-2", "US West (Oregon)"],
    ["ap-southeast-3", "Asia Pacific (Jakarta)"],
    ["ap-south-1", "Asia Pacific (Mumbai)"],
    ["ap-southeast-2", "Asia Pacific (Sydney)"],
    ["ap-northeast-1", "Asia Pacific (Tokyo)"],
    ["eu-central-1", "Europe (Frankfurt)"],
    ["eu-west-1", "Europe (Ireland)"],
    ["eu-west-2", "Europe (London)"],
    ["eu-south-1", "Europe (Milan)"],
    ["eu-north-1", "Europe (Stockholm)"],
    ["sa-east-1", "South America (São Paulo)"],
    ["us-gov-west-1", "AWS GovCloud (US-West)"],
  ],
};

export function isBedrockProvider(apiFormat) {
  return apiFormat === "bedrock" || apiFormat === "bedrock_mantle";
}

export function bedrockRegionFromBaseUrl(apiFormat, baseUrl) {
  const endpointName = apiFormat === "bedrock_mantle" ? "bedrock-mantle" : "bedrock-runtime";
  const match = String(baseUrl || "").match(new RegExp(`${endpointName}\\.([a-z0-9-]+)\\.`));
  return match?.[1] || BEDROCK_DEFAULT_REGIONS[apiFormat];
}

export function bedrockBaseUrl(apiFormat, region) {
  const selectedRegion = region || BEDROCK_DEFAULT_REGIONS[apiFormat];
  return apiFormat === "bedrock_mantle"
    ? `https://bedrock-mantle.${selectedRegion}.api.aws`
    : `https://bedrock-runtime.${selectedRegion}.amazonaws.com`;
}
