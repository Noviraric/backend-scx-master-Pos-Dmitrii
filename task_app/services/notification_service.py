class NotificationService:
    """Сервис отправки уведомлений (композиция согласно паре 7Б)."""

    def notify(self, message: str) -> None:
        print(f"[NOTIFY] {message}")
