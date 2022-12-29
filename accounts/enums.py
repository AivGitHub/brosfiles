from enum import Enum


class SignedURLMethod(Enum):
    """Available signed URL method"""
    POST = 'POST'
    DELETE = 'DELETE'
    PUT = 'PUT'
    GET = 'GET'
    RESUMABLE = 'RESUMABLE'
