import { type CSSProperties, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Loader2, Play, RotateCcw } from "lucide-react";
import { dealNextHand, retryBotTurn, startGame, submitAction } from "./api/client";
import type { Card, GameSnapshot, PlayerView } from "./types/game";

const redSuits = new Set(["H", "D"]);

function App() {
  const [game, setGame] = useState<GameSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadNewGame() {
    setError(null);
    setIsLoading(true);
    try {
      setGame(await startGame());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start game");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadNewGame();
  }, []);

  const human = useMemo(() => game?.players.find((player) => player.role === "human") ?? null, [game]);
  const pokerBot = useMemo(() => game?.players.find((player) => player.role === "bot") ?? null, [game]);
  const boardCards: Array<Card | undefined> = Array.from({ length: 5 }, (_, index) => game?.communityCards[index]);
  const isActionLocked = isLoading || busyAction !== null || game?.currentPlayerRole !== "human" || Boolean(game?.botError);

  async function handleAction(actionIndex: number, betAmount?: number) {
    if (!game || isActionLocked) {
      return;
    }

    setError(null);
    setBusyAction(actionIndex);
    try {
      setGame(await submitAction(game.sessionId, actionIndex, betAmount));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleNextHand() {
    if (!game) {
      return;
    }

    setError(null);
    setIsLoading(true);
    try {
      setGame(await dealNextHand(game.sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not deal next hand");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRetryBot() {
    if (!game) {
      return;
    }

    setError(null);
    setIsLoading(true);
    try {
      setGame(await retryBotTurn(game.sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resolve bot turn");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="arena-shell">
      <header className="arena-header">
        <div>
          <p>Poker Bot Arena</p>
          <h1>{game?.street ?? "Loading"}</h1>
        </div>
        <button className="reset-button" type="button" onClick={loadNewGame} disabled={isLoading}>
          {isLoading ? <Loader2 className="spin" size={18} /> : <RotateCcw size={18} />}
          New game
        </button>
      </header>

      {(error || game?.botError) && (
        <section className="error-banner" role="alert">
          <AlertTriangle size={18} />
          <span>{error ?? game?.botError}</span>
          {game?.botError && (
            <button type="button" onClick={handleRetryBot} disabled={isLoading}>
              Retry bot
            </button>
          )}
        </section>
      )}

      <section className="felt-table" aria-live="polite">
        <div className="table-rail">
          <div className="table-layout">
            <div className="table-zone opponent-zone">
              {pokerBot && <Seat player={pokerBot} position="opponent" />}
            </div>

            <div className="table-zone board-zone">
              <div className="board-row">
                <div className="community-cards">
                  {boardCards.map((card, index) => (
                    <PlayingCard
                      key={card ? card.code : `board-${index}`}
                      card={card}
                      placeholder
                      boardIndex={index}
                      isBoardCard
                    />
                  ))}
                </div>
                <div className="pot-chip">
                  <span>Pot</span>
                  <strong>{game?.pot ?? 0}</strong>
                </div>
              </div>
            </div>

            <div className="table-zone hero-zone">
              {human && <Seat player={human} position="hero" />}
            </div>
          </div>
          {game && <ActionLog game={game} />}
        </div>
      </section>

      <ActionDock
        game={game}
        busyAction={busyAction}
        isLoading={isLoading}
        isLocked={isActionLocked}
        onAction={handleAction}
        onNextHand={handleNextHand}
      />
    </main>
  );
}

function Seat({ player, position }: { player: PlayerView; position: "opponent" | "hero" }) {
  const cards = position === "opponent"
    ? player.cards.length
      ? player.cards
      : Array.from({ length: player.cardCount || 2 }, () => undefined)
    : player.cards;

  return (
    <section className={`seat ${position} ${player.status === "acting" ? "acting" : ""}`}>
      {position === "hero" && <RoundBet amount={player.betInRound} />}
      <div className="seat-row">
        {player.isButton && <span className="position-marker" aria-label="Dealer button">D</span>}
        <div className="seat-cards">
          {cards.map((card, index) => (
            <PlayingCard
              key={card ? card.code : `${player.id}-hidden-${index}`}
              card={card}
              hidden={position === "opponent" && !card}
            />
          ))}
        </div>
        <div className="seat-stack">
          <strong>{position === "opponent" ? "Opponent" : "You"}</strong>
          <span>{player.chips}</span>
        </div>
      </div>
      {position === "opponent" && <RoundBet amount={player.betInRound} />}
    </section>
  );
}

function RoundBet({ amount }: { amount: number }) {
  return (
    <div className={`round-bet ${amount > 0 ? "" : "empty"}`} aria-label={`Current round bet ${amount}`}>
      <span>Bet</span>
      <strong>{amount}</strong>
    </div>
  );
}

function ActionLog({ game }: { game: GameSnapshot }) {
  const events = game.history
    .filter((event) => event.role !== "dealer")
    .slice(-5)
    .reverse();

  return (
    <aside className="action-log" aria-label="Recent actions">
      <strong>Action</strong>
      {events.length ? (
        <ol>
          {events.map((event, index) => (
            <li key={`${event.actor}-${event.street}-${event.action}-${index}`}>
              <span>{event.role === "bot" ? "Opponent" : "You"}</span>
              <p>
                {event.action}
                {event.amount > 0 ? ` ${event.amount}` : ""}
              </p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="empty-log">No actions yet</p>
      )}
    </aside>
  );
}

function ActionDock({
  game,
  busyAction,
  isLoading,
  isLocked,
  onAction,
  onNextHand,
}: {
  game: GameSnapshot | null;
  busyAction: number | null;
  isLoading: boolean;
  isLocked: boolean;
  onAction: (actionIndex: number, betAmount?: number) => void;
  onNextHand: () => void;
}) {
  const betSizing = game?.availableActions.betSizing ?? {
    enabled: false,
    min: 0,
    max: 0,
    halfPot: 0,
    threeQuarterPot: 0,
    pot: 0,
  };
  const [betAmount, setBetAmount] = useState(betSizing.min);

  useEffect(() => {
    if (!betSizing.enabled) {
      return;
    }
    setBetAmount((currentAmount) => {
      if (currentAmount < betSizing.min || currentAmount > betSizing.max) {
        return betSizing.min;
      }
      return currentAmount;
    });
  }, [betSizing.enabled, betSizing.min, betSizing.max]);

  if (!game) {
    return (
      <footer className="action-dock">
        <div className="dock-status">
          <Loader2 className="spin" size={18} />
          Loading table
        </div>
      </footer>
    );
  }

  if (game.isHandOver) {
    return (
      <footer className="action-dock">
        <div className="dock-status">{game.result?.message ?? "Hand over"}</div>
        <button className="dock-button primary" type="button" onClick={onNextHand} disabled={isLoading}>
          {isLoading ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
          Deal next hand
        </button>
      </footer>
    );
  }

  const immediateActions = game.availableActions.mask
    .map((allowed, index) => (allowed && ![3, 4, 5].includes(index) ? index : -1))
    .filter((index) => index >= 0);
  const wagerVerb = game.amountToCall > 0 ? "Raise" : "Bet";
  const canSlide = betSizing.enabled && betSizing.max > betSizing.min;

  return (
    <footer className="action-dock">
      <div className="dock-status">
        <strong>
          {busyAction !== null || isLoading
            ? "Loading"
            : game.currentPlayerRole === "human"
              ? "Your action"
              : "Waiting"}
        </strong>
        <span>To call: {game.amountToCall}</span>
      </div>
      <div className="dock-actions">
        {immediateActions.map((actionIndex) => (
          <button
            className={`dock-button ${actionIndex === 6 ? "all-in" : ""}`}
            type="button"
            key={actionIndex}
            onClick={() => onAction(actionIndex)}
            disabled={isLocked}
          >
            {busyAction === actionIndex && <Loader2 className="spin" size={16} />}
            {actionLabel(game, actionIndex)}
          </button>
        ))}
      </div>
      {betSizing.enabled && (
        <div className="bet-control">
          <div className="bet-control-topline">
            <strong>{wagerVerb}</strong>
            <span>{betAmount}</span>
          </div>
          <input
            aria-label={`${wagerVerb} amount`}
            className="bet-slider"
            type="range"
            min={betSizing.min}
            max={betSizing.max}
            step="1"
            value={betAmount}
            onChange={(event) => setBetAmount(Number(event.target.value))}
            disabled={isLocked || !canSlide}
          />
          <div className="snap-actions">
            <button type="button" onClick={() => setBetAmount(betSizing.halfPot)} disabled={isLocked}>
              1/2 Pot
            </button>
            <button type="button" onClick={() => setBetAmount(betSizing.threeQuarterPot)} disabled={isLocked}>
              3/4 Pot
            </button>
            <button type="button" onClick={() => setBetAmount(betSizing.pot)} disabled={isLocked}>
              Pot
            </button>
          </div>
          <button
            className="dock-button wager-submit"
            type="button"
            onClick={() => onAction(5, betAmount)}
            disabled={isLocked}
          >
            {busyAction === 5 && <Loader2 className="spin" size={16} />}
            {wagerVerb} {betAmount}
          </button>
        </div>
      )}
    </footer>
  );
}

function actionLabel(game: GameSnapshot, actionIndex: number): string {
  const label = game.availableActions.labels[actionIndex] ?? `Action ${actionIndex}`;
  if (label === "Call" && game.amountToCall > 0) {
    return `Call ${game.amountToCall}`;
  }
  return label;
}

function PlayingCard({
  card,
  hidden = false,
  placeholder = false,
  isBoardCard = false,
  boardIndex = 0,
}: {
  card?: Card;
  hidden?: boolean;
  placeholder?: boolean;
  isBoardCard?: boolean;
  boardIndex?: number;
}) {
  const boardStyle = isBoardCard ? ({ "--deal-delay": `${boardIndex * 90}ms` } as CSSProperties) : undefined;

  if (hidden) {
    return <div className="card card-back" aria-label="Face-down card" />;
  }

  if (!card) {
    return <div className={`card empty-card ${placeholder ? "board-placeholder" : ""}`} aria-label="Empty card slot" />;
  }

  return (
    <div
      className={`card card-face ${redSuits.has(card.suit) ? "red" : "black"} ${isBoardCard ? "board-card" : ""}`}
      style={boardStyle}
    >
      <span>{card.rank}</span>
      <strong>{card.suit}</strong>
    </div>
  );
}

export default App;
