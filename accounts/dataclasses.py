from dataclasses import dataclass
from typing import Union

from base.dataclasses import DataClassBase


@dataclass
class SignedURLReturnObject(DataClassBase):
    """Class to return when upload signed URL generated."""
    url: str
    headers: Union[dict, None]
    method: str
