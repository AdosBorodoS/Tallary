from kivy.clock import Clock


class BottomNavMixin:
    """
    Добавляет методы:
    - on_nav_click(screenName)
    - refresh_nav_state() -> подсветка активной вкладки
    """

    def on_pre_enter(self, *args) -> None:
        super_on_pre_enter = getattr(super(), "on_pre_enter", None)
        if callable(super_on_pre_enter):
            super_on_pre_enter(*args)

        Clock.schedule_once(lambda _: self.refresh_nav_state(), 0)

    def on_nav_click(self, screenName: str) -> None:
        if self.manager is None:
            return
        self.manager.current = screenName
        Clock.schedule_once(lambda _: self.refresh_nav_state(), 0)

    def refresh_nav_state(self) -> None:
        if not hasattr(self, "ids") or self.manager is None:
            return

        activeName = self.manager.current

        navButtons = {
            "home": self.ids.get("navDashboard"),
            "analytics": self.ids.get("navAnalytics"),
            "collab": self.ids.get("navCollab"),
        }

        for screenName, btn in navButtons.items():
            if btn is None:
                continue

            isActive = (activeName == screenName)

            # активная вкладка: ярче, неактивная: темнее
            btn.background_color = (0.25, 0.55, 0.95, 1) if isActive else (0.20, 0.20, 0.20, 1)
