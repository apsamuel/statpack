"""Statpack package initialization."""

from .main import get_commit_sha, get_commit_tag, get_loc
from .common.inputs import read_csv, read_json
from .common.outputs import write_csv, write_json, describe_frame

from .data.sources import fbi
from .data.sources import census
from .data.sources import fred
