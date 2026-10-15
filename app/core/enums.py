import enum


class Medium(enum.StrEnum):
    movie = "movie"
    tv = "tv"
    game = "game"


class SourceKind(enum.StrEnum):
    critic = "critic"
    user = "user"
