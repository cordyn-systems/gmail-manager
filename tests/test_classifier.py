from classifier import classify_email, should_ignore_email
from models import EmailMessage


def make_email(subject: str, snippet: str = "", is_unread: bool = False) -> EmailMessage:
    return EmailMessage(
        message_id="msg-1",
        received_at="2026-05-08T09:00:00+05:30",
        sender_name="Customer",
        sender_email="customer@example.com",
        subject=subject,
        snippet=snippet,
        is_unread=is_unread,
    )


def test_classifies_appointment_request() -> None:
    result = classify_email(make_email("Need appointment", "Can I book a slot today?"))
    assert result.category == "Appointment Request"
    assert result.priority == "High"


def test_classifies_payment_follow_up() -> None:
    result = classify_email(make_email("Payment pending", "Invoice amount is due"))
    assert result.category == "Payment Follow-up"
    assert result.priority == "High"


def test_classifies_complaint() -> None:
    result = classify_email(make_email("Complaint", "There is no response and I am unhappy"))
    assert result.category == "Complaint / Issue"
    assert result.priority == "High"


def test_classifies_new_enquiry() -> None:
    result = classify_email(make_email("Interested in service", "Please send price details"))
    assert result.category == "New Enquiry"
    assert result.priority == "Medium"


def test_classifies_unread_as_needs_reply() -> None:
    result = classify_email(make_email("Hello", "Please check this", is_unread=True))
    assert result.category == "Needs Reply"


def test_other_defaults_to_low_priority() -> None:
    result = classify_email(make_email("Weekly update", "Thank you for the update"))
    assert result.category == "Other"
    assert result.priority == "Low"


def test_ignored_sender_defaults_to_other() -> None:
    email = EmailMessage(
        message_id="msg-2",
        received_at="2026-05-08T09:00:00+05:30",
        sender_name="Newsletter Bot",
        sender_email="no-reply@example.com",
        subject="Weekly business tips",
        snippet="Here is general information about services.",
    )
    result = classify_email(email)
    assert result.category == "Other"
    assert result.priority == "Low"
    assert should_ignore_email(email)


def test_ignores_automated_text() -> None:
    result = should_ignore_email(
        make_email("Weekly digest", "You can unsubscribe or manage your preferences.")
    )
    assert result is True
