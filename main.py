from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import openai
import sys
import os

openai.api_key = os.getenv('API_KEY')

app = FastAPI()



# middleware - allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # adjust to the frontend's URL
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)



# helper - objects

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



# helper - functions

def run_python_code(code: str) -> str:
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=5 
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out."
    except Exception as e:
        return f"Error: {str(e)}"

def get_hint(problem_statement, user_code, previous_hints=None):
    base_prompt = (
        f"""
        **Generating Progressive Hints for Code Improvement**

        **Context:**
        - **Problem Statement:** {problem_statement}
        - **User Code:** {user_code}

        **Goal:** Provide a clear, actionable hint that guides the user toward a more effective solution based on their current code. 

        ### Hint Generation Instructions:
        - **Clarity and Brevity:** Each hint should be concise (under 100 characters), easy to understand, and focused on a single actionable step.
        - **Progressive Guidance:** Build on previous hints to guide the user through sequential improvements. Avoid repeating advice.
        - **Code Optimization Focus:** Only suggest performance improvements if applicable; otherwise, explicitly state, "No further improvements are necessary."
        - If a specific optimization is feasible, recommend precise actions, such as data structure changes or algorithmic adjustments, to enhance efficiency.
        """
    )

    if previous_hints:
        base_prompt += f"""
        **Context:** 
        - **Previous Hints Provided:** {'; '.join(previous_hints)}

        ### Guidelines for Effective Hint Creation:
        1. **Avoid Redundancy:** Ensure each hint adds new insight without revisiting prior suggestions.
        2. **Leverage Past Hints:** Reference previous hints to create a coherent improvement trajectory.
        3. **Focus on Next Steps:** Target the immediate logical improvement that progresses the user toward a refined solution.
        """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful coding assistant. Always progress logically from prior hints."},
            {"role": "user", "content": base_prompt}
        ],
        max_tokens=100
    )

    return response.choices[0].message.content.strip()



# api endpoints

@app.post("/executeCode")
async def execute_code_api(request: CodeExecutionRequest):
    output = run_python_code(request.code)
    return {"output": output}

# @app.post("/runTestCase")
# async def run_test_case_api(request: TestCaseRequest):
#     # Inject test input into code by using input() replacements
#     code_with_input = f"""
#         import sys
#         from io import StringIO
#         sys.stdin = StringIO('{request.test_input}')
#         {request.code}
#     """
#     output = run_python_code(code_with_input)
#     return {"output": output}

@app.post("/getHint")
async def get_hint_api(request: HintRequest):
    try:
        hint = get_hint(
            problem_statement=request.problem_statement,
            user_code=request.user_code,
            previous_hints=request.previous_hints
        )
        return {"hint": hint}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))