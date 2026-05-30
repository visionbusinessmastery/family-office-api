from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def read(relative_path):
    return (REPO / relative_path).read_text(encoding="utf-8")


def fail(issues, label, detail):
    issues.append(f"FAIL {label}: {detail}")


def ok(lines, label):
    lines.append(f"PASS {label}")


def main():
    issues = []
    passes = []

    routes = read("family-office-api-main/advisor/routes.py")
    service = read("family-office-api-main/advisor/service.py")
    response_engine = read("family-office-api-main/advisor/ethan/response_engine.py")
    output_renderer = read("family-office-api-main/advisor/ethan/output_renderer.py")
    runtime_engine = read("family-office-api-main/advisor/ethan/runtime_engine.py")
    advisor_chat = read("components/dashboard/AdvisorChat.tsx")

    if 'ETHAN_GLOBAL_CACHE_VERSION = "v26-memory-priority"' in read("family-office-api-main/advisor/ethan/cache_policy.py"):
        ok(passes, "global cache version is v26-memory-priority")
    else:
        fail(issues, "cache", "ETHAN_GLOBAL_CACHE_VERSION must be v26-memory-priority")

    advisor_core_block = routes.split("def advisor_core", 1)[1].split("def advisor_legacy_route", 1)[0]
    if (
        "validate_ethan_frontend_contract" in advisor_core_block
        and '"result": result' not in advisor_core_block
        and '"input": message' not in advisor_core_block
    ):
        ok(passes, "/advisor/core returns validated analysis + metadata only")
    else:
        fail(issues, "advisor_core_contract", "/advisor/core must not expose input/system/result wrappers")

    if "render_ethan_output(" in service and '"analysis": rendered_text' in service:
        ok(passes, "service uses output renderer for final analysis")
    else:
        fail(issues, "service_renderer", "service.py must assign analysis from render_ethan_output")

    if "cognitive_variation" not in service and "output_variation" not in service:
        ok(passes, "no active variation layer in frozen pipeline")
    else:
        fail(issues, "variation_engine", "freeze pipeline forbids active variation layers")

    if 'return {"status": CORE_EMPTY_STATUS}' in response_engine and "Je " not in response_engine and "Tu " not in response_engine:
        ok(passes, "response engine fallback is data-only")
    else:
        fail(issues, "response_engine", "response_engine.py must not compose human fallback text")

    if not (REPO / "family-office-api-main/advisor/ethan/cognitive_variation_engine.py").exists():
        ok(passes, "cognitive variation engine removed during freeze")
    else:
        fail(issues, "variation_engine_file", "cognitive_variation_engine.py must stay removed in freeze phase")

    if "ETHAN_TEXT_ORIGIN" in output_renderer and "def render_ethan_output" in output_renderer:
        ok(passes, "output renderer is the sole Ethan text renderer")
    else:
        fail(issues, "output_renderer", "output_renderer.py must expose ETHAN_TEXT_ORIGIN and render_ethan_output")

    if 'ADVISOR_CACHE_VERSION = ETHAN_GLOBAL_CACHE_VERSION' in runtime_engine:
        ok(passes, "backend advisor cache follows global cache version")
    else:
        fail(issues, "advisor_cache", "ADVISOR_CACHE_VERSION must point to ETHAN_GLOBAL_CACHE_VERSION")

    if 'const CONVERSATION_CACHE_VERSION = "v26-memory-priority"' in advisor_chat:
        ok(passes, "frontend conversation cache follows global cache version")
    else:
        fail(issues, "frontend_cache", "AdvisorChat cache version must be v26-memory-priority")

    if "data.result" not in advisor_chat and "result?:" not in advisor_chat:
        ok(passes, "frontend consumes direct Ethan contract only")
    else:
        fail(issues, "frontend_contract", "AdvisorChat must not read legacy result.analysis contract")

    frontend_calls = []
    for relative in ["app", "components", "hooks", "lib"]:
        base = REPO / relative
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            if "/advisor/" in content or "/advisor" in content:
                frontend_calls.append((path.relative_to(REPO), content))

    bad_frontend_calls = [
        str(path)
        for path, content in frontend_calls
        if '"/advisor/core"' not in content
    ]
    if not bad_frontend_calls:
        ok(passes, "frontend advisor calls converge to /advisor/core")
    else:
        fail(issues, "frontend_calls", ", ".join(bad_frontend_calls))

    openai_imports = []
    for path in ROOT.rglob("*.py"):
        if "scripts" in path.parts:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if "from openai import" in content or "import openai" in content or "OpenAI(" in content:
            if path.as_posix().replace("\\", "/").endswith("advisor/ethan/openai_gateway.py"):
                continue
            openai_imports.append(str(path.relative_to(REPO)))
    if not openai_imports:
        ok(passes, "OpenAI access is isolated to Ethan gateway")
    else:
        fail(issues, "openai_gateway", ", ".join(openai_imports))

    print("ETHAN TEXT ORIGIN MAP")
    for line in passes:
        print(line)
    for issue in issues:
        print(issue)

    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
