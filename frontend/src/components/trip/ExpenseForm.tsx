import { FormEvent, useEffect, useState } from "react";
import { Plus, Save, X } from "lucide-react";

import type { Expense, ExpenseCategory, ExpenseCreate, ExpenseType, Participant } from "../../types";
import { type CurrencyCode, currencies, normalizeCurrency } from "../../utils/currency";
import { categories } from "../../utils/expenses";

interface ExpenseFormProps {
  participants: Participant[];
  editingExpense: Expense | null;
  isSaving: boolean;
  onCancelEdit: () => void;
  onSubmit: (payload: ExpenseCreate) => Promise<boolean>;
}

export default function ExpenseForm({
  participants,
  editingExpense,
  isSaving,
  onCancelEdit,
  onSubmit,
}: ExpenseFormProps) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [paidBy, setPaidBy] = useState("");
  const [splitAmong, setSplitAmong] = useState<string[]>([]);
  const [expenseType, setExpenseType] = useState<ExpenseType>("shared");
  const [category, setCategory] = useState<ExpenseCategory>("food");
  const [date, setDate] = useState("");
  const [currency, setCurrency] = useState<CurrencyCode>("USD");
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (editingExpense) {
      setTitle(editingExpense.title);
      setAmount(String(editingExpense.amount));
      setPaidBy(editingExpense.paid_by);
      setSplitAmong(editingExpense.split_among);
      setExpenseType(editingExpense.expense_type ?? "shared");
      setCategory(editingExpense.category);
      setDate(editingExpense.date);
      setCurrency(normalizeCurrency(editingExpense.currency));
      setNote(editingExpense.note ?? "");
      setFormError(null);
      return;
    }

    resetFields();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingExpense]);

  useEffect(() => {
    if (editingExpense) return;
    if (!paidBy && participants[0]) {
      setPaidBy(participants[0].id);
    }
    if (splitAmong.length === 0 && participants.length > 0) {
      setSplitAmong(participants.map((participant) => participant.id));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [participants]);

  function resetFields() {
    setTitle("");
    setAmount("");
    setExpenseType("shared");
    setCategory("food");
    setDate("");
    setCurrency("USD");
    setNote("");
    setFormError(null);
    if (participants[0]) {
      setPaidBy(participants[0].id);
      setSplitAmong(participants.map((participant) => participant.id));
    } else {
      setPaidBy("");
      setSplitAmong([]);
    }
  }

  function toggleSplitParticipant(participantId: string) {
    setSplitAmong((current) =>
      current.includes(participantId)
        ? current.filter((id) => id !== participantId)
        : [...current, participantId],
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const parsedAmount = Number(amount);
    if (!title.trim()) {
      setFormError("Title is required.");
      return;
    }
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setFormError("Amount must be greater than 0.");
      return;
    }
    if (!paidBy) {
      setFormError("Paid by is required.");
      return;
    }
    if (expenseType === "shared" && splitAmong.length === 0) {
      setFormError("Select at least one person to share this expense.");
      return;
    }

    setFormError(null);
    const responsibleParticipants = expenseType === "personal" ? [paidBy] : splitAmong;
    const succeeded = await onSubmit({
      title: title.trim(),
      amount: parsedAmount,
      paid_by: paidBy,
      split_among: responsibleParticipants,
      expense_type: expenseType,
      category,
      date: date || new Date().toISOString().slice(0, 10),
      currency,
      note: note.trim() || undefined,
    });

    if (succeeded) {
      resetFields();
    }
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{editingExpense ? "Edit Expense" : "Add Expense"}</h2>
        {editingExpense ? (
          <button
            className="secondary-button"
            type="button"
            onClick={onCancelEdit}
            disabled={isSaving}
          >
            <X size={16} />
            Cancel
          </button>
        ) : null}
      </div>
      {formError ? <div className="alert">{formError}</div> : null}
      <form className="form-grid compact" onSubmit={handleSubmit}>
        <label htmlFor="expense-title">
          Title
          <input
            id="expense-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Dinner"
          />
        </label>
        <label htmlFor="expense-amount">
          Amount
          <input
            id="expense-amount"
            type="number"
            min="0"
            step="0.01"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="80.00"
          />
        </label>
        <label htmlFor="expense-paid-by">
          Paid by
          <select
            id="expense-paid-by"
            value={paidBy}
            onChange={(event) => {
              const nextPaidBy = event.target.value;
              setPaidBy(nextPaidBy);
              if (expenseType === "personal" && nextPaidBy) {
                setSplitAmong([nextPaidBy]);
              }
            }}
          >
            <option value="">Select payer</option>
            {participants.map((participant) => (
              <option key={participant.id} value={participant.id}>
                {participant.name}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="expense-type">
          Type
          <select
            id="expense-type"
            value={expenseType}
            onChange={(event) => {
              const nextType = event.target.value as ExpenseType;
              setExpenseType(nextType);
              if (nextType === "personal" && paidBy) {
                setSplitAmong([paidBy]);
              }
            }}
          >
            <option value="shared">Shared</option>
            <option value="personal">Personal</option>
          </select>
        </label>
        <label htmlFor="expense-category">
          Category
          <select
            id="expense-category"
            value={category}
            onChange={(event) => setCategory(event.target.value as ExpenseCategory)}
          >
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor="expense-date">
          Date
          <input
            id="expense-date"
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
          <span className="field-hint">Stored as YYYY-MM-DD.</span>
        </label>
        <label htmlFor="expense-currency">
          Currency
          <select
            id="expense-currency"
            value={currency}
            onChange={(event) => setCurrency(event.target.value as CurrencyCode)}
          >
            {currencies.map((item) => (
              <option key={item.code} value={item.code}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="wide-field" htmlFor="expense-note">
          Note
          <input
            id="expense-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional"
          />
        </label>
        <fieldset className="wide-field checkbox-field">
          <legend>Who should share this expense?</legend>
          {expenseType === "personal" ? (
            <p className="helper-text">
              Personal expenses are assigned only to the payer and do not affect
              settlements.
            </p>
          ) : (
            <>
              <p className="helper-text">
                The amount is split evenly across the selected people. The payer gets
                credit for paying upfront, and each selected person owes their share.
              </p>
              <div className="checkbox-grid">
                {participants.map((participant) => (
                  <label key={participant.id}>
                    <input
                      type="checkbox"
                      checked={splitAmong.includes(participant.id)}
                      onChange={() => toggleSplitParticipant(participant.id)}
                    />
                    {participant.name}
                  </label>
                ))}
              </div>
            </>
          )}
        </fieldset>
        <div className="form-actions wide-field">
          <button className="primary-button" type="submit" disabled={isSaving}>
            {editingExpense ? <Save size={18} /> : <Plus size={18} />}
            {editingExpense ? "Save changes" : "Add expense"}
          </button>
        </div>
      </form>
    </section>
  );
}
