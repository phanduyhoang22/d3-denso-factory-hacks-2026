"""Chọn bản thật (nếu đã có) hoặc bản mock cho từng hàm trong CONTRACTS."""
import importlib

from . import mock
from .contracts import CONTRACTS


def resolve(name, force_mock=False):
    """Trả về (hàm, 'real' | 'mock')."""
    if not force_mock:
        try:
            mod = importlib.import_module(CONTRACTS[name])
            fn = getattr(mod, name, None)
            if fn is not None:
                return fn, "real"
        except ModuleNotFoundError as e:
            if e.name != CONTRACTS[name]:  # module thật có nhưng import bên trong bị lỗi → báo ngay
                raise
    return getattr(mock, name), "mock"


def resolve_all(force_mock=False):
    fns, impl = {}, {}
    for name in CONTRACTS:
        fns[name], impl[name] = resolve(name, force_mock)
    return fns, impl
