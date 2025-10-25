"""Vote use cases."""

from .upvote import UpvoteRequest, UpvoteResponse, UpvoteUseCase
from .remove_vote import RemoveVoteRequest, RemoveVoteResponse, RemoveVoteUseCase

__all__ = [
    "UpvoteRequest",
    "UpvoteResponse",
    "UpvoteUseCase",
    "RemoveVoteRequest",
    "RemoveVoteResponse",
    "RemoveVoteUseCase",
]
