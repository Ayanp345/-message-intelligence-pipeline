import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class SensitiveMatch:
    sensitivity_type: str
    risk: str
    recommended_action: str
    raw_value: str
    reason: str


# Each rule: (type_name, regex_with_one_capture_group, risk, action, reason_template)
# The capture group is the exact span that gets masked.
RULES = [
    (
        "password",
        re.compile(r"\bpassword\s+(\S+)", re.IGNORECASE),
        "high",
        "do_not_store",
        "Message explicitly shares a literal account password.",
    ),
    (
        "one_time_password",
        re.compile(r"\bOTP\s+is\s+([\w\-]+)", re.IGNORECASE),
        "high",
        "do_not_store",
        "Message contains a one-time password (OTP), a short-lived authentication secret.",
    ),
    (
        "bank_card_number",
        re.compile(r"\bcard number is\s+([\d][\d\s\-]{5,})", re.IGNORECASE),
        "high",
        "do_not_store",
        "Message contains what appears to be a payment card number.",
    ),
    (
        "bank_account_number",
        re.compile(r"\bbank account number\s+([\d\-]+)", re.IGNORECASE),
        "high",
        "do_not_store",
        "Message contains a bank account number, direct financial identifier.",
    ),
    (
        "auth_token",
        re.compile(r"\baccess token is\s+(\S+)", re.IGNORECASE),
        "high",
        "do_not_store",
        "Message contains an authentication/API access token.",
    ),
    (
        "account_recovery_code",
        re.compile(r"\baccount recovery code is\s+([\w\-]+)", re.IGNORECASE),
        "high",
        "do_not_store",
        "Message contains an account recovery code, which can be used to bypass login.",
    ),
    (
        "personal_identification_number",
        re.compile(r"\bidentification number is\s+([\w\-]+)", re.IGNORECASE),
        "high",
        "do_not_store",
        "Message contains a personal identification number (government/institution ID style).",
    ),
    (
        "private_address",
        re.compile(r"\bhome address is\s+(.+?)(?:\.$|\.\s|$)", re.IGNORECASE),
        "medium",
        "ask_for_confirmation",
        "Message contains a private home address.",
    ),
    (
        "private_phone_number",
        re.compile(r"\bcontact me on\s+([\d\s\-]+)", re.IGNORECASE),
        "medium",
        "ask_for_confirmation",
        "Message contains a private phone/contact number.",
    ),
    (
        "health_information",
        re.compile(r"\btest result says\s+(.+?)(?:\.$|\.\s|$)", re.IGNORECASE),
        "medium",
        "ask_for_confirmation",
        "Message contains personal health information (medical test result).",
    ),
]


def _mask_span(text: str, start: int, end: int) -> str:
    """Replace text[start:end] with asterisks of the same visual length,
    capped so very long secrets don't create unreadable walls of *."""
    span_len = end - start
    stars = "*" * min(span_len, 8)
    return text[:start] + stars + text[end:]


def detect_sensitive(message_id: str, text: str) -> List[SensitiveMatch]:
    """Return a list of SensitiveMatch objects for every rule that fires."""
    findings = []
    for type_name, pattern, risk, action, reason in RULES:
        m = pattern.search(text)
        if m:
            findings.append(
                SensitiveMatch(
                    sensitivity_type=type_name,
                    risk=risk,
                    recommended_action=action,
                    raw_value=m.group(1),
                    reason=reason,
                )
            )
    return findings


def _mask_group1(match: re.Match) -> str:
    span_len = match.end(1) - match.start(1)
    stars = "*" * min(span_len, 8)
    # re-assemble: text before group1 (relative to whole match) + stars + text after group1
    whole = match.group(0)
    g_start_rel = match.start(1) - match.start(0)
    g_end_rel = match.end(1) - match.start(0)
    return whole[:g_start_rel] + stars + whole[g_end_rel:]


def mask_message(text: str) -> str:
    """Return a copy of the message with every sensitive span replaced by
    asterisks. Each rule runs exactly once (single pass), so this always
    terminates even if masked output could coincidentally match the same
    pattern again."""
    masked = text
    for type_name, pattern, risk, action, reason in RULES:
        masked = pattern.sub(_mask_group1, masked, count=1)
    return masked


def build_sensitive_records(message_id: str, text: str):
    """Convenience wrapper used by the pipeline: returns a list of plain
    dicts (one per detected sensitivity type) ready to serialize to JSON."""
    matches = detect_sensitive(message_id, text)
    masked_text = mask_message(text)
    records = []
    for m in matches:
        records.append(
            {
                "message_id": message_id,
                "sensitivity_type": m.sensitivity_type,
                "risk": m.risk,
                "masked_text": masked_text,
                "recommended_action": m.recommended_action,
                "reason": m.reason,
            }
        )
    return records
