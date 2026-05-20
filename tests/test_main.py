from main import build_rows
from appointment_llm import AppointmentDecision
from models import EmailMessage


class FakeAppointmentAnalyzer:
    calls = 0

    def analyze(self, email: EmailMessage) -> AppointmentDecision:
        self.calls += 1
        is_appointment = email.message_id == "action-1"
        return AppointmentDecision(
            appointment_related=is_appointment,
            category="Appointment Request" if is_appointment else "Not Appointment",
            summary="Customer wants an appointment." if is_appointment else "Not appointment related.",
            pending_action="Confirm the appointment slot." if is_appointment else "",
            priority="High" if is_appointment else "Low",
            reason="Test fixture",
        )


def test_build_rows_only_adds_appointment_messages_to_action_list() -> None:
    emails = [
        EmailMessage(
            message_id="action-1",
            received_at="2026-05-09T10:00:00+05:30",
            sender_name="Customer",
            sender_email="customer@example.com",
            subject="Need appointment today",
            snippet="Can I book a slot?",
        ),
        EmailMessage(
            message_id="ignored-1",
            received_at="2026-05-09T10:05:00+05:30",
            sender_name="Newsletter Bot",
            sender_email="no-reply@example.com",
            subject="Weekly digest",
            snippet="You can unsubscribe any time.",
        ),
    ]

    analyzer = FakeAppointmentAnalyzer()
    action_items, processed_emails, ignored_count = build_rows(emails, analyzer)

    assert len(action_items) == 1
    assert action_items[0].gmail_message_id == "action-1"
    assert len(processed_emails) == 2
    assert ignored_count == 1
    assert processed_emails[1].category == "Ignored / Automated"
    assert analyzer.calls == 1


def test_build_rows_ignores_unsubscribe_body_before_llm() -> None:
    analyzer = FakeAppointmentAnalyzer()
    emails = [
        EmailMessage(
            message_id="auto-1",
            received_at="2026-05-09T10:00:00+05:30",
            sender_name="Brand Updates",
            sender_email="hello@example.com",
            subject="Available appointment offers",
            snippet="Book today and save.",
            body_preview="You are receiving this email because you subscribed. Unsubscribe here.",
        )
    ]

    action_items, processed_emails, ignored_count = build_rows(emails, analyzer)

    assert action_items == []
    assert ignored_count == 1
    assert processed_emails[0].category == "Ignored / Automated"
    assert analyzer.calls == 0
