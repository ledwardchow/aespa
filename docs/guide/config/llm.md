# Configuring LLMs

For AESPA to work, you need to set up a model provider. AESPA supports GitHub Copilot subscriptions, AWS Bedrock Runtime, Azure OpenAI, OpenAI-compatible, Anthropic, and other API formats.

A **Provider** is an API endpoint and a list of models which it can supply.

A **Profile** allows you to configure settings for a specific model - max tokens, temperature, whether the model has vision capability, and whether tool execution should be forced. You can select a default system-wide profile, and optionally a specific profile can be selected per scan run.

## Configuring a provider

Click on "New Provider" on the top right to create one:
![LLM Provider configuration screen](images/llmproviders.png)

Set a name for your LLM provider (it will show up in the profile creation as this name).
![alt text](images/createprovider.png)
The following providers can be selected as an API format to pre-fill the Base URL:
- GitHub Copilot subscription (no base URL is needed)
- OpenRouter (https://openrouter.ai/api/v1)
- Anthropic API (https://api.anthropic.com)
- OpenAI API (https://api.openai.com/v1)
- Google Gemini API (https://generativelanguage.googleapis.com)

The following API format selector values will require you to input your base URL:
- OpenAI-compatible API (select this if you are using a locally hosted model - i.e. Ollama, LM Studio)
- Amazon Bedrock Runtime (https://bedrock-runtime.REGIONNAME.amazonaws.com)
- Amazon Bedrock Mantle (https://bedrock-mantle.REGIONNAME.api.aws/v1 — OpenAI-compatible; leave the Base URL blank to default to us-east-2)
- Azure OpenAI (https://RESOURCENAME.openai.azure.com)
- Azure AI Foundry (OpenAI API) (https://RESOURCENAME.services.ai.azure.com/openai/v1)
- Azure AI Foundry (Anthropic API) (https://RESOURCENAME.services.ai.azure.com/anthropic/v1)

Enter model names one per line, or leave the field blank to save the model names shown in that provider's placeholder. This works for every provider format.

Most providers require an API key. GitHub Copilot is different: leave both the username and token blank to use Copilot CLI's selected default account. To use another account from Copilot CLI's `/user` list, enter its login in the username field. You can instead provide a GitHub user token for an account with Copilot access; an explicit token takes precedence over the username. The first request may download the official Copilot CLI runtime. Copilot calls count against the chosen account's Copilot usage allowance.

Use `auto` as the model name to let Copilot choose an available model. AESPA also prefills GPT-5.6 Luna, Terra, and Sol, plus Claude Sonnet 5 and Opus 4.8. Availability depends on the signed-in account's Copilot plan and organization policies. The Copilot SDK does not currently expose temperature or per-call output-token settings, so those two profile fields are not forwarded for this provider.

During a Copilot-backed scan, the Status tab shows the AI credits and model calls used by that AESPA run. Accounts that still use GitHub's older billing model show premium requests instead. Expand the usage bar to see token/cache details and the latest allowance information GitHub provided.

For Amazon Bedrock Runtime, you can provide an API key or leave it blank to use the default AWS SDK/boto3 profile installed on your machine. Amazon Bedrock Mantle is OpenAI-compatible: supply an Amazon Bedrock API key (sent as a Bearer token), or leave the key blank to authenticate with AWS credentials. AESPA drives Mantle via the OpenAI **Responses** API, so it works with the frontier `openai.gpt-5.x` models and the `openai.gpt-oss-*` models. Claude models are not available over Mantle's OpenAI APIs; use the Amazon Bedrock Runtime provider for those.

If you have a rate limit/quota on your LLM provider, enter them here and AESPA will pace LLM calls to ensure you don't exceed it. If you leave it blank, it will run as fast as it can - I've seen it consume up to ~10m TPM for a single scan in bursts. (If you have a limit and you don't fill this in, your LLM calls will fail and your scans will break. An error message will show up in the scan log if this is the case.)

## Configuring a profile

Click on **New Profile** at the top right to create a profile. 

Click on **Use** on a profile to select it as the default profile.

![LLM Profiles screen](images/llmprofiles.png)

### Create/edit profile screen

![alt text](images/createprofile.png)

The models you entered for the provider will show up in the drop down. Set the max tokens, temperature, vision and tool execution settings for your model and click Save.

Your model **must** support either Anthropic tool calling/OpenAI function calling for it to work in AESPA. There is no specific error message if you select a model that doesn't support this! Your scans may just terminate early.

Vision support is optional; tick the box to send captured screenshots to the model when pages are queried out of the context tool, this may improve feature discovery.

Note the following model restrictions:
- Haiku 4.5 supports a maximum of 64000 output tokens.
- Opus 4.8 does not support the **temperature** setting; turn it off for this model.
- Many models that aren't from OpenAI or Anthropic don't support forcing tool execution.
