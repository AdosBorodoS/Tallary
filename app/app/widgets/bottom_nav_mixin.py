from kivy.clock import Clock


class BottomNavMixin:
    """
    Добавляет методы:
    - on_nav_click(screenName)
    - refresh_nav_state() -> подсветка активной вкладки
    Ожидаемые ids кнопок:
    navHome, navTransactions, navCategories, navAnalytics
    """

    def on_pre_enter(self, *args) -> None:
        super_on_pre_enter = getattr(super(), "on_pre_enter", None)
        if callable(super_on_pre_enter):
            super_on_pre_enter(*args)

        Clock.schedule_once(lambda _: self.refresh_nav_state(), 0)

    def on_nav_click(self, screenName: str) -> None:
        if self.manager is None:
            return

        # Если уже на нужном экране — просто обновим подсветку
        if self.manager.current == screenName:
            self.refresh_nav_state()
            return

        self.manager.current = screenName
        Clock.schedule_once(lambda _: self.refresh_nav_state(), 0)

    def refresh_nav_state(self) -> None:
        if self.manager is None or not hasattr(self, "ids"):
            return

        activeName = self.manager.current

        navButtons = {
            "home": self.ids.get("navHome"),
            "transactions": self.ids.get("navTransactions"),
            "categories": self.ids.get("navCategories"),
            "analytics": self.ids.get("navAnalytics"),
        }

        activeColor = (0.27, 0.62, 0.97, 1)
        inactiveColor = (0.70, 0.70, 0.70, 1)

        for screenName, btn in navButtons.items():
            if btn is None:
                continue
            btn.color = activeColor if (activeName == screenName) else inactiveColor
