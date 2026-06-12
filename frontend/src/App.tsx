import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Cpu, Loader2, Play, RotateCcw, User } from "lucide-react";
import { dealNextHand, retryBotTurn, startGame, submitAction } from "./api/client";
import type { Card, GameSnapshot, PlayerView } from "./types/game";

const redSuits = new Set(["H", "D"]);

function App() {
  const [game, setGame] = useState<GameSnapshot | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Animation states
  const [animateHeroBet, setAnimateHeroBet] = useState(false);
  const [animateOpponentBet, setAnimateOpponentBet] = useState(false);
  const [animateSweep, setAnimateSweep] = useState(false);
  const [animatePotWin, setAnimatePotWin] = useState<"human" | "bot" | "split" | null>(null);

  const prevGameRef = useRef<GameSnapshot | null>(null);

  useEffect(() => {
    if (!game) {
      prevGameRef.current = null;
      return;
    }

    let t1: ReturnType<typeof setTimeout> | undefined;
    let t2: ReturnType<typeof setTimeout> | undefined;
    let t3: ReturnType<typeof setTimeout> | undefined;
    let t4: ReturnType<typeof setTimeout> | undefined;

    if (prevGameRef.current && prevGameRef.current.sessionId === game.sessionId) {
      const prevHero = prevGameRef.current.players.find((p) => p.role === "human");
      const prevBot = prevGameRef.current.players.find((p) => p.role === "bot");
      const currHero = game.players.find((p) => p.role === "human");
      const currBot = game.players.find((p) => p.role === "bot");

      const prevHeroBet = prevHero?.betInRound ?? 0;
      const prevBotBet = prevBot?.betInRound ?? 0;
      const currHeroBet = currHero?.betInRound ?? 0;
      const currBotBet = currBot?.betInRound ?? 0;

      // 1. Bet increase
      if (currHeroBet > prevHeroBet) {
        setAnimateHeroBet(true);
        t1 = setTimeout(() => setAnimateHeroBet(false), 600);
      }
      if (currBotBet > prevBotBet) {
        setAnimateOpponentBet(true);
        t2 = setTimeout(() => setAnimateOpponentBet(false), 600);
      }

      // 2. Pot sweep
      const potIncreased = game.pot > prevGameRef.current.pot;
      const hadBets = prevHeroBet > 0 || prevBotBet > 0;
      const betsCleared = currHeroBet === 0 && currBotBet === 0;

      if (potIncreased && hadBets && betsCleared) {
        setAnimateSweep(true);
        t3 = setTimeout(() => setAnimateSweep(false), 850);
      }

      // 3. Pot win
      const handJustEnded = game.isHandOver && !prevGameRef.current.isHandOver;
      if (handJustEnded && game.result?.winner) {
        setAnimatePotWin(game.result.winner);
        t4 = setTimeout(() => setAnimatePotWin(null), 1200);
      }
    }

    prevGameRef.current = game;

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, [game]);

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
            {/* Sweep Animation */}
            {animateSweep && (
              <div className="pot-sweep-container">
                <div className="sweep-chip hero-sweep-1" />
                <div className="sweep-chip hero-sweep-2" />
                <div className="sweep-chip hero-sweep-3" />
                <div className="sweep-chip opponent-sweep-1" />
                <div className="sweep-chip opponent-sweep-2" />
                <div className="sweep-chip opponent-sweep-3" />
              </div>
            )}

            {/* Pot Win Animation */}
            {animatePotWin && (
              <div className="pot-win-container">
                <div className={`win-chip chip-1 winner-${animatePotWin}`} />
                <div className={`win-chip chip-2 winner-${animatePotWin}`} />
                <div className={`win-chip chip-3 winner-${animatePotWin}`} />
                <div className={`win-chip chip-4 winner-${animatePotWin}`} />
                <div className={`win-chip chip-5 winner-${animatePotWin}`} />
              </div>
            )}

            <div className="table-zone opponent-zone">
              {pokerBot && (
                <Seat
                  player={pokerBot}
                  position="opponent"
                  animateBet={animateOpponentBet}
                  isWinner={Boolean(game?.isHandOver && (game.result?.winner === "bot" || game.result?.winner === "split"))}
                  isSplit={game?.result?.winner === "split"}
                  isHandOver={game?.isHandOver}
                />
              )}
            </div>

            <div className="table-zone board-zone">
              <div className="board-row">
                <div className="pot-spacer" aria-hidden="true" />
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
              {human && (
                <Seat
                  player={human}
                  position="hero"
                  animateBet={animateHeroBet}
                  isWinner={Boolean(game?.isHandOver && (game.result?.winner === "human" || game.result?.winner === "split"))}
                  isSplit={game?.result?.winner === "split"}
                  isHandOver={game?.isHandOver}
                />
              )}
            </div>
          </div>
          {game && <ActionLog key={game.history.length} game={game} />}
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

function Seat({
  player,
  position,
  animateBet = false,
  isWinner = false,
  isSplit = false,
  isHandOver = false,
}: {
  player: PlayerView;
  position: "opponent" | "hero";
  animateBet?: boolean;
  isWinner?: boolean;
  isSplit?: boolean;
  isHandOver?: boolean;
}) {
  const cards = position === "opponent"
    ? player.cards.length
      ? player.cards
      : Array.from({ length: player.cardCount || 2 }, () => undefined)
    : player.cards;

  return (
    <section className={`seat ${position} ${player.status === "acting" ? "acting" : ""} ${player.status === "all-in" ? "all-in" : ""} ${player.status === "folded" ? "folded" : ""} ${isWinner ? "winner" : ""}`}>
      {position === "hero" && <RoundBet amount={player.betInRound} />}
      <div className="seat-row">
        {player.isButton && <span className="position-marker" aria-label="Dealer button">D</span>}
        
        {player.status === "all-in" && (
          <div className="all-in-plaque" aria-label="All-in plaque">
            <div className="all-in-text">
              <div>ALL</div>
              <div>IN</div>
            </div>
          </div>
        )}

        {player.status === "folded" && (
          <div className="fold-stamp" aria-hidden="true">
            FOLD
          </div>
        )}

        {isWinner && (
          <div className="winner-badge" aria-label="Winner badge">
            {isSplit ? "SPLIT POT" : "WINNER"}
            {player.handName && <span className="winner-hand-desc"> • {player.handName}</span>}
          </div>
        )}

        {isHandOver && !isWinner && player.status !== "folded" && player.handName && (
          <div className="hand-badge" aria-label="Showdown hand">
            {player.handName}
          </div>
        )}

        <div className="seat-cards">
          {cards.map((card, index) => (
            <PlayingCard
              key={card ? card.code : `${player.id}-hidden-${index}`}
              card={card}
              hidden={position === "opponent" && !card}
              dealIndex={index}
            />
          ))}
        </div>
        <div className="seat-stack">
          <div className="seat-avatar" aria-hidden="true">
            {position === "opponent" ? <Cpu size={16} /> : <User size={16} />}
          </div>
          <div className="seat-details">
            <strong>{position === "opponent" ? "Opponent" : "You"}</strong>
            <span>{player.chips}</span>
          </div>
        </div>
      </div>
      {position === "opponent" && <RoundBet amount={player.betInRound} />}

      {/* Bet Animation Chips */}
      {animateBet && (
        <div className="flying-chips-container">
          <div className="flying-chip chip-1" />
          <div className="flying-chip chip-2" />
          <div className="flying-chip chip-3" />
        </div>
      )}
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
  const lastEvent = game.history
    .filter((event) => event.role !== "dealer")
    .slice(-1)[0] ?? null;

  const getActionClass = (action: string) => {
    const act = action.toLowerCase();
    if (act.includes("fold")) return "action-fold";
    if (act.includes("check") || act.includes("call")) return "action-passive";
    return "action-aggressive"; // bet, raise, all-in, pot, etc.
  };

  return (
    <aside className="action-log" aria-label="Latest action">
      <strong>Latest Action</strong>
      {lastEvent ? (
        <div className={`latest-action-badge ${getActionClass(lastEvent.action)}`}>
          <span className="actor-name">{lastEvent.role === "bot" ? "Opponent" : "You"}</span>
          <p className="action-value">
            {lastEvent.action}
            {lastEvent.amount > 0 ? ` ${lastEvent.amount}` : ""}
          </p>
        </div>
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

const suitSymbols: Record<string, string> = {
  H: "♥",
  D: "♦",
  C: "♣",
  S: "♠",
};

function PlayingCard({
  card,
  hidden = false,
  placeholder = false,
  isBoardCard = false,
  boardIndex = 0,
  dealIndex,
}: {
  card?: Card;
  hidden?: boolean;
  placeholder?: boolean;
  isBoardCard?: boolean;
  boardIndex?: number;
  dealIndex?: number;
}) {
  const cardStyle = isBoardCard
    ? ({ "--deal-delay": `${boardIndex * 90}ms` } as CSSProperties)
    : dealIndex !== undefined
      ? ({ "--deal-delay": `${dealIndex * 120}ms` } as CSSProperties)
      : undefined;

  if (hidden) {
    return (
      <div
        className="card card-back player-card"
        aria-label="Face-down card"
        style={cardStyle}
      />
    );
  }

  if (!card) {
    return <div className={`card empty-card ${placeholder ? "board-placeholder" : ""}`} aria-label="Empty card slot" />;
  }

  const symbol = suitSymbols[card.suit] ?? card.suit;

  return (
    <div
      className={`card card-face suit-${card.suit.toLowerCase()} ${redSuits.has(card.suit) ? "red" : "black"} ${isBoardCard ? "board-card" : "player-card"}`}
      style={cardStyle}
    >
      <div className="card-corner top-left">
        <span className="card-rank">{card.rank}</span>
        <span className="card-suit">{symbol}</span>
      </div>
      <div className="card-center-suit">{symbol}</div>
      <div className="card-corner bottom-right">
        <span className="card-rank">{card.rank}</span>
        <span className="card-suit">{symbol}</span>
      </div>
    </div>
  );
}

export default App;
