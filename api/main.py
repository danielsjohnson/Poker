from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
import torch
from agent.agent import DQN


ml_models = {}
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Server Starting ---")
    print("Loading ML Models...")
    bot = DQN(input_size=44, output_size=7)
    bot.load_state_dict(torch.load("models/agent_v0_maniac.pth", map_location=torch.device('cpu')))
    bot.eval()

    ml_models["poker_bot"] = bot
    print("ML Models Loaded.")
    yield

    ml_models.clear()
    print("server shutting down, resources cleaned up.")
    print("model cleared from memory")
app = FastAPI(lifespan=lifespan)



class GameState(BaseModel):
    hand: list[str]
    community_cards: list[str]
    pot_size: int
    amount_to_call: int


@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/get_action")
def get_bot_action(state: GameState):
    active_brain = ml_models.get("poker_bot")
    print(f"Using model: {active_brain} to get action for state: {state}")

    calculated_action = "Raise"

    return {
        "bot_action": calculated_action,
        "explaination": active_brain
    }