"""Базовые проверки окружения kpack-lab."""
import importlib

import torch


def test_torch_importable():
    assert torch.__version__


def test_cuda_available():
    assert torch.cuda.is_available(), "PyTorch не видит CUDA/GPU"


def test_gpu_matmul():
    d = torch.device("cuda:0")
    c = torch.randn(64, 64, device=d) @ torch.randn(64, 64, device=d)
    assert c.device.type == "cuda"


def test_ml_libs_importable():
    for name in ("transformers", "datasets", "peft", "accelerate"):
        assert importlib.import_module(name) is not None
