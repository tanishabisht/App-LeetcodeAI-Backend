from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import openai
import sys
import os

openai.api_key = os.getenv('API_KEY')

app = FastAPI()

# Allow CORS for your frontend's origin (localhost:3000 for example)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust to the frontend's URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

class CodeExecutionRequest(BaseModel):
    code: str

class TestCaseRequest(BaseModel):
    code: str
    test_input: str

class HintRequest(BaseModel):
    problem_statement: str
    user_code: str
    hint_type: str = "logic"
    previous_hints: list = None

def run_python_code(code: str) -> str:
    try:
        # Run the code using subprocess in a sandboxed environment
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=5  # Limit execution time
        )
        print(result)
        return result.stdout if result.returncode == 0 else result.stderr
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out."
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/executeCode")
async def execute_code(request: CodeExecutionRequest):
    output = run_python_code(request.code)
    return {"output": output}

@app.post("/runTestCase")
async def run_test_case(request: TestCaseRequest):
    # Inject test input into code by using input() replacements
    code_with_input = f"""
        import sys
        from io import StringIO
        sys.stdin = StringIO('{request.test_input}')
        {request.code}
    """
    output = run_python_code(code_with_input)
    return {"output": output}

def get_hint_new_code(problem_statement, user_code, hint_type="logic", previous_hints=None):
    base_prompt = (
        f"""
        Problem Statement:
        {problem_statement}

        User Code:
        {user_code}

        Objective: Generate one clear, actionable hint based on the current user code.
        - The hint should address the {hint_type} of the code.
        - Use simple, direct language that is easy to understand and within 100 characters.
        - Build on previous hints (if any) to guide the user progressively towards an improved solution.
        - Each new hint should be unique and address the next logical improvement, avoiding repetition.
        """
    )

    if previous_hints:
        base_prompt += f"""
        Previous Hints:
        {'; '.join(previous_hints)}
        Hint Guidelines:
        - Avoid redundancy: Each hint should be a distinct step forward, building on previous hints.
        - Reference previous hints to ensure progression, helping the user advance without revisiting the same advice.
        """

    if hint_type == "logic":
        prompt = base_prompt + (
            """
            Hint Type: Logic Improvement
            - Provide a logical refinement to guide the user toward a clearer or more accurate solution.
            - Focus on one specific aspect of the code, suggesting a concrete way to improve clarity, correctness, or structure.
            - Avoid general advice: be precise, referencing specific lines or sections where possible.
            """
        )

    elif hint_type == "optimization":
        prompt = base_prompt + (
            """
            Hint Type: Optimization
            - Evaluate the code’s current efficiency and give hint only if it is possible to improve it.
            - If no time optimizations are required, clearly state "No further improvements are necessary."
            - For non-optimal code, suggest a specific change that would enhance time efficiency (like: recommend relevant data structures, algorithm adjustments)
            """
        )
    else:
        raise ValueError("Invalid hint_type. Choose 'logic' or 'optimization'.")

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful coding assistant. Always progress logically from prior hints."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100
    )

    return response.choices[0].message.content.strip()

@app.post("/getHint")
async def get_hint(request: HintRequest):
    try:
        hint = get_hint_new_code(
            problem_statement=request.problem_statement,
            user_code=request.user_code,
            hint_type=request.hint_type,
            previous_hints=request.previous_hints
        )
        return {"hint": hint}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))