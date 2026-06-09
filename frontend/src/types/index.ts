export type ExpenseCategory =
  | "food"
  | "hotel"
  | "transportation"
  | "gas"
  | "tickets"
  | "shopping"
  | "other";

export type ExpenseType = "shared" | "personal";

export interface Participant {
  id: string;
  name: string;
}

export interface Expense {
  id: string;
  trip_id: string;
  title: string;
  amount: number;
  paid_by: string;
  split_among: string[];
  expense_type?: ExpenseType;
  category: ExpenseCategory;
  date: string;
  currency?: string | null;
  note?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Trip {
  id: string;
  name: string;
  start_date: string;
  end_date?: string | null;
  participants: Participant[];
  expenses: Expense[];
  created_at: string;
  updated_at: string;
}

export interface TripCreate {
  name: string;
  start_date: string;
  end_date?: string;
}

export interface ParticipantCreate {
  name: string;
}

export interface ExpenseCreate {
  title: string;
  amount: number;
  paid_by: string;
  split_among: string[];
  expense_type: ExpenseType;
  category: ExpenseCategory;
  date: string;
  currency?: string;
  note?: string;
}

export type ExpenseUpdate = Partial<ExpenseCreate>;

export interface Settlement {
  from_participant_id: string;
  from_name: string;
  to_participant_id: string;
  to_name: string;
  amount: number;
}

export interface SettlementSummary {
  settlements: Settlement[];
}
