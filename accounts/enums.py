from enum import Enum


class SignedURLMethod(Enum):
    """Available signed URL method"""
    POST = 'POST'
    DELETE = 'DELETE'
    PUT = 'PUT'
    GET = 'GET'
    RESUMABLE = 'RESUMABLE'


class TransferType(Enum):
    """Available transfer type"""
    CHUNKED = 'CHUNKED'
    SIGNED_URL = 'SIGNED_URL'
    DEFAULT = 'DEFAULT'
