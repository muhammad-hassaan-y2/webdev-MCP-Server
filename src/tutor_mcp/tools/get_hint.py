import os
import httpx
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from ..missions.registry import get_mission
from ..sandbox.run_python import run_python_tests
from ..sandbox.physics import check_simulation_answer

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = (
    "You are a patient tutor. You are given a concept, what the student is "
    "currently trying, and REAL results that were computed deterministically "
    "(not by you). Never claim something passed or failed yourself - only refer "
    "to the ground truth you were given. Give ONE short Socratic hint (2-3 "
    "sentences) that nudges the student toward the answer without stating it "
    "outright."
)


FALLBACK_MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest"),
    "gemini-flash-lite-latest",
    "gemini-pro-latest",
    "gemini-flash-latest",
]


async def _call_gemini_for_hint(
    concept: str, description: str, context: str, ground_truth: str, attempt_number: int
) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    user_text = (
        f"Concept: {concept}\n"
        f"Mission: {description}\n"
        f"Attempt number: {attempt_number}\n"
        f"Student's current state:\n{context}\n\n"
        f"Ground truth (computed deterministically, not by you):\n{ground_truth}"
    )

    body = {
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {"maxOutputTokens": 200},
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        for model in FALLBACK_MODELS:
            try:
                resp = await client.post(
                    GEMINI_URL_TMPL.format(model=model),
                    params={"key": api_key},
                    json=body,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    return text
            except (httpx.HTTPError, KeyError, IndexError, ValueError):
                continue
    return None


def register_get_hint(server: MCPServer) -> None:
    @server.tool(
        name="get_hint",
        description=(
            "Generates a Socratic hint for a student who is stuck on a mission "
            "(code or simulation). Grounds the hint in real, deterministically "
            "computed results - the AI never guesses whether something is right, "
            "it only explains results that were already computed."
        ),
    )
    async def get_hint(
        missionId: str,
        code: str | None = None,
        params: dict[str, float] | None = None,
        studentAnswer: float | None = None,
        attemptNumber: int = 1,
    ) -> CallToolResult:
        """
        Args:
            missionId: The mission id.
            code: Current code, for code missions.
            params: Current parameter values, for simulation missions.
            studentAnswer: The student's current numeric answer, if any (simulation missions).
            attemptNumber: Which attempt this is, starting at 1.
        """
        mission = get_mission(missionId)

        if mission.type == "code":
            student_code = code or mission.starter_code
            run = run_python_tests(student_code, mission.function_name, mission.tests)
            context = f"Code:\n{student_code}"
            if run.load_error:
                ground_truth = f"Load error: {run.load_error}"
            else:
                ground_truth = "\n".join(
                    f"f({', '.join(map(str, r.input))}) expected {r.expected!r}, "
                    f"got {r.actual!r} -> {'PASS' if r.passed else 'FAIL'}"
                    + (f" ({r.error})" if r.error else "")
                    for r in run.results
                )
        else:
            p = params or {spec.key: spec.default for spec in mission.params}
            context = f"Chosen parameters: {p}, student answer: {studentAnswer if studentAnswer is not None else '(not yet submitted)'}"
            if studentAnswer is not None:
                result = check_simulation_answer(missionId, p, studentAnswer)
                ground_truth = (
                    f"Actual value (computed, not guessed): {result.actual:.2f} "
                    f"-> {'PASS' if result.passed else 'FAIL'}"
                )
            else:
                ground_truth = "Student hasn't submitted an answer yet."

        ai_hint = await _call_gemini_for_hint(
            mission.concept, mission.description, context, ground_truth, attemptNumber
        )
        hint = ai_hint or mission.fallback_hints[min(attemptNumber - 1, len(mission.fallback_hints) - 1)]

        return CallToolResult(
            content=[TextContent(type="text", text=hint)],
            structured_content={"hint": hint, "source": "ai" if ai_hint else "fallback"},
            is_error=False,
        )
