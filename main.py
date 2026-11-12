from __future__ import annotations

import ast
import math
import operator
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from groq import AsyncGroq
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.templating import Jinja2Templates


limiter = Limiter(key_func=get_remote_address, default_limits=[])
app = FastAPI(title="Math Helper", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Only basic arithmetic is permitted; input is parsed as an expression, never eval'd.
_BINARY_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _calculate_node(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = node.value
        if abs(value) > 1e100:
            raise ValueError("Numbers must be smaller than 1e100.")
        return value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        left = _calculate_node(node.left)
        right = _calculate_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponents must be between -100 and 100.")
        result = _BINARY_OPS[type(node.op)](left, right)
        if isinstance(result, complex) or not math.isfinite(result) or abs(result) > 1e100:
            raise ValueError("That calculation is outside the supported range.")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_calculate_node(node.operand))
    raise ValueError("Use numbers, parentheses, and +, -, *, /, //, %, or ** only.")


def calculate(expression: str) -> float | int:
    if not expression.strip() or len(expression) > 200:
        raise ValueError("Enter an expression up to 200 characters long.")
    try:
        tree = ast.parse(expression, mode="eval")
        return _calculate_node(tree.body)
    except (SyntaxError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Please check the expression and try again.") from exc


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/calculate")
@limiter.limit("20/hour")
async def calculate_api(request: Request) -> JSONResponse:
    try:
        body = await request.json()
        expression = body.get("expression", "")
        if not isinstance(expression, str):
            raise ValueError("Expression must be text.")
        result = calculate(expression)
        return JSONResponse({"result": result})
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except (TypeError, AttributeError):
        return JSONResponse({"error": "Send a JSON object with an expression."}, status_code=400)


@app.post("/api/ask")
@limiter.limit("20/hour")
async def ask_ai(request: Request) -> JSONResponse:
    body = await request.json()
    question = body.get("question", "") if isinstance(body, dict) else ""
    if not isinstance(question, str) or not question.strip():
        return JSONResponse({"error": "Enter a math question first."}, status_code=400)
    if len(question) > 2000:
        return JSONResponse({"error": "Questions must be 2,000 characters or fewer."}, status_code=400)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return JSONResponse(
            {"error": "AI help is not configured yet. Add GROQ_API_KEY in your hosting environment."},
            status_code=503,
        )

    try:
        client = AsyncGroq(api_key=api_key)
        response = await client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a friendly math tutor. Explain the solution step by step, "
                        "show the key reasoning clearly, and point out the final answer. "
                        "If the question is not about math, politely ask for a math question."
                    ),
                },
                {"role": "user", "content": question.strip()},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        answer = response.choices[0].message.content or "I couldn't generate an explanation."
        return JSONResponse({"answer": answer})
    except Exception:
        # Do not expose provider details or credentials to site visitors.
        return JSONResponse({"error": "The AI assistant is temporarily unavailable. Please try again."}, status_code=502)
