from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import openai
import sys

openai.api_key = "YOUR_OPENAI_API_KEY"

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
