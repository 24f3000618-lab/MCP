import hashlib
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI()

EMAIL = "24f3000618@ds.study.iitm.ac.in".strip().lower()

TOOL = {
    "name": "solve_challenge",
    "description": "Returns the exam answer for the current challenge header.",
    "inputSchema": {"type": "object", "properties": {}},
}


def handle(msg: dict, headers) -> dict | None:
    method = msg.get("method")
    msg_id = msg.get("id")

    # Notifications have no id and need no reply
    if msg_id is None:
        return None

    if method == "initialize":
        client_version = (msg.get("params") or {}).get("protocolVersion", "2025-03-26")
        result = {
            "protocolVersion": client_version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "exam-server", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call":
        challenge = headers.get("x-exam-challenge", "")
        if not challenge:
            result = {
                "content": [{"type": "text", "text": "missing X-Exam-Challenge header"}],
                "isError": True,
            }
        else:
            digest = hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]
            result = {"content": [{"type": "text", "text": digest}]}
    elif method == "ping":
        result = {}
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


@app.post("/")
@app.post("/mcp")
async def mcp(request: Request):
    body = await request.json()
    if isinstance(body, list):  # batch support, just in case
        replies = [r for m in body if (r := handle(m, request.headers))]
        return JSONResponse(replies) if replies else Response(status_code=202)
    reply = handle(body, request.headers)
    if reply is None:
        return Response(status_code=202)
    return JSONResponse(reply)


@app.get("/")
async def health():
    return {"status": "ok"}