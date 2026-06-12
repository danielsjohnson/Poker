export type Suit = "H" | "D" | "C" | "S";
export type Rank = "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "J" | "Q" | "K" | "A";
export type SeatRole = "human" | "bot" | "dealer";
export type PlayerStatus = "acting" | "waiting" | "all-in" | "folded" | "showdown";

export interface Card {
  rank: Rank;
  suit: Suit;
  code: string;
}

export interface PlayerView {
  id: string;
  name: string;
  role: Exclude<SeatRole, "dealer">;
  chips: number;
  betInRound: number;
  totalBet: number;
  isButton: boolean;
  status: PlayerStatus;
  cards: Card[];
  cardCount: number;
}

export interface AvailableActions {
  mask: number[];
  labels: string[];
  betSizing: {
    enabled: boolean;
    min: number;
    max: number;
    halfPot: number;
    threeQuarterPot: number;
    pot: number;
  };
}

export interface GameActionEvent {
  actor: string;
  role: SeatRole;
  action: string;
  actionIndex: number | null;
  street: string;
  amount: number;
  potAfter: number;
}

export interface HandResult {
  winner: "human" | "bot" | "split";
  humanDelta: number;
  botDelta: number;
  message: string;
}

export interface BotResponse {
  botAction: string;
  actionIndex: number;
}

export interface GameSnapshot {
  sessionId: string;
  handNumber: number;
  street: string;
  pot: number;
  currentBet: number;
  amountToCall: number;
  currentPlayerRole: "human" | "bot" | null;
  players: PlayerView[];
  communityCards: Card[];
  availableActions: AvailableActions;
  history: GameActionEvent[];
  isHandOver: boolean;
  result: HandResult | null;
  botError: string | null;
  lastBotResponse: BotResponse | null;
}
