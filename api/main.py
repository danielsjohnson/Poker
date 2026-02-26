from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")


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
    print(f"Recieved hand: {state.hand} with pot: {state.pot_size}")

    return {
        "bot_action": "Raise",
        "explaination": "Dummy Response."
    }