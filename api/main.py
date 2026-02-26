from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "The Poker Bot API is online and waiting for hands."}