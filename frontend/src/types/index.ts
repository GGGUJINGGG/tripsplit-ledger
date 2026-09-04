export type ExpenseCategory =
  | "food"
  | "hotel"
  | "transportation"
  | "gas"
  | "tickets"
  | "shopping"
  | "other";

export type ExpenseType = "shared" | "personal";

export type MemberRole = "owner" | "member";

export interface Participant {
  id: string;
  name: string;
  user_id?: string | null;
  role: MemberRole;
}

export interface PendingInvitation {
  id: string;
  trip_id: string;
  trip_name: string;
  invited_at: string;
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

export type TripUpdate = Partial<TripCreate>;

export interface ParticipantCreate {
  name: string;
}

export interface ParticipantInvite {
  email: string;
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

export interface CategorySpending {
  category: ExpenseCategory;
  amount: number;
}

export interface DailySpending {
  date: string;
  amount: number;
}

export interface PersonAmount {
  participant_id: string;
  name: string;
  amount: number;
}

export interface PersonBalance {
  participant_id: string;
  name: string;
  balance: number;
}

export interface DashboardSummary {
  total_trip_spending: number;
  spending_by_category: CategorySpending[];
  spending_by_day: DailySpending[];
  paid_by_person: PersonAmount[];
  owed_by_person: PersonAmount[];
  net_balances: PersonBalance[];
}

export interface User{
  id: string;
  email: string;
  display_name:string;
  created_at: string;
  updated_at: string;
}

export interface UserRegistration{
  email: string;
  password: string;
  display_name: string;
}

export interface UserLogin{
  email:string;
  password: string;
}

export interface AuthToken{
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}
