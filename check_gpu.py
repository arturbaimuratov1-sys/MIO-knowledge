"""Проверка: PyTorch видит GPU и выполняет малую операцию на ней."""
import torch


def main() -> None:
    print(f"torch: {torch.__version__}")
    print(f"cuda_available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("CUDA недоступна — дальше проверять нечего.")
        raise SystemExit(1)
    print(f"device_count: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"device[{i}]: {torch.cuda.get_device_name(i)}")
        free, total = torch.cuda.mem_get_info(i)
        print(f"  mem_free_mib: {free / 1024**2:.0f}, mem_total_mib: {total / 1024**2:.0f}")

    d = torch.device("cuda:0")
    a = torch.randn(512, 512, device=d)
    b = torch.randn(512, 512, device=d)
    c = a @ b
    torch.cuda.synchronize()
    print(f"matmul ok: shape={tuple(c.shape)}, device={c.device}, mean={c.mean().item():.4f}")


if __name__ == "__main__":
    main()
