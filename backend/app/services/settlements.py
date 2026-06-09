from app.models import Trip
from app.schemas import Settlement, SettlementSummary
from app.services.calculations import cents_to_float, net_balances_cents


def simplify_settlements(trip: Trip) -> SettlementSummary:
    balances = net_balances_cents(trip)
    participants_by_id = {
        participant.id: participant.name for participant in trip.participants
    }

    debtors = [
        {"participant_id": participant_id, "amount": -balance}
        for participant_id, balance in balances.items()
        if balance < 0
    ]
    creditors = [
        {"participant_id": participant_id, "amount": balance}
        for participant_id, balance in balances.items()
        if balance > 0
    ]

    debtors.sort(key=lambda item: item["amount"], reverse=True)
    creditors.sort(key=lambda item: item["amount"], reverse=True)

    settlements: list[Settlement] = []
    debtor_index = 0
    creditor_index = 0

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor = debtors[debtor_index]
        creditor = creditors[creditor_index]
        payment_cents = min(debtor["amount"], creditor["amount"])

        if payment_cents > 0:
            settlements.append(
                Settlement(
                    from_participant_id=debtor["participant_id"],
                    from_name=participants_by_id[debtor["participant_id"]],
                    to_participant_id=creditor["participant_id"],
                    to_name=participants_by_id[creditor["participant_id"]],
                    amount=cents_to_float(payment_cents),
                )
            )

        debtor["amount"] -= payment_cents
        creditor["amount"] -= payment_cents

        if debtor["amount"] == 0:
            debtor_index += 1
        if creditor["amount"] == 0:
            creditor_index += 1

    return SettlementSummary(settlements=settlements)
