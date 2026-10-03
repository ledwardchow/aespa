from __future__ import annotations

import json

from sqlmodel import Session, select

from aespa.models import SastRun, SastSurfaceItem
from aespa.services import sast_semantic, sast_workprogram
from aespa.services.component_facts import extract_component_facts
from aespa.services.sast_parsers import extract_parser_facts

_FILES = {
    "src/Shop/Shop.csproj": """<Project Sdk="Microsoft.NET.Sdk.Web">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="12.0.1" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer">
      <Version>7.0.0</Version>
    </PackageReference>
  </ItemGroup>
</Project>
""",
    "src/Legacy/packages.config": '<packages><package id="log4net" version="1.2.10" /></packages>\n',
    "src/Shop/Program.cs": """var app = WebApplication.CreateBuilder(args).Build();
app.MapGet("/health", () => Results.Ok("ok"));
app.MapPost("/api/exec", (string cmd) => ShellRunner.Run(cmd)).RequireAuthorization();
app.Run();
""",
    "src/Shop/Controllers/OrdersController.cs": """using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class OrdersController : ControllerBase
{
    private readonly OrderRepository _repo;
    public OrdersController(OrderRepository repo) { _repo = repo; }

    [HttpGet("{id}")]
    public IActionResult Get(string id, [FromQuery] string sort)
    {
        _logger.LogInformation("Order {Id}", id);
        // new SqlCommand("select * from x")
        var order = _repo.Find(id, sort);
        return Ok(order);
    }

    [HttpPost]
    [AllowAnonymous]
    public IActionResult Import([FromBody] string payload)
    {
        var settings = new JsonSerializerSettings { TypeNameHandling = TypeNameHandling.All };
        return Content(payload, "text/html");
    }
}

public class HomeController : Controller
{
    public IActionResult Download(string name)
    {
        return PhysicalFile(Path.Combine("/var/files", name), "application/octet-stream");
    }
}
""",
    "src/Shop/Services/OrderRepository.cs": """public class OrderRepository
{
    public Order Find(string id, string sort)
    {
        var cmd = new SqlCommand("SELECT * FROM Orders WHERE Id = '" + id + "'", _conn);
        using var reader = cmd.ExecuteReader();
        return _db.Orders.FromSqlRaw("SELECT * FROM Orders WHERE Id = " + id).First();
    }
    public void Unused() { Process.Start("rm", "-rf /"); }
}
public static class ShellRunner
{
    public static string Run(string cmd) { return Process.Start("sh", cmd).ToString(); }
}
""",
    "src/Shop/Data/ShopContext.cs": """public class ShopContext : DbContext
{
    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<Order>().HasOne(o => o.User).WithMany().OnDelete(DeleteBehavior.Cascade);
    }
}
""",
    "src/Shop/Pages/Account/Login.cshtml.cs": """public class LoginModel : PageModel
{
    [BindProperty] public string ReturnUrl { get; set; }
    public void OnGet() { }
    public async Task<IActionResult> OnPostAsync()
    {
        await _signIn.PasswordSignInAsync(Input.Email, Input.Password, false, false);
        return Redirect(ReturnUrl);
    }
}
""",
    "src/Shop/Pages/Account/Login.cshtml": """@page
@model LoginModel
<div>@Html.Raw(Model.ReturnUrl)</div>
""",
    "src/Shop/Web.config": """<configuration><system.web>
<compilation debug="true" targetFramework="4.8" />
</system.web></configuration>
""",
}


def _write(root, files):
    for name, contents in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    return root


def _surfaces(tmp_path):
    root = _write(tmp_path / "source", _FILES)
    with Session(sast_workprogram.get_engine()) as session:
        run = SastRun(name="dotnet", status="scanning")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    summary = sast_workprogram.build_source_atlas(run_id, root)
    with Session(sast_workprogram.get_engine()) as session:
        rows = session.exec(
            select(SastSurfaceItem).where(SastSurfaceItem.sast_run_id == run_id)
        ).all()
    return summary, {
        (row.path.rsplit("/", 1)[-1], row.line, row.name): row for row in rows
    }


def test_work_program_finds_aspnet_routes_inputs_and_sinks(
    tmp_path, isolated_db_engine
):
    summary, items = _surfaces(tmp_path)
    keys = set(items)
    expected = {
        ("Program.cs", 2, "HTTP route"),
        ("Program.cs", 3, "HTTP route"),
        ("OrdersController.cs", 4, "Annotated HTTP handler"),
        ("OrdersController.cs", 11, "Annotated HTTP handler"),
        ("OrdersController.cs", 12, ".NET request value"),
        ("OrdersController.cs", 14, "Sensitive logging"),
        ("OrdersController.cs", 17, "Response serialization"),
        ("OrdersController.cs", 21, "Authentication control"),
        ("OrdersController.cs", 24, "Deserialization"),
        ("OrdersController.cs", 25, "HTML output"),
        ("OrdersController.cs", 33, "Filesystem operation"),
        ("OrderRepository.cs", 5, "Database query"),
        ("OrderRepository.cs", 6, "Database query"),
        ("OrderRepository.cs", 7, "Database query"),
        ("OrderRepository.cs", 9, "Command execution"),
        ("Login.cshtml.cs", 3, ".NET request value"),
        ("Login.cshtml.cs", 4, "Razor page handler"),
        ("Login.cshtml.cs", 5, "Razor page handler"),
        ("Login.cshtml.cs", 8, "Redirect or navigation"),
        ("Login.cshtml", 1, "Razor page handler"),
        ("Login.cshtml", 3, "HTML output"),
    }
    assert expected <= keys, sorted(expected - keys)
    # A commented-out query and EF's fluent OnDelete() are not review points.
    assert ("OrdersController.cs", 15, "Database query") not in keys
    assert not any(
        name == "ShopContext.cs" and kind == "Razor page handler"
        for name, _, kind in keys
    )
    unused = json.loads(
        items[("OrderRepository.cs", 9, "Command execution")].details_json
    )
    assert unused["reachability"] == "no_callers"
    query = json.loads(items[("OrderRepository.cs", 5, "Database query")].details_json)
    assert query["reachability"] == "reachable"
    assert query["function"].startswith("OrderRepository.Find")
    graph = summary["code_graph"]
    assert graph["languages"] == {"c_sharp": 5}
    assert graph["sink_matches_outside_calls"] >= 1
    assert graph["function_reachability"]["no_callers"] >= 1


def test_component_facts_map_aspnet_routes(tmp_path):
    root = _write(tmp_path, _FILES)
    facts = extract_component_facts(root)
    routes = {
        (fact["method"], fact["path"]) for fact in facts if fact["fact_type"] == "route"
    }
    assert {
        ("GET", "/health"),
        ("POST", "/api/exec"),
        ("GET", "/api/Orders/{id}"),
        ("POST", "/api/Orders"),
        (None, "/Home/Download"),
        ("GET", "/Account/Login"),
        ("POST", "/Account/Login"),
    } <= routes
    frameworks = {fact["name"] for fact in facts if fact["fact_type"] == "framework"}
    assert {"ASP.NET Core", "Entity Framework Core"} <= frameworks
    assert any(
        fact["fact_type"] == "auth_boundary" and "Authorize" in fact["name"]
        for fact in facts
    )


def test_deep_parser_facts_use_code_map_for_dotnet(tmp_path):
    root = _write(tmp_path, _FILES)
    result = extract_parser_facts(root)
    assert not result.warnings
    routes = {
        (fact["name"], fact["detail"]["method"], fact["path"])
        for fact in result.facts
        if fact["fact_type"] == "route"
    }
    assert ("OrdersController.Get", "GET", "/api/Orders/{id}") in routes
    assert ("LoginModel.OnPostAsync", "POST", "/Account/Login") in routes
    assert any(path == "/health" for _, _, path in routes)
    sinks = {
        (fact["evidence_location"].rsplit("/", 1)[-1], fact["detail"]["category"]): fact
        for fact in result.facts
        if fact["fact_type"] == "sensitive_operation"
    }
    assert sinks[("OrderRepository.cs:5", "Database query")]["detail"][
        "reachability"
    ] == ("reachable")
    assert sinks[("OrderRepository.cs:9", "Command execution")]["detail"][
        "reachability"
    ] == ("no_callers")
    assert ("OrdersController.cs:15", "Database query") not in sinks
    assert sinks[("OrdersController.cs:24", "Deserialization")]
    auth = [fact for fact in result.facts if fact["fact_type"] == "auth_boundary"]
    assert any(fact["detail"].get("allows_anonymous") for fact in auth)
    dependencies = {
        fact["name"]: fact["detail"]["version"]
        for fact in result.facts
        if fact["fact_type"] == "dependency"
    }
    assert dependencies == {
        "Newtonsoft.Json": "12.0.1",
        "Microsoft.EntityFrameworkCore.SqlServer": "7.0.0",
        "log4net": "1.2.10",
    }
    kinds = [fact["fact_type"] for fact in result.facts]
    assert kinds.index("callable") > kinds.index("sensitive_operation")


def test_deep_parser_routes_for_other_languages(tmp_path):
    root = _write(
        tmp_path,
        {
            "server/app.js": "const app = express();\n"
            "app.get('/users/:id', show);\n"
            "function show(req, res) { db.query('SELECT ' + req.params.id); }\n",
            "web/client.ts": "class Api { load() { return this.http.get('/users/1'); } }\n",
            "cmd/main.go": "package main\n"
            'func main() { http.HandleFunc("GET /items", list) }\n'
            "func list(w http.ResponseWriter, r *http.Request) {}\n",
            "routes/web.php": "<?php Route::middleware('auth')->post('/orders', [OrderController::class, 'store']);\n",
            "config/routes.rb": "Rails.application.routes.draw do\n  get 'photos/:id', to: 'photos#show'\n  resources :users\nend\n",
            "vendor/lib/other.php": "<?php Route::get('/vendor', 'x');\n",
        },
    )
    result = extract_parser_facts(root)
    routes = {
        (fact["detail"]["method"], fact["path"])
        for fact in result.facts
        if fact["fact_type"] == "route"
    }
    assert {
        ("GET", "/users/:id"),
        ("GET", "/items"),
        ("POST", "/orders"),
        ("GET", "/photos/:id"),
        ("", "/users"),
    } <= routes
    assert ("GET", "/users/1") not in routes
    assert ("GET", "/vendor") not in routes
    show = next(
        fact
        for fact in result.facts
        if fact["fact_type"] == "callable" and fact["name"] == "show"
    )
    assert show["detail"]["reachability"] == "reachable"


def test_dotnet_deterministic_candidates(tmp_path):
    root = _write(tmp_path, _FILES)
    titles = {
        (candidate["title"], candidate["location"].rsplit("/", 1)[-1])
        for candidate in sast_semantic.deterministic_security_candidates(root)
    }
    assert ("Potential unsafe deserialization", "OrdersController.cs:24") in titles
    assert ("Debug mode enabled by source configuration", "Web.config:2") in titles
