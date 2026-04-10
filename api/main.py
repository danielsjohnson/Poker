from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
import torch
from agent.agent import DQN
import os
import glob
import re


def get_highest_version_model(model_dir="models"):
    list_of_files = glob.glob(os.path.join(model_dir, "*.pth"))

    if not list_of_files:
        raise FileNotFoundError(f"No .pth model files found in {model_dir}")

    def extract_version(filepath):
        filename = os.path.basename(filepath)
        version_parts = re.findall(r'\d+', filename)
        return tuple(map(int, version_parts)) if version_parts else (0,)

    highest_version_file = max(list_of_files, key=extract_version)
    return highest_version_file

ml_models = {}
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Server Starting ---")
    print("Loading ML Models...")
    bot = DQN(input_size=44, output_size=7)
    model_path = get_highest_version_model()
    print(f"🚀 Deploying highest version found: {model_path}")
    bot.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    bot.eval()

    ml_models["poker_bot"] = bot
    print("ML Models Loaded.")
    yield

    ml_models.clear()
    print("server shutting down, resources cleaned up.")
    print("model cleared from memory")
app = FastAPI(lifespan=lifespan)



class GameState(BaseModel):
    state_vector: list[float]
    valid_actions: list[int]


@app.get("/")
def health_check():
    return {"status": "ok", "version": " 1.1 - Automated"}

@app.post("/get_action")
def get_bot_action(state: GameState):
    active_brain = ml_models.get("poker_bot")
    state_tensor = torch.tensor(state.state_vector, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        q_values = active_brain(state_tensor)
    mask = torch.tensor(state.valid_actions, dtype=torch.bool)
    q_values[0, ~mask] = -1e9
    action_index = q_values.argmax().item()
    action_names = ["Fold", "Check", "Call", "1/2 Pot", "3/4Pot", "Pot", "All-in"]
    calculated_action = action_names[action_index]

    return {
        "bot_action": calculated_action,
        "action_index": action_index
    }