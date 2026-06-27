from pathlib import Path

from docs_for_me.core.content_signals import analyze_content


def test_analyze_content_infers_purpose_from_generic_signals() -> None:
    content = """
const title = "Bookings"
const emptyMessage = "No bookings found"

function searchBookings() {}
function updatePaymentStatus() {}

fetch("/api/bookings")
fetch("/api/payments")
"""

    signals = analyze_content(Path("app/bookings/page.tsx"), content, "TypeScript React")

    assert "bookings" in signals.domain_terms
    assert "payments" in signals.domain_terms
    assert "search" in signals.actions
    assert "update" in signals.actions
    assert "Bookings" in signals.labels
    assert "/api/bookings" in signals.endpoints
    assert "bookings" in signals.purpose
    assert signals.confidence == "High"
    assert any("Repeated domain terms" in item for item in signals.evidence)


def test_analyze_content_works_without_known_language() -> None:
    content = """
# Sync customer records before import
command = "Import Customers"
endpoint = "/v1/customers/sync"
"""

    signals = analyze_content(Path("jobs/customer_sync.task"), content, "Unknown")

    assert "customer" in signals.domain_terms or "customers" in signals.domain_terms
    assert "sync" in signals.actions
    assert "Import Customers" in signals.labels
    assert "/v1/customers/sync" in signals.endpoints
