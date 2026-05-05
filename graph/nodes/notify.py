from notifier.email import send_email


def notify_node(state: dict) -> dict:
    print("\n[ Notify Node ] 이메일 발송 중...")
    send_email(state["report_items"], state["theme"])
    return {}
