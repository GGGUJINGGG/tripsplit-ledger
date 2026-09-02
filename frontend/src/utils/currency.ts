export const currencies = [
  { code: "USD", label: "USD (US Dollar)" },
  { code: "CNY", label: "CNY (Chinese Yuan)" },
  { code: "EUR", label: "EUR (Euro)" },
  { code: "GBP", label: "GBP (British Pound)" },
] as const;

export type CurrencyCode = (typeof currencies)[number]["code"];

export function normalizeCurrency(currency?: string | null): CurrencyCode {
  const normalized = currency?.toUpperCase();
  return currencies.some((item) => item.code === normalized)
    ? (normalized as CurrencyCode)
    : "USD";
}

export function formatMoney(currency: string, amount: number): string {
  return `${currency} ${amount.toFixed(2)}`;
}

export function formatMoneyItems(
  items: Array<{ currency: string; amount: number }>,
): string {
  if (items.length === 0) {
    return "USD 0.00";
  }
  return items.map((item) => formatMoney(item.currency, item.amount)).join(", ");
}

export function formatSignedMoney(currency: string, amount: number): string {
  const sign = amount > 0 ? "+" : amount < 0 ? "-" : "";
  return `${sign}${formatMoney(currency, Math.abs(amount))}`;
}
