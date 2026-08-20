import assert from "node:assert/strict";
import test from "node:test";

import { bedrockBaseUrl, bedrockRegionFromBaseUrl } from "./bedrock.js";

test("Bedrock Runtime defaults to Sydney and builds its fixed endpoint", () => {
  assert.equal(bedrockRegionFromBaseUrl("bedrock", null), "ap-southeast-2");
  assert.equal(
    bedrockBaseUrl("bedrock", "ap-southeast-2"),
    "https://bedrock-runtime.ap-southeast-2.amazonaws.com"
  );
});

test("Bedrock Mantle derives the selected region and fixed host", () => {
  const baseUrl = "https://bedrock-mantle.eu-west-1.api.aws/openai/v1";

  assert.equal(bedrockRegionFromBaseUrl("bedrock_mantle", baseUrl), "eu-west-1");
  assert.equal(
    bedrockBaseUrl("bedrock_mantle", "eu-west-1"),
    "https://bedrock-mantle.eu-west-1.api.aws"
  );
});
