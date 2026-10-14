import enum


class Medium(str, enum.Enum):
    movie = "movie"
    tv = "tv"
    game = "game"


class SourceKind(str, enum.Enum):
    critic = "critic"
    user = "user"