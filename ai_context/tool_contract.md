\# NativeClaw Tool Contract \& Session Handling



This document defines the expected behavior of tools used with NativeClaw and how the system should handle their outputs. Adhering to this contract ensures consistency, predictability, and a smooth user experience.



\## 1. Tool Output Contract



Every tool (a script declared via `tool.yaml`) must follow these rules when invoked.



\### 1.1 Exit Codes

\- \*\*0\*\*: Tool executed successfully. This includes cases where the tool found issues (e.g., violations) – as long as the tool itself didn't crash.

\- \*\*Non-zero\*\*: Tool failed to execute (missing dependencies, invalid arguments, internal error). NativeClaw will treat this as a step failure and abort the session.



\### 1.2 Output Modes

Tools support two output modes, determined by the presence of an `input\_format: json` field in the capability definition (which tells NativeClaw to pass inputs as a JSON string) and optionally a `--json` command‑line flag for manual use.



\#### Human‑readable mode (default when run manually)

\- Print descriptive messages to stdout/stderr.

\- May create output files (reports, logs) in well‑known locations (e.g., `ai\_context/`).

\- Should include a final message indicating where any saved files are located.



\#### JSON mode (when used in a NativeClaw goal with `input\_format: json` or with `--json` flag)

\- \*\*Only\*\* print a single JSON object on stdout. No other output (no progress messages, no debug prints). All internal prints should be suppressed.

\- The JSON object must contain at least the following fields:

&nbsp; - `status`: `"success"` or `"error"`. If `"error"`, include an `error` field with a message.

&nbsp; - `saved\_files`: list of paths (relative to project root) that the tool created or modified during this run.

&nbsp; - `data`: any additional structured data relevant to the tool's purpose (e.g., `violation\_count`, `report\_data`). This data can be used by subsequent steps.

\- Example:

&nbsp; ```json

&nbsp; {

&nbsp;   "status": "success",

&nbsp;   "saved\_files": \["ai\_context/guardrail\_violations.json"],

&nbsp;   "data": {

&nbsp;     "violation\_count": 2,

&nbsp;     "summary": "Found violations in world/dm\_chat\_handler.py and world/session\_system.py"

&nbsp;   }

&nbsp; }

1.3 Side Effects

Tools may create or modify files. All such files should be listed in saved\_files (relative to project root).



Temporary files should be cleaned up; only artifacts intended for the user should persist.



2\. NativeClaw Session Enhancements

NativeClaw will be extended to respect this contract and preserve valuable outputs.



2.1 Step Output Capture

When a tool is invoked with input\_format: json, NativeClaw will attempt to parse its stdout as JSON.



If successful, the parsed object is stored in the session context and also saved to:

.nativeclaw/sessions/<session>/outputs/step\_<n>.json



If parsing fails, the raw stdout is captured as a string and logged (for debugging).



2.2 Artifact Collection

If the JSON contains a saved\_files list, each listed file is copied to:

.nativeclaw/sessions/<session>/artifacts/ (preserving relative path structure).



The original file paths are recorded so that later steps can refer to them (e.g., via previous.step\_name.artifacts).



2.3 Review Trigger

After all steps have executed, NativeClaw will decide whether to prompt for review (unless -y/--yes was used). The review is offered if any of the following is true:



Files were changed (git diff is non‑empty).



Any step produced non‑empty JSON output (i.e., useful data was generated).



Any artifacts were saved.



The prompt message will summarize:



Number of files changed (if any).



Number of steps that produced output.



Path to the session folder (where all outputs and artifacts are stored).



2.4 Resume Command Enhancements

When resuming a session, the resume command will display:



A summary of step outputs (e.g., "Step 1: found 2 violations, report saved to artifacts/...").



The file diff (if any) as before.



The location of the session folder.



3\. Implementation Example: Guardrails Tool

We will update tools/guardrails/run.py to follow the contract:



Modify check\_ai\_contract to accept a quiet parameter. When quiet=True, suppress all print statements and instead collect the results to return.



Return a dictionary containing violation\_count and the saved file path (if any).



In main():



If JSON mode is detected (via input\_format: json), call check\_ai\_contract(quiet=True), then print a JSON object with status, saved\_files, and data.



Otherwise, call it with quiet=False (allowing prints) and after execution, print a human‑readable message including the saved file location.



4\. Example Workflow

bash

\# Run a goal that uses guardrails

python tools/nativeclaw/nativeclaw.py semantic goals/check\_guardrails.yaml



\# After execution, even though no files changed, you'll be prompted:

\# "Review outputs? \[Y]es \[N]o: "

\# If you say Y, you'll see:

\#   Step 1 produced output: found 2 violations (saved to artifacts/guardrail\_violations.json)

\#   No files were changed.

\#   Session folder: .nativeclaw/sessions/20260219\_232832/

5\. Benefits

Consistency: All tools behave the same way, making them easier to use and debug.



Preservation: Valuable outputs are never lost; they are stored in session archives.



Clarity: Users always know where results are saved, and the system guides them.



Extensibility: New tools can be added without special‑case handling.

