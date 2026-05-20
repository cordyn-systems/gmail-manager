from gmail_client import GmailClient


def test_html_to_text_exposes_unsubscribe_text() -> None:
    html = """
    <html>
      <body>
        <p>Appointment slots available this week.</p>
        <a href="https://example.com/unsubscribe">Unsubscribe</a>
      </body>
    </html>
    """

    text = GmailClient._html_to_text(html)

    assert "Appointment slots available" in text
    assert "Unsubscribe" in text

