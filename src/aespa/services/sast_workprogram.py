"""Deterministic, framework-neutral SAST attack-surface and work-program state."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, insert, update
from sqlmodel import Session, select

from aespa.db import get_engine
from aespa.models import (
    SastCodeCall,
    SastCodeSymbol,
    SastCoverageObligation,
    SastDiscoveryTelemetry,
    SastEvidenceReceipt,
    SastObligationLead,
    SastPartition,
    SastSourceFile,
    SastSurfaceEdge,
    SastSurfaceItem,
    SastThreatModel,
    SastThreatScenario,
    SastWorker,
    SastWorkItem,
)
from aespa.services import sast_codegraph

_UTC = timezone.utc
CLASS_GROUPS = ("injection", "access", "logic")
TERMINAL_WORK_STATUSES = {
    "safe",
    "no_match",
    "candidate",
    "design_intent",
    "not_applicable",
}
_MAX_ATLAS_FILE_BYTES = 1_000_000
_MAX_SURFACE_ITEMS = 12_000
_PARTITION_INPUT_LIMIT = 12
_SINK_WORK_LIMIT = 40
_HELPER_SINK_CLAIM_LIMIT = 12

_LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".vb": "Visual Basic",
    ".cshtml": "Razor",
    ".razor": "Razor",
    ".aspx": "ASP.NET Web Forms",
    ".ascx": "ASP.NET Web Forms",
    ".ashx": "ASP.NET Web Forms",
    ".asmx": "ASP.NET Web Forms",
    ".c": "C/C++",
    ".cc": "C/C++",
    ".cpp": "C/C++",
    ".h": "C/C++",
    ".hpp": "C/C++",
    ".rs": "Rust",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sql": "SQL",
    ".html": "HTML",
    ".htm": "HTML",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".graphql": "GraphQL",
    ".proto": "Protocol Buffers",
    ".yaml": "Configuration",
    ".yml": "Configuration",
    ".json": "Configuration",
    ".toml": "Configuration",
    ".xml": "Configuration",
    ".config": "Configuration",
    ".csproj": "Configuration",
    ".props": "Configuration",
}
_SOURCE_LANGUAGES = {
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "Kotlin",
    "Go",
    "Ruby",
    "PHP",
    "C#",
    "Visual Basic",
    "Razor",
    "ASP.NET Web Forms",
    "C/C++",
    "Rust",
    "Swift",
    "Scala",
    "HTML",
    "Vue",
    "Svelte",
    "Protocol Buffers",
}
_EXCLUDED_PARTS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "vendors",
    "third_party",
    "third-party",
    "external",
    "deps",
    "dist",
    "build",
    "coverage",
    "target",
    "__pycache__",
    ".venv",
    "venv",
}
_TEST_PARTS = {"test", "tests", "spec", "specs", "__tests__", "fixtures"}
_GENERATED_PARTS = {"generated", "gen", "autogen", "codegen"}
_ASSET_SUFFIXES = {
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".map",
    ".min.js",
    ".min.css",
}
_DOC_SUFFIXES = {".md", ".rst", ".txt", ".adoc"}
# Sinks that are function calls. In files the parser understands, these only
# count when the match is inside a real call, not in a comment or plain string.
# Serialization and deserialization stay line-based: definitions such as
# `toPublic()` or Java's `readObject()` are review points too.
_CALL_SINKS = {
    "Database query",
    "Command execution",
    "Filesystem operation",
    "Outbound request",
    "Code or template evaluation",
    "Sensitive logging",
}
# Scope-review items that are not tied to a line of code.
_SYNTHETIC_CATEGORIES = {
    "handler_review",
    "inferred_handler",
    "repository_surface",
    "no_input_entrypoint",
}
_CODE_GRAPH_BATCH = 5_000


@dataclass(frozen=True)
class _Pattern:
    kind: str
    category: str
    name: str
    regex: re.Pattern[str]


def _rx(value: str) -> re.Pattern[str]:
    return re.compile(value, re.IGNORECASE)


def _rx_exact(value: str) -> re.Pattern[str]:
    """Match case-sensitively, for call names whose case identifies the API."""
    return re.compile(value)


# Excludes method calls such as `$stmt->fetch(`, `regex.exec(` and
# `el.classList.remove(`, which share names with dangerous free functions.
_FREE_CALL = r"(?<![\w.$>:])"


_PATTERNS = (
    _Pattern(
        "entrypoint",
        "http",
        "HTTP route registration",
        _rx(
            r"(?:\baddRoute\s*\(|\bRoute::(?:get|post|put|patch|delete|any|match|resource)\s*\(|^\s*(?:path|re_path)\s*\()"
        ),
    ),
    _Pattern(
        "entrypoint",
        "http",
        "HTTP route",
        _rx(
            r"(?:@\w+\.(?:get|post|put|patch|delete|route)|\b(?:app|router|server)\.(?:get|post|put|patch|delete|use)\s*\()"
            r"|\.Map(?:Get|Post|Put|Patch|Delete|Methods|Fallback|Hub|Grpc(?:Service)?)\b\s*(?:<[^>]*>)?\s*\("
        ),
    ),
    _Pattern(
        "entrypoint",
        "http",
        "Annotated HTTP handler",
        _rx(
            r"@(?:RequestMapping|GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping|Path)\b"
            r"|\[\s*(?:Http(?:Get|Post|Put|Patch|Delete|Head|Options)|Route|AcceptVerbs|WebMethod)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "http",
        "HTTP handler registration",
        _rx(
            r"\b(?:HandleFunc|handle\s*\(|add_route|register_route|register_rest_route)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "http",
        "Razor page handler",
        _rx_exact(
            r"\bpublic\s+(?:async\s+)?[\w<>\[\],?\s]*?(?<![.\w])On(?:Get|Post|Put|Patch|Delete)\w*\s*\("
            r"|^\s*@page\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "rpc",
        "RPC service method",
        _rx(r"\b(?:grpc|thrift|rpc)\b.*\b(?:handler|service|method|server)\b"),
    ),
    _Pattern(
        "entrypoint",
        "queue",
        "Message consumer",
        _rx(
            r"\b(?:consumer|subscribe|on_message|message_handler|KafkaListener|SqsListener|RabbitListener|IConsumer|ServiceBusProcessor)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "websocket",
        "WebSocket handler",
        _rx(r"\b(?:websocket|WebSocket|socket\.on|onmessage)\b|:\s*Hub\b"),
    ),
    _Pattern(
        "entrypoint",
        "cli",
        "CLI command",
        _rx(
            r"\b(?:argparse|add_argument|process\.argv|cobra\.Command|flag\.(?:String|Int|Bool)|CommandLine\.Command)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "serverless",
        "Serverless handler",
        _rx(
            r"\b(?:lambda_handler|APIGatewayProxyHandler|CloudFunction|FunctionsFramework|event\.Records|HttpTrigger|ServiceBusTrigger|QueueTrigger|FunctionName)\b"
        ),
    ),
    _Pattern(
        "entrypoint",
        "file",
        "File processor",
        _rx(r"\b(?:multipart|upload|FileUpload|watchdog|fs\.watch|inotify)\b"),
    ),
    _Pattern(
        "entrypoint",
        "job",
        "Scheduled job",
        _rx(r"\b(?:cron|schedule|Scheduled|Celery|sidekiq|background_job)\b"),
    ),
    _Pattern(
        "input",
        "request",
        "Request value",
        _rx(
            r"\b(?:req\.(?:params|query|body|headers|cookies)|request\.(?:args|form|json|headers|cookies|files)|r\.(?:URL\.Query|FormValue|Header\.Get)|RequestParam|PathVariable|RequestBody)\b"
        ),
    ),
    _Pattern(
        "input",
        "request",
        ".NET request value",
        _rx_exact(
            r"\[\s*From(?:Body|Query|Route|Form|Header)\b|\[\s*BindProperty\b"
            r"|\bRequest\.(?:Query|QueryString|Form|Headers|Cookies|Body|BodyReader|RouteValues|Params|Path|Files|InputStream|ServerVariables)\b"
            r"|\bRequest\s*\[|\bIFormFile\b|\bIFormCollection\b|\bHttpPostedFile\w*\b"
        ),
    ),
    _Pattern(
        "input",
        "request",
        "PHP request value",
        _rx(
            r"(?:\$_(?:GET|POST|REQUEST|FILES|COOKIE|SERVER)\b|php://input|\bRequest::(?:input|all|query|post|header)\s*\()"
        ),
    ),
    _Pattern(
        "input",
        "event",
        "Event or message value",
        _rx(
            r"\b(?:event|message|record|payload)\.(?:body|data|value|headers|attributes|Records)\b"
        ),
    ),
    _Pattern(
        "input",
        "cli",
        "CLI input",
        _rx(
            r"\b(?:process\.argv|sys\.argv|add_argument|flag\.(?:String|Int|Bool)|stdin)\b"
        ),
    ),
    _Pattern(
        "input",
        "config",
        "Runtime configuration",
        _rx(
            r"\b(?:getenv|environ\[|process\.env|System\.getenv|Environment\.GetEnvironmentVariable|GetConnectionString)\b"
        ),
    ),
    _Pattern(
        "input",
        "file",
        "Uploaded or external file",
        _rx(
            r"\b(?:filename|originalname|content_type|mimetype|multipart|UploadedFile|FileStorage)\b"
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Database query",
        _rx(
            r"\b(?:execute|executemany|rawQuery|createQuery|query|prepareStatement|\$wpdb->query)\s*\("
            r"|->exec\s*\("
            r"|\b(?:Sql|OleDb|Odbc|Npgsql|MySql|Sqlite|Oracle)Command\b"
            r"|\bExecute(?:Reader|NonQuery|Scalar)(?:Async)?\s*\("
            r"|\b(?:FromSql(?:Raw|Interpolated)?|ExecuteSql(?:Raw|Interpolated)?(?:Async)?|SqlQuery(?:Raw)?)\s*(?:<[^>]*>)?\s*\("
            r"|\b(?:Query|Execute)(?:Async|First\w*|Single\w*|Multiple\w*)?\s*<[^>]*>\s*\("
            r"|\b(?:Query|Execute)(?:Async|First\w*|Single\w*|Multiple\w*)\s*\("
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Command execution",
        _rx_exact(
            _FREE_CALL
            + r"(?:system|popen|proc_open|shell_exec|passthru|exec|execFile|execFileSync|execSync|spawn|spawnSync|pcntl_exec)\s*\("
            r"|\b(?:os\.(?:system|popen|exec\w*|spawn\w*)|child_process\.\w+)\s*\("
            r"|\bsubprocess\.\w+|\brequire\(\s*['\"](?:node:)?child_process['\"]\s*\)"
            r"|\bProcessBuilder\b|\bRuntime\.getRuntime\(\)\.exec|\bCommand::new\b|\bexec\.Command(?:Context)?\s*\("
            r"|\bProcess\.Start\s*\(|\bProcessStartInfo\b"
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Filesystem operation",
        _rx_exact(
            _FREE_CALL
            + r"(?:open|fopen|file_get_contents|file_put_contents|readfile|unlink|rmdir|mkdir|rename|copy|move_uploaded_file|tempnam|sendFile|send_file)\s*\("
            r"(?!\s*['\"]php://input)"
            r"|\b(?:include|require)(?:_once)?\s*\(?\s*\$"
            r"|\bfs(?:\.promises)?\.\w+\s*\(|\b(?:os|shutil)\.(?:remove|unlink|rename|rmdir|removedirs|makedirs|mkdir|rmtree|copy\w*|move)\s*\("
            r"|\bos\.(?:Open|OpenFile|Create|ReadFile|WriteFile|Remove|RemoveAll)\s*\(|\bioutil\.\w*File\s*\("
            r"|\bFile(?:InputStream|OutputStream|Reader|Writer)\b|\b(?:Path\.of|Paths\.get|Files\.\w+)\s*\("
            r"|\bFile\.(?:Open|ReadAll\w*|WriteAll\w*|Delete|Copy|Move)\w*\s*\(|\bres\.(?:sendFile|download)\s*\("
            r"|\bStorage::\w+\s*\("
            r"|\bFile\.(?:Create|Append\w*|ReadLines|Exists)\w*\s*\(|\bDirectory\.\w+\s*\(|\bnew\s+(?:FileStream|StreamReader|StreamWriter|FileInfo|DirectoryInfo)\s*\("
            r"|\bPath\.Combine\s*\(|\b(?:PhysicalFile|VirtualFile)\s*\(|\bServer\.MapPath\s*\(|\bZipFile\.ExtractToDirectory\s*\(|\.ExtractToFile\s*\("
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Outbound request",
        _rx_exact(
            _FREE_CALL + r"fetch\s*\(|\b(?:window|globalThis)\.fetch\s*\(|\baxios\b"
            r"|\brequests\.(?:get|post|put|patch|delete|head|request)\s*\(|\bhttpx\.|\burllib\.request\b|\burlopen\s*\("
            r"|\bcurl_(?:init|exec|setopt)\s*\(|\bhttps?\.(?:request|get)\s*\(|\bhttp\.(?:Get|Post|PostForm|Head|NewRequest\w*)\s*\("
            r"|\b(?:HttpClient|RestTemplate|WebClient|OkHttpClient|XMLHttpRequest|GuzzleHttp|Guzzle)\b|\bwp_remote_\w+\s*\("
            r"|\bHttp::(?:get|post|put|patch|delete|send)\s*\("
            r"|\bfile_get_contents\s*\(\s*\$|\bfsockopen\s*\("
            r"|\b(?:WebRequest|HttpWebRequest)\.Create\w*\s*\(|\bRestClient\b|\bIHttpClientFactory\b"
            r"|\.(?:GetAsync|PostAsync|PutAsync|PatchAsync|DeleteAsync|SendAsync|GetStringAsync|GetStreamAsync|GetByteArrayAsync|PostAsJsonAsync|PutAsJsonAsync|GetFromJsonAsync|DownloadString\w*|DownloadData\w*|DownloadFile\w*|UploadString\w*)\s*\("
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "Code or template evaluation",
        _rx_exact(
            _FREE_CALL
            + r"(?:eval|exec|compile|create_function|assert)\s*\(|\bnew\s+Function\s*\(|"
            + _FREE_CALL
            + r"Function\s*\(|\b(?:setTimeout|setInterval)\s*\(\s*['\"`]"
            r"|\bvm\.(?:runIn\w*Context|Script)\b|\brender_template_string\s*\(|\bTemplate\s*\("
            r"|\b(?:ScriptEngine\w*|ScriptingEngine|SpelExpressionParser|OgnlUtil)\b|\bpreg_replace\s*\(\s*['\"].*/e['\"]"
            r"|\bCSharpScript\.\w+\s*\(|\bCSharpCodeProvider\b|\bCompileAssemblyFrom\w+\s*\(|\bRazor(?:Engine)?\.(?:Parse|Compile\w*|RunCompile)\s*\("
            r"|\bEngine\.Razor\.\w+\s*\(|\bAssembly\.Load(?:From|File)?\s*\(|\bActivator\.CreateInstance\s*\(|\bType\.GetType\s*\(|\bDynamicExpressionParser\b"
        ),
    ),
    _Pattern(
        "sink",
        "injection",
        "HTML output",
        _rx(
            r"\b(?:innerHTML|outerHTML|dangerouslySetInnerHTML|document\.write|v-html|render\(|html\(|echo\s)\b"
            r"|\bHtml\.Raw\s*\(|\bnew\s+(?:HtmlString|MarkupString)\s*\(|\(\s*MarkupString\s*\)|\bResponse\.Write\s*\(|<%=|\bContent\s*\([^)]*text/html"
        ),
    ),
    _Pattern(
        "sink",
        "access",
        "Redirect or navigation",
        _rx(
            r"\b(?:redirect|sendRedirect|Location|window\.location|location\.(?:href|assign|replace)|window\.open)\b"
            r"|\bRedirect(?:Permanent\w*|PreserveMethod)?\s*\(|\bResponse\.Redirect\s*\("
        ),
    ),
    _Pattern(
        "sink",
        "access",
        "Authorization decision",
        _rx(
            r"\b(?:authorize|permission|isAllowed|hasRole|hasPermission|checkAccess|ownership|owner_id|tenant_id)\b"
            r"|\b(?:AuthorizeAsync|IsInRole|HasClaim|FindFirst(?:Value)?)\s*\("
        ),
    ),
    _Pattern(
        "sink",
        "access",
        "Response serialization",
        _rx(
            r"\b(?:toPublic|toJSON|to_dict|as_dict|serialize|jsonify|JsonResponse|Response::success|res\.json)\s*\("
            r"|\bSerializeObject\s*\("
            # ASP.NET action results that write an object into the response.
            r"|(?-i:\breturn\s+(?:Ok|Json|Created\w*|Accepted\w*|(?:Typed)?Results\.(?:Ok|Json|Created\w*))\s*(?:<[^>]*>)?\s*\(\s*[^)\s])"
        ),
    ),
    _Pattern(
        "sink",
        "logic",
        "Deserialization",
        _rx(
            r"\b(?:pickle\.loads|yaml\.load|ObjectInputStream|unserialize|BinaryFormatter|readObject)\b"
            r"|\bTypeNameHandling\.(?:All|Auto|Objects|Arrays)\b|\b(?:LosFormatter|ObjectStateFormatter|SoapFormatter|NetDataContractSerializer|JavaScriptSerializer|XmlSerializer|DataContractSerializer)\b"
            r"|\bSimpleTypeResolver\b"
        ),
    ),
    _Pattern(
        "sink",
        "logic",
        "Cryptographic operation",
        _rx_exact(
            r"\b(?:md5|sha1|crc32|MD5|SHA1)(?:_file)?\s*\(|\bhashlib\.(?:md5|sha1|new)\b"
            r"|\b(?:Cipher|MessageDigest|KeyGenerator|SecureRandom|Signature|Mac|SecretKeyFactory)\.getInstance\s*\("
            r"|\bcrypto\.(?:createCipher\w*|createDecipher\w*|createHash|createHmac|createSign|createVerify|randomBytes|pbkdf2\w*|scrypt\w*|subtle)\b"
            r"|\b(?:openssl|sodium|mcrypt)_\w+\s*\(|\bpassword_(?:hash|verify)\s*\(|\bhash(?:_hmac|_equals)?\s*\("
            r"|\b(?:jwt|jsonwebtoken|jose)\.(?:sign|verify|decode)\s*\(|\bJWT::(?:encode|decode)\s*\("
            r"|\bMath\.random\s*\(|"
            + _FREE_CALL
            + r"(?:mt_)?rand\s*\(|\brandom\.(?:random|randint|choice|randrange|getrandbits)\s*\("
            r"|\buniqid\s*\(|\b(?:DES|3DES|RC4|ECB)\b|\bbcrypt\b|\b(?:encrypt|decrypt)\w*\s*\("
            r"|\b(?:MD5|SHA1|DES|TripleDES|RC2|Aes|Rijndael|RSA|ECDsa|HMAC\w*)\.Create\s*\(|\bnew\s+(?:Random|MD5CryptoServiceProvider|SHA1Managed|RijndaelManaged|DESCryptoServiceProvider|HMACMD5|HMACSHA1)\s*\("
            r"|\bRfc2898DeriveBytes\b|\bRandomNumberGenerator\b|\b(?:Encrypt|Decrypt|ComputeHash|SignData|VerifyData)\s*\("
            r"|\b(?:JwtSecurityTokenHandler|TokenValidationParameters)\b"
        ),
    ),
    _Pattern(
        "sink",
        "logic",
        "Sensitive logging",
        _rx(
            r"\b(?:log|logger|console)\.(?:debug|info|warn|error|log)\s*\("
            r"|\.Log(?:Trace|Debug|Information|Warning|Error|Critical)\s*\("
            r"|\bLog\.(?:Verbose|Debug|Information|Warning|Error|Fatal)\s*\("
        ),
    ),
    _Pattern(
        "sink",
        "logic",
        "Concurrent state operation",
        _rx(
            r"\b(?:create_task|executor\.submit|CompletableFuture|go\s+func|setImmediate|ThreadPoolExecutor)\b"
            r"|\bTask\.Run\s*\(|\bParallel\.For(?:Each)?(?:Async)?\s*\(|\bThreadPool\.QueueUserWorkItem\b|\bnew\s+Thread\s*\("
        ),
    ),
    _Pattern(
        "control",
        "authentication",
        "Authentication control",
        _rx(
            r"\b(?:authenticate|login_required|requireAuth|verify_jwt|verifyToken|get_current_user|PreAuthorize)\b"
            r"|\[\s*AllowAnonymous\b|\b(?:SignInAsync|PasswordSignInAsync|AddAuthentication|AddJwtBearer|UseAuthentication|ValidateToken)\s*\("
        ),
    ),
    _Pattern(
        "control",
        "authorization",
        "Authorization control",
        _rx(
            r"\b(?:authorize|checkAccess|hasPermission|hasRole|current_user_can|ownership|owner_id\s*==|tenant_id\s*==)\b"
            r"|\b(?:RequireAuthorization|AddAuthorization|UseAuthorization|RequireRole|RequireClaim)\s*\("
        ),
    ),
    _Pattern(
        "control",
        "validation",
        "Input validation",
        _rx(
            r"\b(?:validate|validator|schema\.parse|safeParse|isValid|sanitize|escape|parameterized|prepareStatement|nonce|csrf)\b"
            r"|\bModelState\.IsValid\b|\[\s*(?:ValidateAntiForgeryToken|AutoValidateAntiforgeryToken|IgnoreAntiforgeryToken)\b|\bSqlParameter\b|\.Parameters\.Add\w*\s*\("
        ),
    ),
)


def _file_classification(path: Path, rel: str) -> tuple[str, bool, str]:
    parts = {part.casefold() for part in Path(rel).parts}
    name = path.name.casefold()
    suffixes = "".join(path.suffixes[-2:]).casefold()
    if parts & _EXCLUDED_PARTS:
        return "dependency_or_build", False, "dependency, build output, or VCS data"
    if parts & _TEST_PARTS or re.search(r"(?:^test_|_test\.|\.test\.|\.spec\.)", name):
        return "test", False, "test or fixture code"
    if parts & _GENERATED_PARTS or ".generated." in name or name.endswith(".pb.go"):
        return "generated", False, "generated source"
    if path.suffix.casefold() in _DOC_SUFFIXES:
        return "documentation", False, "documentation"
    if path.suffix.casefold() in _ASSET_SUFFIXES or suffixes in _ASSET_SUFFIXES:
        return "asset", False, "static or minified asset"
    language = _LANGUAGE_BY_SUFFIX.get(path.suffix.casefold(), "Other")
    if language == "Configuration":
        return "configuration", True, "runtime or deployment configuration"
    if language in _SOURCE_LANGUAGES:
        return "production", True, "first-party source candidate"
    return "other", False, "unsupported non-source file"


def _fingerprint(*parts: object) -> str:
    value = "|".join(str(part or "").strip().casefold() for part in parts)
    return hashlib.sha256(value.encode()).hexdigest()


def _handler_scope(path: str) -> bool:
    """Find likely request handlers even when a framework's route syntax is unknown."""
    parts = [part.casefold() for part in Path(path).parts]
    stem = Path(path).stem.casefold()
    if set(parts[:-1]) & {
        "controllers",
        "controller",
        "handlers",
        "handler",
        "routes",
        "endpoints",
        "hubs",
    }:
        return True
    if stem.endswith(
        ("controller", "handler", "router", "routes", "endpoint", "endpoints", "hub")
    ):
        return True
    # Razor Pages code-behind, e.g. Pages/Account/Login.cshtml.cs.
    if path.casefold().endswith((".cshtml.cs", ".aspx.cs", ".ashx.cs", ".asmx.cs")):
        return True
    if stem in {"views", "urls"} and Path(path).suffix.casefold() == ".py":
        return True
    return stem in {"index", "app", "server", "main"} and (
        len(parts) == 1 or bool(set(parts[:-1]) & {"public", "api", "server"})
    )


def _partition_base(path: str) -> str:
    parts = Path(path).parts
    if len(parts) <= 1:
        return "root"
    source_markers = {"src", "app", "apps", "lib", "libs", "cmd", "pkg", "server"}
    for index, part in enumerate(parts[:-1]):
        if part.casefold() in source_markers and index + 1 < len(parts) - 1:
            return "/".join(parts[: index + 2])
    return "/".join(parts[: min(2, len(parts) - 1)]) or "root"


def reset_work_program(sast_run_id: int) -> None:
    """Remove work-program rows for a fresh scan without touching leads/logs."""
    with Session(get_engine()) as session:
        for model in (
            SastObligationLead,
            SastCoverageObligation,
            SastThreatScenario,
            SastThreatModel,
            SastSurfaceEdge,
            SastDiscoveryTelemetry,
            SastEvidenceReceipt,
            SastWorkItem,
            SastWorker,
            SastPartition,
            SastSurfaceItem,
            SastSourceFile,
            SastCodeCall,
            SastCodeSymbol,
        ):
            session.exec(delete(model).where(model.sast_run_id == sast_run_id))
        session.commit()


def build_source_atlas(sast_run_id: int, root: Path) -> dict[str, Any]:
    """Inventory production scope and seed durable source/sink obligations."""
    reset_work_program(sast_run_id)
    file_rows: list[SastSourceFile] = []
    path_to_disk: dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            classification, relevant, reason = _file_classification(path, rel)
            try:
                raw = path.read_bytes()
                file_stat = path.stat()
            except OSError:
                continue
            digest = hashlib.sha256(raw).hexdigest()
            file_rows.append(
                SastSourceFile(
                    sast_run_id=sast_run_id,
                    path=rel,
                    language=_LANGUAGE_BY_SUFFIX.get(path.suffix.casefold(), "Other"),
                    size=file_stat.st_size,
                    sha256=digest,
                    classification=classification,
                    production_relevant=relevant,
                    classification_reason=reason,
                )
            )
            path_to_disk[rel] = path

    with Session(get_engine(), expire_on_commit=False) as session:
        session.add_all(file_rows)
        session.commit()
        persisted_files = session.exec(
            select(SastSourceFile).where(SastSourceFile.sast_run_id == sast_run_id)
        ).all()
        graph = sast_codegraph.build_code_graph(
            (row.path, path_to_disk[row.path])
            for row in persisted_files
            if row.production_relevant and row.size <= _MAX_ATLAS_FILE_BYTES
        )
        sinks_outside_calls = 0
        surface_rows: list[SastSurfaceItem] = []
        for row in persisted_files:
            if not row.production_relevant or len(surface_rows) >= _MAX_SURFACE_ITEMS:
                continue
            path = path_to_disk[row.path]
            if row.size > _MAX_ATLAS_FILE_BYTES:
                continue
            try:
                raw = path.read_bytes()
                if b"\x00" in raw[:512]:
                    continue
                lines = raw.decode("utf-8", errors="replace").splitlines()
            except OSError:
                continue
            file_surface_start = len(surface_rows)
            parsed = graph.is_parsed(row.path)
            for line_number, line in enumerate(lines, start=1):
                for pattern in _PATTERNS:
                    match = pattern.regex.search(line)
                    if not match:
                        continue
                    if (
                        parsed
                        and pattern.kind == "sink"
                        and pattern.name in _CALL_SINKS
                        and not any(
                            call.kind != "ref" and pattern.regex.search(call.text)
                            for call in graph.calls_on_line(row.path, line_number)
                        )
                    ):
                        sinks_outside_calls += 1
                        continue
                    snippet = line.strip()[:500]
                    surface_rows.append(
                        SastSurfaceItem(
                            sast_run_id=sast_run_id,
                            source_file_id=row.id,
                            kind=pattern.kind,
                            category=pattern.category,
                            name=pattern.name,
                            path=row.path,
                            line=line_number,
                            symbol=snippet[:160],
                            details_json=json.dumps({"snippet": snippet}),
                            fingerprint=_fingerprint(
                                pattern.kind,
                                pattern.category,
                                row.path,
                                line_number,
                                pattern.name,
                            ),
                        )
                    )
                    if len(surface_rows) >= _MAX_SURFACE_ITEMS:
                        break
                if len(surface_rows) >= _MAX_SURFACE_ITEMS:
                    break
            if len(surface_rows) >= _MAX_SURFACE_ITEMS:
                continue
            file_entrypoints = [
                item
                for item in surface_rows[file_surface_start:]
                if item.kind == "entrypoint"
            ]
            handler_scope = row.language in _SOURCE_LANGUAGES - {
                "HTML",
                "Vue",
                "Svelte",
            } and _handler_scope(row.path)
            if not file_entrypoints and handler_scope:
                surface_rows.append(
                    SastSurfaceItem(
                        sast_run_id=sast_run_id,
                        source_file_id=row.id,
                        kind="entrypoint",
                        category="inferred_handler",
                        name="Likely request handler",
                        path=row.path,
                        line=1,
                        symbol="Review this handler and find its callers or route registration.",
                        provenance="path_heuristic",
                        fingerprint=_fingerprint("inferred-handler", row.path),
                    )
                )
            if file_entrypoints or handler_scope:
                surface_rows.append(
                    SastSurfaceItem(
                        sast_run_id=sast_run_id,
                        source_file_id=row.id,
                        kind="input",
                        category="handler_review",
                        name="Route and handler security review",
                        path=row.path,
                        line=file_entrypoints[0].line if file_entrypoints else 1,
                        symbol=(
                            "Trace registered routes to handlers; review authentication, "
                            "validation, response data, errors, rate limits, sensitive "
                            "state changes, and audit events."
                        ),
                        provenance="scope_review",
                        fingerprint=_fingerprint("handler-review", row.path),
                    )
                )
        _annotate_reachability(graph, surface_rows)
        session.add_all(surface_rows)
        session.commit()
        _persist_code_graph(session, sast_run_id, graph)

        surfaces = session.exec(
            select(SastSurfaceItem).where(SastSurfaceItem.sast_run_id == sast_run_id)
        ).all()
        entrypoints = [item for item in surfaces if item.kind == "entrypoint"]
        inputs = [item for item in surfaces if item.kind == "input"]
        sinks = [item for item in surfaces if item.kind == "sink"]

        if not inputs:
            seeds = (
                entrypoints
                or [
                    SastSurfaceItem(
                        sast_run_id=sast_run_id,
                        source_file_id=row.id,
                        kind="input",
                        category="repository_surface",
                        name="Production source scope",
                        path=row.path,
                        line=1,
                        symbol="No framework-specific input was detected; review this source scope.",
                        details_json="{}",
                        provenance="fallback",
                        fingerprint=_fingerprint("fallback-input", row.path),
                    )
                    for row in persisted_files
                    if row.production_relevant
                ][:200]
            )
            for seed in seeds:
                if seed.kind == "input":
                    session.add(seed)
                else:
                    session.add(
                        SastSurfaceItem(
                            sast_run_id=sast_run_id,
                            source_file_id=seed.source_file_id,
                            kind="input",
                            category="no_input_entrypoint",
                            name=f"Entrypoint review: {seed.name}",
                            path=seed.path,
                            line=seed.line,
                            symbol=seed.symbol,
                            details_json=json.dumps({"entrypoint_id": seed.id}),
                            provenance="reconciliation",
                            fingerprint=_fingerprint(
                                "entrypoint-input", seed.fingerprint
                            ),
                        )
                    )
            session.commit()
            surfaces = session.exec(
                select(SastSurfaceItem).where(
                    SastSurfaceItem.sast_run_id == sast_run_id
                )
            ).all()
            inputs = [item for item in surfaces if item.kind == "input"]

        grouped: dict[str, list[SastSurfaceItem]] = defaultdict(list)
        for item in inputs:
            grouped[_partition_base(item.path)].append(item)
        partition_rows: list[SastPartition] = []
        for base, items in sorted(grouped.items()):
            for offset in range(0, len(items), _PARTITION_INPUT_LIMIT):
                chunk = items[offset : offset + _PARTITION_INPUT_LIMIT]
                key = f"{base}:{offset // _PARTITION_INPUT_LIMIT + 1}"
                partition_rows.append(
                    SastPartition(
                        sast_run_id=sast_run_id,
                        partition_key=key,
                        name=f"{base} part {offset // _PARTITION_INPUT_LIMIT + 1}",
                        file_paths_json=json.dumps(
                            sorted({item.path for item in chunk})
                        ),
                    )
                )
        session.add_all(partition_rows)
        session.commit()

        partitions = session.exec(
            select(SastPartition).where(SastPartition.sast_run_id == sast_run_id)
        ).all()
        partition_for_path: dict[str, SastPartition] = {}
        for partition in partitions:
            for path in json.loads(partition.file_paths_json):
                partition_for_path.setdefault(path, partition)

        workers: dict[int, SastWorker] = {}
        for partition in partitions:
            worker = SastWorker(
                sast_run_id=sast_run_id,
                partition_id=partition.id,
                worker_key=f"{partition.partition_key}:review",
                class_group="review",
            )
            session.add(worker)
            workers[partition.id] = worker
        # A route reviewer can close local sink checks while the file is open.
        # Shared/helper sinks and excess work remain for the later sink pass.
        route_paths = {
            item.path for item in inputs if item.category == "handler_review"
        }
        local_sink_counts: dict[int, int] = defaultdict(int)
        local_sinks: list[tuple[SastSurfaceItem, SastPartition]] = []
        residual_sinks: list[SastSurfaceItem] = []
        for sink in sinks:
            partition = partition_for_path.get(sink.path)
            if (
                sink.path in route_paths
                and partition is not None
                and local_sink_counts[partition.id] < _PARTITION_INPUT_LIMIT
            ):
                local_sinks.append((sink, partition))
                local_sink_counts[partition.id] += 1
            else:
                residual_sinks.append(sink)
        sink_workers: list[SastWorker] = []
        for offset in range(0, len(residual_sinks), _SINK_WORK_LIMIT):
            sink_worker = SastWorker(
                sast_run_id=sast_run_id,
                partition_id=None,
                worker_key=f"sink-audit:{offset // _SINK_WORK_LIMIT + 1}",
                class_group="sink",
            )
            session.add(sink_worker)
            sink_workers.append(sink_worker)
        session.commit()

        for item in inputs:
            partition = partition_for_path.get(item.path)
            if partition is None:
                continue
            for class_group in CLASS_GROUPS:
                worker = workers[partition.id]
                session.add(
                    SastWorkItem(
                        sast_run_id=sast_run_id,
                        partition_id=partition.id,
                        surface_item_id=item.id,
                        worker_id=worker.id,
                        work_key=f"input:{item.id}:{class_group}",
                        work_type="input",
                        class_group=class_group,
                    )
                )
        for sink, partition in local_sinks:
            session.add(
                SastWorkItem(
                    sast_run_id=sast_run_id,
                    partition_id=partition.id,
                    surface_item_id=sink.id,
                    worker_id=workers[partition.id].id,
                    work_key=f"sink:{sink.id}",
                    work_type="sink",
                    class_group="sink",
                )
            )
        for offset in range(0, len(residual_sinks), _SINK_WORK_LIMIT):
            worker = sink_workers[offset // _SINK_WORK_LIMIT]
            for sink in residual_sinks[offset : offset + _SINK_WORK_LIMIT]:
                session.add(
                    SastWorkItem(
                        sast_run_id=sast_run_id,
                        partition_id=(
                            partition_for_path.get(sink.path).id
                            if partition_for_path.get(sink.path)
                            else None
                        ),
                        surface_item_id=sink.id,
                        worker_id=worker.id,
                        work_key=f"sink:{sink.id}",
                        work_type="sink",
                        class_group="sink",
                    )
                )
        session.commit()

    summary = work_program_summary(sast_run_id)
    summary["code_graph"] = {
        **summary.get("code_graph", {}),
        "sink_matches_outside_calls": sinks_outside_calls,
        "warnings": graph.warnings[:20],
    }
    return summary


def _annotate_reachability(
    graph: sast_codegraph.CodeGraph, surface_rows: list[SastSurfaceItem]
) -> None:
    """Mark each surface item with its function and whether an entry point reaches it.

    Roots are every file's top level, every function holding a detected route
    or request input, and every function in a likely handler file.
    """
    roots = {graph.module_key(path) for path in graph.parsed_files}
    for item in surface_rows:
        if (
            item.kind in {"entrypoint", "input"}
            and item.category not in _SYNTHETIC_CATEGORIES
            and item.line
        ):
            enclosing = graph.enclosing_def(item.path, item.line)
            if enclosing is not None:
                roots.add(enclosing.key)
    for path in graph.parsed_files:
        if _handler_scope(path):
            roots.update(item.key for item in graph.defs_in_file(path))
    graph.compute_reachability(roots)
    for item in surface_rows:
        if item.category in _SYNTHETIC_CATEGORIES or not item.line:
            continue
        status, enclosing = graph.status_for(item.path, item.line)
        if enclosing is None:
            continue
        details = json.loads(item.details_json or "{}")
        details["function"] = enclosing.label
        details["reachability"] = status
        if status == sast_codegraph.REACHABLE:
            chain = graph.path_to(enclosing.key)
            if len(chain) > 1:
                details["reached_from"] = [
                    graph.defs[key].label for key in chain if key in graph.defs
                ]
        item.details_json = json.dumps(details)


def _persist_code_graph(
    session: Session, sast_run_id: int, graph: sast_codegraph.CodeGraph
) -> None:
    symbol_rows = [
        {
            "sast_run_id": sast_run_id,
            "symbol_key": item.key,
            "path": item.path,
            "language": item.language,
            "name": item.name,
            "qualname": item.qualname,
            "kind": item.kind,
            "start_line": item.start_line,
            "end_line": item.end_line,
            "reachability": graph.reachability.get(item.key, sast_codegraph.UNKNOWN),
            "is_root": item.key in graph.roots,
        }
        for item in graph.defs.values()
    ]
    call_rows = [
        {
            "sast_run_id": sast_run_id,
            "path": call.path,
            "line": call.line,
            "caller_key": call.caller_key,
            "callee_name": call.callee_name,
            "receiver": call.receiver,
            "kind": call.kind,
            "text": call.text,
            "targets_json": json.dumps(call.targets),
        }
        for call in graph.calls
    ]
    connection = session.connection()
    for model, rows in ((SastCodeSymbol, symbol_rows), (SastCodeCall, call_rows)):
        for offset in range(0, len(rows), _CODE_GRAPH_BATCH):
            connection.execute(
                insert(model.__table__), rows[offset : offset + _CODE_GRAPH_BATCH]
            )
    session.commit()


def work_program_summary(sast_run_id: int) -> dict[str, Any]:
    with Session(get_engine()) as session:
        files = session.exec(
            select(SastSourceFile).where(SastSourceFile.sast_run_id == sast_run_id)
        ).all()
        surfaces = session.exec(
            select(SastSurfaceItem).where(SastSurfaceItem.sast_run_id == sast_run_id)
        ).all()
        partitions = session.exec(
            select(SastPartition).where(SastPartition.sast_run_id == sast_run_id)
        ).all()
        workers = session.exec(
            select(SastWorker).where(SastWorker.sast_run_id == sast_run_id)
        ).all()
        work_items = session.exec(
            select(SastWorkItem).where(SastWorkItem.sast_run_id == sast_run_id)
        ).all()
        receipts = session.exec(
            select(SastEvidenceReceipt).where(
                SastEvidenceReceipt.sast_run_id == sast_run_id
            )
        ).all()

    surface_counts: dict[str, int] = defaultdict(int)
    for item in surfaces:
        surface_counts[item.kind] += 1
    work_counts: dict[str, int] = defaultdict(int)
    for item in work_items:
        work_counts[item.status] += 1
    worker_counts: dict[str, int] = defaultdict(int)
    for worker in workers:
        worker_counts[worker.status] += 1
    surface_by_id = {item.id: item for item in surfaces}
    worker_by_id = {worker.id: worker for worker in workers}
    partition_paths = {
        partition.id: set(json.loads(partition.file_paths_json))
        for partition in partitions
    }
    claimed_helper_sinks = sum(
        item.work_type == "sink"
        and (worker := worker_by_id.get(item.worker_id)) is not None
        and worker.class_group == "review"
        and (surface := surface_by_id.get(item.surface_item_id)) is not None
        and surface.path not in partition_paths.get(worker.partition_id, set())
        for item in work_items
    )
    direct_paths = {
        receipt.path for receipt in receipts if receipt.tool_name == "read_file"
    }
    matched_paths: set[str] = set()
    for receipt in receipts:
        try:
            matched_paths.update(
                json.loads(receipt.details_json).get("matched_paths", [])
            )
        except (TypeError, ValueError, AttributeError):
            continue
    unresolved = sum(
        count
        for status, count in work_counts.items()
        if status not in TERMINAL_WORK_STATUSES
    )
    sink_reachability: dict[str, int] = defaultdict(int)
    for item in surfaces:
        if item.kind == "sink":
            status = _code_context(item).get("reachability", sast_codegraph.UNKNOWN)
            sink_reachability[status] += 1
    return {
        "files": {
            "total": len(files),
            "production": sum(row.production_relevant for row in files),
            "directly_opened": len(direct_paths),
            "with_search_matches": len(matched_paths),
        },
        "surface": dict(surface_counts),
        "partitions": {
            "total": len(partitions),
            "complete": sum(row.status == "complete" for row in partitions),
        },
        "workers": {"total": len(workers), **dict(worker_counts)},
        "work_items": {
            "total": len(work_items),
            "resolved": len(work_items) - unresolved,
            "unresolved": unresolved,
            "claimed_helper_sinks": claimed_helper_sinks,
            "statuses": dict(work_counts),
        },
        "evidence": {
            "receipts": len(receipts),
            "read_calls": sum(r.tool_name == "read_file" for r in receipts),
            "search_calls": sum(r.tool_name == "grep" for r in receipts),
            "characters_returned": sum(r.characters_returned for r in receipts),
            "truncated": sum(r.truncated for r in receipts),
        },
        "code_graph": {
            **_code_graph_counts(sast_run_id),
            "sink_reachability": dict(sink_reachability),
        },
    }


def _code_graph_counts(sast_run_id: int) -> dict[str, Any]:
    with Session(get_engine()) as session:
        languages = {
            str(language): int(count)
            for language, count in session.exec(
                select(SastCodeSymbol.language, func.count())
                .where(
                    SastCodeSymbol.sast_run_id == sast_run_id,
                    SastCodeSymbol.kind == "module",
                )
                .group_by(SastCodeSymbol.language)
            ).all()
        }
        function_reachability = {
            str(status): int(count)
            for status, count in session.exec(
                select(SastCodeSymbol.reachability, func.count())
                .where(
                    SastCodeSymbol.sast_run_id == sast_run_id,
                    SastCodeSymbol.kind != "module",
                )
                .group_by(SastCodeSymbol.reachability)
            ).all()
        }
        files = sum(languages.values())
        functions = session.exec(
            select(func.count())
            .select_from(SastCodeSymbol)
            .where(
                SastCodeSymbol.sast_run_id == sast_run_id,
                SastCodeSymbol.kind != "module",
            )
        ).one()
        calls = session.exec(
            select(func.count())
            .select_from(SastCodeCall)
            .where(SastCodeCall.sast_run_id == sast_run_id, SastCodeCall.kind != "ref")
        ).one()
        resolved = session.exec(
            select(func.count())
            .select_from(SastCodeCall)
            .where(
                SastCodeCall.sast_run_id == sast_run_id,
                SastCodeCall.kind != "ref",
                SastCodeCall.targets_json != "[]",
            )
        ).one()
    return {
        "files_parsed": int(files),
        "languages": dict(sorted(languages.items())),
        "functions": int(functions),
        "function_reachability": function_reachability,
        "calls": int(calls),
        "resolved_calls": int(resolved),
    }


def worker_payload(worker_id: int) -> dict[str, Any]:
    with Session(get_engine()) as session:
        worker = session.get(SastWorker, worker_id)
        if worker is None:
            return {}
        partition = (
            session.get(SastPartition, worker.partition_id)
            if worker.partition_id
            else None
        )
        work_items = session.exec(
            select(SastWorkItem)
            .where(SastWorkItem.worker_id == worker_id)
            .order_by(SastWorkItem.id)
        ).all()
        result = []
        for work_item in work_items:
            surface = session.get(SastSurfaceItem, work_item.surface_item_id)
            if surface is None:
                continue
            result.append(
                {
                    "work_item_id": work_item.id,
                    "work_type": work_item.work_type,
                    "class_group": work_item.class_group,
                    "status": work_item.status,
                    "surface": {
                        "kind": surface.kind,
                        "category": surface.category,
                        "name": surface.name,
                        "path": surface.path,
                        "line": surface.line,
                        "symbol": surface.symbol,
                        "trust_level": surface.trust_level,
                        **_code_context(surface),
                    },
                }
            )
        return {
            "worker_id": worker.id,
            "worker_key": worker.worker_key,
            "class_group": worker.class_group,
            "partition": partition.partition_key if partition else "global",
            "files": json.loads(partition.file_paths_json) if partition else [],
            "work_items": result,
        }


def _code_context(surface: SastSurfaceItem) -> dict[str, Any]:
    try:
        details = json.loads(surface.details_json or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(details, dict):
        return {}
    return {
        key: details[key]
        for key in ("function", "reachability", "reached_from")
        if details.get(key)
    }


def work_program_view(worker_id: int) -> dict[str, Any]:
    """Return a worker's program for the model, with open items listed first.

    Finished items are reduced to their id and status so a large program still
    shows every open item in full.
    """
    payload = worker_payload(worker_id)
    if not payload:
        return payload
    items = list(payload.get("work_items") or [])
    open_items = [
        item for item in items if item.get("status") not in TERMINAL_WORK_STATUSES
    ]
    finished = [
        {"work_item_id": item["work_item_id"], "status": item.get("status")}
        for item in items
        if item.get("status") in TERMINAL_WORK_STATUSES
    ]
    return {
        **{key: value for key, value in payload.items() if key != "work_items"},
        "open_count": len(open_items),
        "finished_count": len(finished),
        "work_items": open_items,
        "finished_items": finished,
    }


def unresolved_items_message(worker_id: int, limit: int = 50) -> str:
    """Describe a worker's open items so the model can act on them directly."""
    open_ids = set(unresolved_for_worker(worker_id))
    if not open_ids:
        return ""
    items = [
        item
        for item in worker_payload(worker_id).get("work_items") or []
        if item.get("work_item_id") in open_ids
    ]
    lines = []
    for item in items[:limit]:
        surface = item.get("surface") or {}
        location = str(surface.get("path") or "unknown file")
        if surface.get("line"):
            location += f":{surface['line']}"
        detail = " ".join(
            str(part)
            for part in (
                item.get("work_type"),
                surface.get("category"),
                surface.get("name"),
            )
            if part
        )
        symbol = str(surface.get("symbol") or "").strip()
        if len(symbol) > 160:
            symbol = symbol[:157] + "..."
        line = f"- {item['work_item_id']}: {detail} at {location}"
        if symbol:
            line += f" — {symbol}"
        lines.append(line)
    found_ids = {item["work_item_id"] for item in items}
    for missing_id in sorted(open_ids - found_ids):
        if len(lines) >= limit:
            break
        lines.append(f"- {missing_id}: no source location recorded")
    extra = len(open_ids) - len(lines)
    if extra > 0:
        lines.append(f"- ...and {extra} more; call get_work_program to see them.")
    return "Resolve these assigned work items before done:\n" + "\n".join(lines)


def discovery_worker_budget(
    payload: dict[str, Any],
    *,
    security_check_count: int,
    budget_mode: str,
    minimum: int,
    maximum: int,
    is_baseline: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Return a discovery budget and the inputs used to calculate it."""
    work_items = list(payload.get("work_items") or [])
    paths = {str(path) for path in payload.get("files") or [] if path}
    paths.update(
        str(item.get("surface", {}).get("path"))
        for item in work_items
        if item.get("surface", {}).get("path")
    )
    basis = {
        "mode": budget_mode,
        "minimum": minimum,
        "maximum": maximum,
        "work_items": len(work_items),
        "security_checks": max(0, security_check_count),
        "unique_files": len(paths),
        "class_group": str(payload.get("class_group") or ""),
        "baseline": is_baseline,
    }
    if budget_mode == "fixed":
        basis["calculated"] = minimum
        return minimum, basis

    calculated = (
        20 + 3 * len(work_items) + 2 * max(0, security_check_count) + 2 * len(paths)
    )
    if str(payload.get("class_group") or "") in {"access", "logic"}:
        calculated = (calculated * 115 + 99) // 100
    basis["calculated"] = calculated
    return min(maximum, max(minimum, calculated)), basis


def set_worker_budget(worker_id: int, budget: int, basis: dict[str, Any]) -> None:
    with Session(get_engine()) as session:
        worker = session.get(SastWorker, worker_id)
        if worker is None:
            return
        worker.tool_call_budget = budget
        worker.budget_basis_json = json.dumps(basis, sort_keys=True)
        worker.updated_at = datetime.now(_UTC)
        session.add(worker)
        session.commit()


def set_worker_status(
    worker_id: int, status: str, *, summary: str = "", error: str = ""
) -> None:
    with Session(get_engine()) as session:
        worker = session.get(SastWorker, worker_id)
        if worker is None:
            return
        now = datetime.now(_UTC)
        worker.status = status
        worker.summary = summary[:4000]
        worker.error_message = error[:4000]
        worker.updated_at = now
        if status == "running" and worker.started_at is None:
            worker.started_at = now
        if status in {"complete", "failed", "blocked"}:
            worker.completed_at = now
        session.add(worker)
        session.flush()
        if worker.partition_id:
            partition = session.get(SastPartition, worker.partition_id)
            if partition is not None:
                sibling_statuses = session.exec(
                    select(SastWorker.status).where(
                        SastWorker.partition_id == partition.id
                    )
                ).all()
                statuses = list(sibling_statuses)
                if all(value == "complete" for value in statuses):
                    partition.status = "complete"
                    partition.completed_at = now
                elif any(value in {"failed", "blocked"} for value in statuses):
                    partition.status = "partial"
                elif any(value == "running" for value in statuses):
                    partition.status = "running"
                    partition.started_at = partition.started_at or now
                partition.updated_at = now
                session.add(partition)
        session.commit()


def unresolved_for_worker(worker_id: int) -> list[int]:
    with Session(get_engine()) as session:
        rows = session.exec(
            select(SastWorkItem).where(SastWorkItem.worker_id == worker_id)
        ).all()
    return [row.id for row in rows if row.status not in TERMINAL_WORK_STATUSES]


def claim_traced_sinks(worker_id: int, path: str, line: int) -> tuple[list[int], str]:
    """Assign a directly read helper sink to the route worker that traced it."""

    with Session(get_engine()) as session:
        worker = session.get(SastWorker, worker_id)
        if worker is None or worker.class_group != "review":
            return [], "Only a route review worker can claim a traced sink."
        if line < 1 or not path:
            return [], "Give the exact source file and sink line."
        receipt = session.exec(
            select(SastEvidenceReceipt.id)
            .where(SastEvidenceReceipt.worker_id == worker_id)
            .where(SastEvidenceReceipt.tool_name == "read_file")
            .where(SastEvidenceReceipt.path == path)
            .where(
                (SastEvidenceReceipt.start_line == None)  # noqa: E711
                | (SastEvidenceReceipt.start_line <= line)
            )
            .where(
                (SastEvidenceReceipt.end_line == None)  # noqa: E711
                | (SastEvidenceReceipt.end_line >= line)
            )
        ).first()
        if receipt is None:
            return [], f"Open {path}:{line} with read_file before claiming it."
        route_items = session.exec(
            select(SastWorkItem)
            .where(SastWorkItem.worker_id == worker_id)
            .where(SastWorkItem.work_type == "input")
        ).all()
        route_paths = {
            surface.path
            for item in route_items
            if item.surface_item_id
            if (surface := session.get(SastSurfaceItem, item.surface_item_id))
            is not None
        }
        route_read = session.exec(
            select(SastEvidenceReceipt.id)
            .where(SastEvidenceReceipt.worker_id == worker_id)
            .where(SastEvidenceReceipt.tool_name == "read_file")
            .where(SastEvidenceReceipt.path.in_(route_paths))
        ).first()
        if route_read is None:
            return [], "Open an assigned route or handler before claiming its sink."
        claimed_count = sum(
            item.work_type == "sink"
            and (surface := session.get(SastSurfaceItem, item.surface_item_id))
            is not None
            and surface.path not in route_paths
            for item in session.exec(
                select(SastWorkItem).where(SastWorkItem.worker_id == worker_id)
            ).all()
        )
        if claimed_count >= _HELPER_SINK_CLAIM_LIMIT:
            return (
                [],
                "Helper sink claim limit reached; remaining sinks stay in later review.",
            )
        surfaces = session.exec(
            select(SastSurfaceItem)
            .where(SastSurfaceItem.sast_run_id == worker.sast_run_id)
            .where(SastSurfaceItem.kind == "sink")
            .where(SastSurfaceItem.path == path)
            .where(SastSurfaceItem.line == line)
        ).all()
        if not surfaces:
            return [], f"No inventoried sink exists at {path}:{line}."
        claimed: list[int] = []
        for surface in surfaces:
            if claimed_count >= _HELPER_SINK_CLAIM_LIMIT:
                break
            item = session.exec(
                select(SastWorkItem)
                .where(SastWorkItem.sast_run_id == worker.sast_run_id)
                .where(SastWorkItem.surface_item_id == surface.id)
                .where(SastWorkItem.work_type == "sink")
            ).first()
            if item is None or item.status in TERMINAL_WORK_STATUSES:
                continue
            if item.worker_id == worker_id:
                claimed.append(item.id)
            elif item.worker_id is not None:
                owner = session.get(SastWorker, item.worker_id)
                if (
                    owner is not None
                    and owner.class_group == "sink"
                    and owner.status == "pending"
                ):
                    changed = session.execute(
                        update(SastWorkItem)
                        .where(SastWorkItem.id == item.id)
                        .where(SastWorkItem.worker_id == owner.id)
                        .where(SastWorkItem.status == "pending")
                        .values(
                            worker_id=worker_id,
                            partition_id=worker.partition_id,
                            updated_at=datetime.now(_UTC),
                        )
                    )
                    if changed.rowcount:
                        claimed.append(item.id)
                        claimed_count += 1
        session.commit()
    if not claimed:
        return (
            [],
            "Sink is already assigned or resolved; later review remains scheduled.",
        )
    return claimed, "Claimed sink work item(s): " + ", ".join(map(str, claimed))


def record_disposition(
    work_item_id: int,
    *,
    status: str,
    reasoning: str,
    trace: list[Any] | None = None,
    controls: list[Any] | None = None,
    evidence: list[Any] | None = None,
    candidate_from_lead: bool = False,
) -> tuple[bool, str]:
    if status not in TERMINAL_WORK_STATUSES:
        return False, f"Invalid terminal disposition: {status}"
    if not reasoning.strip():
        return False, "A concrete disposition reason is required."
    if status == "candidate" and not candidate_from_lead:
        return False, "Use write_lead to record a candidate disposition."
    with Session(get_engine()) as session:
        item = session.get(SastWorkItem, work_item_id)
        if item is None:
            return False, f"Unknown work item {work_item_id}."
        if item.status == "candidate" and status != "candidate":
            return False, "A candidate work item cannot be replaced by a safe result."
        surface = (
            session.get(SastSurfaceItem, item.surface_item_id)
            if item.surface_item_id
            else None
        )
        receipts = session.exec(
            select(SastEvidenceReceipt)
            .where(SastEvidenceReceipt.worker_id == item.worker_id)
            .where(SastEvidenceReceipt.tool_name == "read_file")
        ).all()
        has_direct_evidence = surface is not None and any(
            receipt.path == surface.path
            and (
                surface.line is None
                or (
                    (receipt.start_line is None or receipt.start_line <= surface.line)
                    and (receipt.end_line is None or receipt.end_line >= surface.line)
                )
            )
            for receipt in receipts
        )
        if not has_direct_evidence:
            location = surface.path if surface is not None else "the assigned source"
            return (
                False,
                f"Open {location} with read_file before closing this work item.",
            )
        item.status = status
        item.disposition = status
        item.reasoning = reasoning[:8000]
        item.trace_json = json.dumps(trace or [], ensure_ascii=False)
        item.controls_json = json.dumps(controls or [], ensure_ascii=False)
        item.evidence_json = json.dumps(evidence or [], ensure_ascii=False)
        item.updated_at = datetime.now(_UTC)
        session.add(item)
        session.commit()
    return True, f"Work item {work_item_id} recorded as {status}."


def attach_lead(work_item_id: int | None, lead_id: int) -> None:
    if not work_item_id:
        return
    with Session(get_engine()) as session:
        item = session.get(SastWorkItem, work_item_id)
        if item is None:
            return
        item.lead_id = lead_id
        item.status = "candidate"
        item.disposition = "candidate"
        item.updated_at = datetime.now(_UTC)
        session.add(item)
        session.commit()


def record_evidence_receipt(receipt: SastEvidenceReceipt) -> None:
    with Session(get_engine()) as session:
        session.add(receipt)
        session.commit()


def completion_decision(sast_run_id: int) -> tuple[str, list[str], dict[str, Any]]:
    summary = work_program_summary(sast_run_id)
    reasons: list[str] = []
    with Session(get_engine()) as session:
        concrete_entrypoint = session.exec(
            select(SastSurfaceItem.id)
            .where(SastSurfaceItem.sast_run_id == sast_run_id)
            .where(SastSurfaceItem.kind == "entrypoint")
            .where(SastSurfaceItem.category != "inferred_handler")
        ).first()
    if summary["files"]["production"] and concrete_entrypoint is None:
        reasons.append("No production entry point was identified for reconciliation.")
    if summary["files"]["production"] and not summary["surface"].get("sink"):
        reasons.append("No security-sensitive sink was identified for the sink pass.")
    if sum(summary["surface"].values()) >= _MAX_SURFACE_ITEMS:
        reasons.append("The deterministic source atlas reached its item limit.")
    if summary["work_items"]["total"] == 0:
        reasons.append("No source or sink security checks were created.")
    if summary["work_items"]["unresolved"]:
        reasons.append(
            f"{summary['work_items']['unresolved']} work item(s) remain unresolved."
        )
    failed_workers = summary["workers"].get("failed", 0) + summary["workers"].get(
        "blocked", 0
    )
    if failed_workers:
        reasons.append(f"{failed_workers} worker(s) failed or were blocked.")
    pending_workers = summary["workers"].get("pending", 0) + summary["workers"].get(
        "running", 0
    )
    if pending_workers:
        reasons.append(f"{pending_workers} worker(s) did not complete.")
    return ("full" if not reasons else "partial", reasons, summary)


def semantic_obligation_summary(planning: dict[str, Any]) -> dict[str, Any]:
    """Project JSON security checks into the legacy work-program view.

    These checks are stored under the legacy ``obligations`` field in
    ``phase_state_json`` rather than a new table. This compact projection lets
    analysis/report consumers
    display the new planning contract beside legacy ``SastWorkItem`` rows while
    remaining tolerant of older runs and future relational storage.
    """

    obligations = planning.get("obligations")
    if not isinstance(obligations, list):
        obligations = []
    statuses: dict[str, int] = defaultdict(int)
    families: dict[str, int] = defaultdict(int)
    for obligation in obligations:
        if not isinstance(obligation, dict):
            continue
        statuses[str(obligation.get("status") or "pending")] += 1
        families[str(obligation.get("obligation_type") or "unknown")] += 1
    return {
        "total": len(obligations),
        "statuses": dict(statuses),
        "families": dict(families),
        "workers": len(planning.get("workers") or [])
        if isinstance(planning.get("workers"), list)
        else 0,
    }


def worker_rows(sast_run_id: int) -> list[SastWorker]:
    with Session(get_engine(), expire_on_commit=False) as session:
        return list(
            session.exec(
                select(SastWorker)
                .where(SastWorker.sast_run_id == sast_run_id)
                .order_by(SastWorker.id)
            ).all()
        )


def count_rows(sast_run_id: int, model) -> int:
    with Session(get_engine()) as session:
        return int(
            session.exec(
                select(func.count())
                .select_from(model)
                .where(model.sast_run_id == sast_run_id)
            ).one()
        )
