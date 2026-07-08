from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4
import json
from pathlib import Path
from urllib import error, request

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
from engine.game import Game
from engine.player import Player
from engine.table import Table
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


ACTION_NAMES = ["Fold", "Check", "Call", "1/2 Pot", "3/4 Pot", "Pot", "All-in"]
STREET_NAMES = {
    0: "Pre-flop",
    1: "Flop",
    2: "Turn",
    3: "River",
}

ml_models = {}
game_sessions = {}
ENABLE_LOCAL_BOT = os.getenv("POKER_ENABLE_LOCAL_BOT", "").lower() in {"1", "true", "yes"}
FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Server Starting ---")
    if ENABLE_LOCAL_BOT:
        import torch
        from agent.agent import DQN

        print("Loading local ML model...")
        bot = DQN(input_size=47, output_size=7)
        model_path = get_highest_version_model()
        print(f"Deploying highest version found: {model_path}")
        bot.load_state_dict(torch.load(model_path, map_location=torch.device('cpu'), weights_only=True))
        bot.eval()

        ml_models["poker_bot"] = bot
        ml_models["active_model_path"] = model_path
        print("Local ML model loaded.")
    else:
        print("Local ML model disabled. Bot actions will use POKER_BOT_API_URL.")
    yield

    ml_models.clear()
    print("server shutting down, resources cleaned up.")
    print("model/session resources cleared from memory")


app = FastAPI(lifespan=lifespan)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "POKER_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials="*" not in allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GameState(BaseModel):
    state_vector: list[float]
    valid_actions: list[int]


class StartPokerGameRequest(BaseModel):
    stack_size: int = 1000


class HumanActionRequest(BaseModel):
    action_index: int
    bet_amount: int | None = None


class BotInferenceError(Exception):
    pass


@dataclass
class PokerSession:
    session_id: str
    table: Table
    game: Game
    human: Player
    bot: Player
    stack_size: int
    hand_number: int = 0
    hand_start_chips: dict[str, int] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    last_bot_response: dict[str, Any] | None = None
    bot_error: str | None = None


@app.get("/")
def health_check():
    if FRONTEND_DIST.exists():
        return FileResponse(FRONTEND_DIST / "index.html")
    return {"status": "ok", "version": "1.2 - game server"}


@app.get("/health")
def health_check_json():
    return {
        "status": "ok",
        "version": "1.2 - game server",
        "local_bot_enabled": ENABLE_LOCAL_BOT,
        "remote_bot_configured": bool(bot_action_url()),
        "frontend_dist": FRONTEND_DIST.exists(),
    }


@app.get("/model-info")
async def get_model_info():
    return {
        "active_model": ml_models.get("active_model_path"),
        "local_bot_enabled": ENABLE_LOCAL_BOT,
        "remote_bot_configured": bool(bot_action_url()),
        "status": "online",
        "deployment_type": "game-server"
    }


@app.post("/get_action")
def get_bot_action(state: GameState):
    if not ENABLE_LOCAL_BOT:
        raise HTTPException(status_code=404, detail="Local inference is disabled for this deployment")
    import torch

    if len(state.state_vector) != 47:
        raise HTTPException(status_code=400, detail="state_vector must contain 47 values")
    if len(state.valid_actions) != len(ACTION_NAMES):
        raise HTTPException(status_code=400, detail="valid_actions must contain 7 values")

    active_brain = ml_models.get("poker_bot")
    if active_brain is None:
        raise HTTPException(status_code=503, detail="Poker bot model is not loaded")

    state_tensor = torch.tensor(state.state_vector, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        q_values = active_brain(state_tensor)
    mask = torch.tensor(state.valid_actions, dtype=torch.bool)
    q_values[0, ~mask] = -1e9
    action_index = q_values.argmax().item()
    calculated_action = ACTION_NAMES[action_index]

    return {
        "bot_action": calculated_action,
        "action_index": action_index
    }


def create_session(stack_size: int) -> PokerSession:
    if stack_size < 100:
        raise HTTPException(status_code=400, detail="stack_size must be at least 100")

    table = Table()
    game = Game(table)
    human = Player("You", table)
    bot = Player("PokerBot", table)
    human.chips = stack_size
    bot.chips = stack_size
    game.players = [human, bot]

    session = PokerSession(
        session_id=str(uuid4()),
        table=table,
        game=game,
        human=human,
        bot=bot,
        stack_size=stack_size,
    )
    deal_new_hand(session)
    game_sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> PokerSession:
    session = game_sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Game session not found")
    return session


def deal_new_hand(session: PokerSession) -> None:
    for player in session.game.players:
        if player.chips <= 0:
            player.chips = session.stack_size

    session.hand_number += 1
    session.hand_start_chips = {
        "human": session.human.chips,
        "bot": session.bot.chips,
    }
    session.history = []
    session.last_bot_response = None
    session.bot_error = None
    session.game.reset()
    session.history.append({
        "actor": "Dealer",
        "role": "dealer",
        "action": "Deal",
        "actionIndex": None,
        "street": current_street(session),
        "amount": 0,
        "potAfter": session.table.pot,
    })


def current_street(session: PokerSession) -> str:
    if session.game.hand_over:
        return "Hand over"
    return STREET_NAMES.get(session.game.street, "Showdown")


def current_role(session: PokerSession) -> str | None:
    if session.game.hand_over or not session.game.active:
        return None

    player = session.game.active[session.game.current_player_index]
    if player is session.human:
        return "human"
    if player is session.bot:
        return "bot"
    return None


def current_player(session: PokerSession) -> Player | None:
    if session.game.hand_over or not session.game.active:
        return None
    return session.game.active[session.game.current_player_index]


def serialize_card(card: Any) -> dict[str, str]:
    return {
        "rank": card.rank,
        "suit": card.suit,
        "code": str(card),
    }


def player_status(session: PokerSession, player: Player) -> str:
    if player not in session.game.active:
        return "folded"
    if session.game.hand_over:
        return "showdown"
    if player.all_in:
        return "all-in"
    if current_player(session) is player:
        return "acting"
    return "waiting"


def serialize_player(session: PokerSession, player: Player, role: str) -> dict[str, Any]:
    reveal_cards = role == "human" or session.game.hand_over
    hand_name = None
    if session.game.hand_over and player in session.game.active and len(player.hand) == 2:
        from engine.hand_detection import Hand_Detection
        judge = Hand_Detection()
        try:
            detected = judge.find_hand(player.hand, session.table.community)
            hand_name = detected[0]
        except Exception:
            pass

    return {
        "id": role,
        "name": player.name,
        "role": role,
        "chips": player.chips,
        "betInRound": player.bet_in_round,
        "totalBet": player.total_bet,
        "isButton": bool(session.game.isButton(player)),
        "status": player_status(session, player),
        "cards": [serialize_card(card) for card in player.hand] if reveal_cards else [],
        "cardCount": len(player.hand),
        "handName": hand_name,
    }


def legal_actions_for_human(session: PokerSession) -> list[int]:
    if current_role(session) != "human":
        return [0] * len(ACTION_NAMES)
    return session.game.get_valid_actions()


def hand_result(session: PokerSession) -> dict[str, Any] | None:
    if not session.game.hand_over:
        return None

    human_delta = session.human.chips - session.hand_start_chips.get("human", session.human.chips)
    bot_delta = session.bot.chips - session.hand_start_chips.get("bot", session.bot.chips)

    if human_delta > bot_delta:
        winner = "human"
        message = f"You won {human_delta} chips"
    elif bot_delta > human_delta:
        winner = "bot"
        message = f"PokerBot won {bot_delta} chips"
    else:
        winner = "split"
        message = "Split pot"

    return {
        "winner": winner,
        "humanDelta": human_delta,
        "botDelta": bot_delta,
        "message": message,
    }


def serialize_session(session: PokerSession) -> dict[str, Any]:
    amount_to_call = 0 if session.game.hand_over else max(0, session.table.current_bet - session.human.bet_in_round)
    can_bet_or_raise = not session.game.hand_over and any(legal_actions_for_human(session)[3:6])
    min_raise = max(session.game.last_raise_amount, session.game.bigBlind_Bet)
    min_bet_amount = min(session.human.chips, amount_to_call + min_raise)
    max_bet_amount = session.human.chips
    half_pot_amount = min(max_bet_amount, max(min_bet_amount, amount_to_call + int(session.table.pot * 0.5)))
    three_quarter_pot_amount = min(max_bet_amount, max(min_bet_amount, amount_to_call + int(session.table.pot * 0.75)))
    pot_amount = min(max_bet_amount, max(min_bet_amount, amount_to_call + session.table.pot))

    return {
        "sessionId": session.session_id,
        "handNumber": session.hand_number,
        "street": current_street(session),
        "pot": session.table.pot,
        "currentBet": session.table.current_bet,
        "amountToCall": amount_to_call,
        "currentPlayerRole": current_role(session),
        "players": [
            serialize_player(session, session.human, "human"),
            serialize_player(session, session.bot, "bot"),
        ],
        "communityCards": [serialize_card(card) for card in session.table.community],
        "availableActions": {
            "mask": legal_actions_for_human(session),
            "labels": ACTION_NAMES,
            "betSizing": {
                "enabled": can_bet_or_raise,
                "min": min_bet_amount if can_bet_or_raise else 0,
                "max": max_bet_amount if can_bet_or_raise else 0,
                "halfPot": half_pot_amount if can_bet_or_raise else 0,
                "threeQuarterPot": three_quarter_pot_amount if can_bet_or_raise else 0,
                "pot": pot_amount if can_bet_or_raise else 0,
            },
        },
        "history": session.history[-20:],
        "isHandOver": session.game.hand_over,
        "result": hand_result(session),
        "botError": session.bot_error,
        "lastBotResponse": session.last_bot_response,
    }


def bot_action_url() -> str:
    raw_url = os.getenv("POKER_BOT_API_URL", "").strip()
    if not raw_url:
        return ""
    if raw_url.startswith("http:") and not raw_url.startswith("http://"):
        raw_url = f"http://{raw_url.removeprefix('http:').lstrip('/')}"
    if raw_url.startswith("https:") and not raw_url.startswith("https://"):
        raw_url = f"https://{raw_url.removeprefix('https:').lstrip('/')}"
    if raw_url.rstrip("/").endswith("/get_action"):
        return raw_url
    return f"{raw_url.rstrip('/')}/get_action"


def remote_bot_action(state_vector: list[float], valid_actions: list[int]) -> dict[str, Any]:
    url = bot_action_url()
    if not url:
        if ENABLE_LOCAL_BOT:
            return get_bot_action(GameState(state_vector=state_vector, valid_actions=valid_actions))
        raise BotInferenceError("POKER_BOT_API_URL is required when local bot inference is disabled")

    payload = json.dumps({
        "state_vector": state_vector,
        "valid_actions": valid_actions,
    }).encode("utf-8")
    post_request = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    timeout = float(os.getenv("POKER_BOT_TIMEOUT_SECONDS", "8"))
    try:
        with request.urlopen(post_request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise BotInferenceError(f"Bot API returned HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise BotInferenceError(f"Could not reach bot API at {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise BotInferenceError(f"Bot API timed out after {timeout} seconds") from exc
    except json.JSONDecodeError as exc:
        raise BotInferenceError("Bot API returned invalid JSON") from exc


def validate_bot_action(response: dict[str, Any], valid_actions: list[int]) -> int:
    try:
        action_index = int(response["action_index"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BotInferenceError("Bot API response did not include a valid action_index") from exc

    if action_index < 0 or action_index >= len(ACTION_NAMES):
        raise BotInferenceError(f"Bot returned out-of-range action index {action_index}")
    if not valid_actions[action_index]:
        raise BotInferenceError(f"Bot returned illegal action {ACTION_NAMES[action_index]}")
    return action_index


def record_action(session: PokerSession, actor: Player, role: str, action_index: int) -> bool:
    chips_before = actor.chips
    amount_to_call = max(0, session.table.current_bet - actor.bet_in_round)
    street = current_street(session)
    _, _, done = session.game.step(action_index)
    spent = max(0, chips_before - actor.chips)
    session.history.append({
        "actor": actor.name,
        "role": role,
        "action": ACTION_NAMES[action_index],
        "actionIndex": action_index,
        "street": street,
        "amount": spent if spent else amount_to_call,
        "potAfter": session.table.pot,
    })
    return done


def apply_custom_bet(session: PokerSession, bet_amount: int) -> bool:
    game = session.game
    player = game.active[game.current_player_index]
    amount_to_call = max(0, game.table.current_bet - player.bet_in_round)
    min_raise = max(game.last_raise_amount, game.bigBlind_Bet)
    min_total_cost = min(player.chips, amount_to_call + min_raise)

    if bet_amount < min_total_cost:
        raise HTTPException(status_code=400, detail=f"Bet amount must be at least {min_total_cost}")
    if bet_amount > player.chips:
        raise HTTPException(status_code=400, detail=f"Bet amount cannot exceed stack size {player.chips}")

    chips_before = player.chips
    street = current_street(session)
    total_cost = min(bet_amount, player.chips)
    actual_raise = max(0, total_cost - amount_to_call)

    if game.tracker:
        game.tracker.on_action(player.name, game.street, 5, amount_to_call)

    player.updateChips(-total_cost)
    player.bet_in_round += total_cost
    game.table.updatePot(total_cost)
    game.isAllIn(player)

    if player.bet_in_round > game.table.current_bet:
        game.last_raise_amount = actual_raise
        game.last_raiser = player
        game.table.current_bet = player.bet_in_round

    game.incrementTurn()
    if game.check_endRound():
        game.advance_street()

    done = False
    if len(game.active) == 1 or game.street > 3:
        game.end_game()
        done = True

    spent = max(0, chips_before - player.chips)
    session.history.append({
        "actor": player.name,
        "role": "human",
        "action": "Bet/Raise",
        "actionIndex": 5,
        "street": street,
        "amount": spent,
        "potAfter": session.table.pot,
    })
    return done


def resolve_bot_turns(session: PokerSession, max_turns: int = 20) -> None:
    session.bot_error = None
    turns = 0

    while not session.game.hand_over and turns < max_turns:
        role = current_role(session)
        if role == "bot":
            state_vector = session.game.get_state()
            valid_actions = session.game.get_valid_actions()
            response = remote_bot_action(state_vector, valid_actions)
            action_index = validate_bot_action(response, valid_actions)
            session.last_bot_response = {
                "botAction": response.get("bot_action", ACTION_NAMES[action_index]),
                "actionIndex": action_index,
            }
            record_action(session, session.bot, "bot", action_index)
            turns += 1
            continue

        if role == "human" and session.human.chips <= 0:
            valid_actions = session.game.get_valid_actions()
            legal_actions = [idx for idx, allowed in enumerate(valid_actions) if allowed]
            if not legal_actions:
                break
            record_action(session, session.human, "human", legal_actions[0])
            turns += 1
            continue

        break

    if turns >= max_turns:
        raise BotInferenceError("Bot turn resolution exceeded the safety limit")


@app.post("/game/start")
def start_poker_game(body: StartPokerGameRequest | None = None):
    body = body or StartPokerGameRequest()
    session = create_session(body.stack_size)
    try:
        resolve_bot_turns(session)
    except BotInferenceError as exc:
        session.bot_error = str(exc)
    return serialize_session(session)


@app.get("/game/{session_id}")
def get_poker_game(session_id: str):
    return serialize_session(get_session(session_id))


@app.post("/game/{session_id}/action")
def submit_human_action(session_id: str, body: HumanActionRequest):
    session = get_session(session_id)

    if session.game.hand_over:
        raise HTTPException(status_code=409, detail="The hand is already over")
    if current_role(session) != "human":
        raise HTTPException(status_code=409, detail="It is not the human player's turn")

    valid_actions = session.game.get_valid_actions()
    if body.action_index < 0 or body.action_index >= len(ACTION_NAMES):
        raise HTTPException(status_code=400, detail="action_index is out of range")
    if not valid_actions[body.action_index]:
        raise HTTPException(status_code=400, detail=f"{ACTION_NAMES[body.action_index]} is not legal now")

    if body.bet_amount is not None:
        if body.action_index not in [3, 4, 5]:
            raise HTTPException(status_code=400, detail="bet_amount can only be used with bet or raise actions")
        apply_custom_bet(session, body.bet_amount)
    else:
        record_action(session, session.human, "human", body.action_index)
    try:
        resolve_bot_turns(session)
    except BotInferenceError as exc:
        session.bot_error = str(exc)
    return serialize_session(session)


@app.post("/game/{session_id}/bot-turn")
def retry_bot_turn(session_id: str):
    session = get_session(session_id)
    try:
        resolve_bot_turns(session)
    except BotInferenceError as exc:
        session.bot_error = str(exc)
    return serialize_session(session)


@app.post("/game/{session_id}/new-hand")
def start_next_hand(session_id: str):
    session = get_session(session_id)
    deal_new_hand(session)
    try:
        resolve_bot_turns(session)
    except BotInferenceError as exc:
        session.bot_error = str(exc)
    return serialize_session(session)


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{full_path:path}")
def serve_react_app(full_path: str):
    if not FRONTEND_DIST.exists():
        raise HTTPException(status_code=404, detail="Frontend build is not available")

    requested_path = FRONTEND_DIST / full_path
    if requested_path.is_file():
        return FileResponse(requested_path)
    return FileResponse(FRONTEND_DIST / "index.html")
