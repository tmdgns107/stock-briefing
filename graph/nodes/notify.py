import os

from notifier.email import send_email


def notify_node(state: dict) -> dict:
    if os.getenv("NOTIFY_VIA") == "n8n":
        print("\n[ Notify Node ] n8n 위임 — 이메일 발송 스킵")
        return {}

    print("\n[ Notify Node ] 이메일 발송 중...")
    send_email(state["report_items"], state["theme"])
    return {}
