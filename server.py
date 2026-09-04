import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agent
import paths
import tools

PUBLIC_DIR = Path(__file__).parent / "public"

app = FastAPI()

# In-memory, single-process session store: session_id -> messages list.
# Sessions are lost on restart and this doesn't scale past one server instance —
# an accepted tradeoff for shipping quickly, not a bug.
SESSIONS = {}


class ChatRequest(BaseModel):
    session_id: str
    user: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


def _get_session(session_id):
    if session_id not in SESSIONS:
        SESSIONS[session_id] = [{"role": "system", "content": agent.SYSTEM_PROMPT}]
    return SESSIONS[session_id]


@app.post("/api/chat")
def chat(request: ChatRequest):
    messages = _get_session(request.session_id)
    messages.append({"role": "user", "content": request.message})

    dispatch = tools.build_dispatch(paths.profile_path(request.user), paths.history_path(request.user))

    try:
        reply = agent.run_turn(messages, available_functions=dispatch, model=agent.MODEL)
    except Exception as error:
        messages.pop()
        return {"error": str(error)}

    return {"reply": reply}


@app.post("/api/reset")
def reset(request: ResetRequest):
    SESSIONS.pop(request.session_id, None)
    return {"ok": True}


# Mounted last so it only catches requests the routes above didn't match —
# serves index.html at "/" and style.css/app.js by their relative paths.
app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")


def main():
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))


if __name__ == "__main__":
    main()
