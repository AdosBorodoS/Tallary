class BankSlugs:
    CASH:str = "cash"
    ALFA: str = "alfa"
    TINKOFF: str = "tinkoff"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.ALFA,
                cls.TINKOFF,
                cls.CASH,]

    @classmethod
    def is_valid(cls, slug: str) -> bool:
        return slug in cls.all()