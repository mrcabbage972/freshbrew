import re
from typing import List, Optional

from pydantic import BaseModel


class StepMeta(BaseModel):
    step_number: int
    duration: float  # in seconds
    input_tokens: int
    output_tokens: int


class Step(BaseModel):
    # This is the step number as found in the header block (e.g. "Step 1")
    header_step: int
    # The code that was executed (if any)
    code: Optional[str] = None
    # Any warning messages
    warnings: Optional[str] = None
    # Execution log output
    execution_logs: Optional[str] = None
    # A generic output line (if available)
    out: Optional[str] = None
    # Metadata extracted from the final line (e.g. duration and token counts)
    meta: StepMeta
    # New field to capture steps that only contain unstructured text (e.g. error messages)
    raw_text: Optional[str] = None


class Log(BaseModel):
    # Top header (e.g. the ASCII-art border with "New run")
    run_header: Optional[str] = None
    # A description or instruction (e.g. "Upgrade the project...")
    description: Optional[str] = None
    # A model or tool information line (e.g. "LiteLLMModel - gemini/gemini-2.0-flash")
    model_info: Optional[str] = None
    # All the step entries in the log
    steps: List[Step]


def parse_log(log_text: str) -> Log:
    # Find step delimiters (lines with many "━" and "Step <number>")
    step_delim_pattern = re.compile(r"^(━+.*Step\s+(\d+).*)$", re.MULTILINE)
    step_delims = list(step_delim_pattern.finditer(log_text))

    # Everything before the first step delimiter is considered the header block.
    header_text = log_text[: step_delims[0].start()] if step_delims else log_text

    # --- Parse header ---
    header_lines = header_text.splitlines()
    run_header = None
    description = None
    model_info = None

    # Assume the run header is on a line containing "New run"
    for line in header_lines:
        if "New run" in line:
            run_header = line.strip()
            break

    # Look for a description line that is nonempty and not part of a border
    for line in header_lines:
        stripped = line.strip("│").strip()
        if stripped and "New run" not in stripped and "─" not in stripped and "LiteLLMModel" not in stripped:
            description = stripped
            break

    # Look for model info (e.g. a line containing "LiteLLMModel")
    for line in header_lines:
        if "LiteLLMModel" in line:
            model_info = line.strip("╰─").strip()
            break

    # --- Parse each step ---
    steps = []
    for i, delim in enumerate(step_delims):
        # Determine the block for this step.
        start_index = delim.start()
        end_index = step_delims[i + 1].start() if i + 1 < len(step_delims) else len(log_text)
        step_text = log_text[start_index:end_index]

        # Extract the header step number (e.g. "Step 17")
        header_step = int(delim.group(2)) if delim.group(2) else i

        # Containers for capturing step details
        code_block = []
        warnings_lines = []
        execution_logs_lines = []
        out_line = None
        meta_obj = None

        state = None  # possible states: "code", "warnings", "logs"
        for line in step_text.splitlines():
            # Start of code block
            if "─ Executing parsed code:" in line:
                state = "code"
                continue
            # End a code block when hitting a border line
            if state == "code" and line.startswith("─") and set(line.strip()) in [set("─"), set("─ ")]:
                state = None
                continue
            # Switch state when warnings appear
            if line.startswith("Warning to user:"):
                state = "warnings"
            # Switch state when execution logs are indicated
            if line.startswith("Execution logs:"):
                state = "logs"
                continue
            # Capture output line
            if line.startswith("Out:"):
                out_line = line[len("Out:") :].strip()
                state = None
                continue
            # Look for metadata (duration, tokens, etc.)
            if re.match(r"\[Step\s+\d+:", line):
                meta_match = re.search(
                    r"\[Step\s+(\d+): Duration ([\d\.]+) seconds\| Input tokens: ([\d,]+) \| Output tokens: ([\d,]+)\]",
                    line,
                )
                if meta_match:
                    meta_obj = StepMeta(
                        step_number=int(meta_match.group(1)),
                        duration=float(meta_match.group(2)),
                        input_tokens=int(meta_match.group(3).replace(",", "")),
                        output_tokens=int(meta_match.group(4).replace(",", "")),
                    )
                continue

            # Accumulate lines based on the current state.
            if state == "code":
                code_block.append(line)
            elif state == "warnings":
                warnings_lines.append(line)
            elif state == "logs":
                execution_logs_lines.append(line)

        # If metadata wasn't found, assign a default meta.
        if not meta_obj:
            meta_obj = StepMeta(step_number=header_step, duration=0.0, input_tokens=0, output_tokens=0)

        # If nothing was captured in code, warnings, logs, or out, assume this is an unstructured step.
        raw_text = None
        if not code_block and not warnings_lines and not execution_logs_lines and not out_line:
            lines = step_text.splitlines()
            # Remove the header/delimiter line
            if len(lines) > 1:
                raw_text = "\n".join(lines[1:]).strip()
            else:
                raw_text = step_text.strip()

        step_obj = Step(
            header_step=header_step,
            code="\n".join(code_block).strip() if code_block else None,
            warnings="\n".join(warnings_lines).strip() if warnings_lines else None,
            execution_logs="\n".join(execution_logs_lines).strip() if execution_logs_lines else None,
            out=out_line,
            meta=meta_obj,
            raw_text=raw_text,
        )
        steps.append(step_obj)

    return Log(
        run_header=run_header,
        description=description,
        model_info=model_info,
        steps=steps,
    )


# --- Example usage ---
if __name__ == "__main__":
    # For demonstration purposes, 'log_text' should be set to the entire log content.
    log_text = r"""
╭────────────────────────────────────────────────────────────────────── New run ───────────────────────────────────────────────────────────────────────╮
│                                                                                                                                                      │
│ Upgrade the project to use JDK 17. Ensure that the build and the tests pass.                                                                         │
│                                                                                                                                                      │
╰─ LiteLLMModel - gemini/gemini-2.0-flash ─────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Step 1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ─ Executing parsed code: ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── 
  import os                                                                                                                                             
  print(os.getcwd())                                                                                                                                    
  files = list_dir(path=".")                                                                                                                            
  print(files)                                                                                                                                          
 ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── 
Warning to user: Code execution failed due to an unauthorized import - Consider passing said import under `additional_authorized_imports` when 
initializing your CodeAgent.
Code execution failed at line 'import os' due to: InterpreterError: Import of os is not allowed. Authorized imports are: ['itertools', 'statistics', 
'random', 'stat', 'collections', 'time', 'unicodedata', 'datetime', 're', 'queue', 'math']
[Step 0: Duration 9.61 seconds| Input tokens: 2,485 | Output tokens: 108]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Step 2 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ─ Executing parsed code: ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── 
  files = list_dir(path=".")                                                                                                                            
  print(files)                                                                                                                                          
 ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── 
Execution logs:
['Dockerfile', 'pom.xml', 'README.md', 'docker-compose.yml', 'bridge.sql', '.git', '.idea', 'src']

Out: None
[Step 1: Duration 0.64 seconds| Input tokens: 5,243 | Output tokens: 156]
    """
    parsed_log = parse_log(log_text)
    print(parsed_log.model_dump_json())
