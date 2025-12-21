class BankSlugs:
    ALFA: str = "alfa"
    TINKOFF: str = "tinkoff"

    @classmethod
    def all(cls) -> list[str]:
        return [cls.ALFA,
                cls.TINKOFF,]

    @classmethod
    def is_valid(cls, slug: str) -> bool:
        return slug in cls.all()