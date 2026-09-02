import json
import subprocess
import tempfile
from pathlib import Path
from ..missions.types import TestCase, CamelModel

START_MARKER = "###RESULTS_START###"
END_MARKER = "###RESULTS_END###"

# Appended after the student's own code, in the same file, so it runs in the
# same module namespace and can see whatever function the student defined.
# It never decides pass/fail based on anything a model said - it calls the
# student's function directly and compares the real return value to the
# expected one.
HARNESS = """
import json, io, contextlib

def __tutor_run__():
    results = []
    func = globals().get(__TUTOR_FUNC__)
    if func is None:
        return {"loadError": f"No function named {__TUTOR_FUNC__} was found.", "results": []}
    for t in __TUTOR_TESTS__:
        entry = {"input": t["input"], "expected": t["expected"]}
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                entry["actual"] = func(*t["input"])
            entry["passed"] = entry["actual"] == t["expected"]
        except Exception as e:
            entry["actual"] = None
            entry["passed"] = False
            entry["error"] = f"{type(e).__name__}: {e}"
        results.append(entry)
    return {"loadError": None, "results": results}

print("%s")
print(json.dumps(__tutor_run__()))
print("%s")
""" % (START_MARKER, END_MARKER)


class TestOutcome(CamelModel):
    input: list
    expected: object
    actual: object = None
    passed: bool
    error: str | None = None


class RunResult(CamelModel):
    load_error: str | None
    results: list[TestOutcome]
    all_passed: bool


def run_python_tests(
    student_code: str,
    function_name: str,
    tests: list[TestCase],
    timeout_seconds: float = 5.0,
) -> RunResult:
    """
    Runs student-submitted Python against a fixed set of test cases and returns
    a deterministic pass/fail per test. This is the ONLY thing in the system
    allowed to decide whether an answer is correct - no model output ever
    overrides it.

    Safety note for anyone deploying this beyond a local demo: this runs the
    process with a timeout and Python's isolated mode (-I), but it is NOT a
    hardened sandbox. It shares the host filesystem/network. For a real
    multi-student deployment, run this inside a locked-down container (gVisor,
    Firecracker, nsjail, a disposable Docker container with --network=none)
    instead of a bare subprocess.
    """
    tests_json = json.dumps([t.model_dump(by_alias=False) for t in tests])
    script = (
        f"{student_code}\n\n"
        f"__TUTOR_FUNC__ = {json.dumps(function_name)}\n"
        f"__TUTOR_TESTS__ = {tests_json}\n"
        f"{HARNESS}"
    )

    with tempfile.TemporaryDirectory(prefix="tutor-") as tmpdir:
        script_path = Path(tmpdir) / "student.py"
        script_path.write_text(script, encoding="utf-8")

        try:
            proc = subprocess.run(
                ["python3", "-I", str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            stdout, stderr = proc.stdout, proc.stderr
            timed_out = False
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            timed_out = True

        start_idx = stdout.find(START_MARKER)
        end_idx = stdout.find(END_MARKER)

        if start_idx == -1 or end_idx == -1:
            last_line = next(
                (line for line in reversed(stderr.strip().splitlines()) if line),
                "The code could not be run.",
            )
            return RunResult(
                load_error=(
                    "Your code took too long to run (possible infinite loop)."
                    if timed_out
                    else last_line
                ),
                results=[],
                all_passed=False,
            )

        json_slice = stdout[start_idx + len(START_MARKER) : end_idx].strip()
        try:
            parsed = json.loads(json_slice)
            results = [TestOutcome(**r) for r in parsed.get("results", [])]
            load_error = parsed.get("loadError")
            return RunResult(
                load_error=load_error,
                results=results,
                all_passed=load_error is None and len(results) > 0 and all(r.passed for r in results),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return RunResult(load_error="Could not read test results.", results=[], all_passed=False)
