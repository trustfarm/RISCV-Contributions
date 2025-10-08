# falcon_validate/sweep_module.py
# Sweep controller for Falcon validation

from __future__ import annotations
import os
import csv
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")  # ✅ headless backend (no Qt)
import matplotlib.pyplot as plt
from .metrics_module import compute_fft_errors, compute_hist_errors, compute_continuous_errors
# (추가) 해시 계산 유틸
import hashlib
import io

# === ADD: complex 벡터를 CSV 문자열로 인코딩 ===
def encode_complex_vector_to_csv_fields(x: np.ndarray):
    xr = np.asarray(x).real.tolist()
    xi = np.asarray(x).imag.tolist()
    re_s = ";".join(f"{v:.17g}" for v in xr)
    im_s = ";".join(f"{v:.17g}" for v in xi)
    return re_s, im_s

# 공용 타임스탬프 생성
def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")

# (추가) RAW payload를 메모리에서 직렬화해 SHA256 계산 (파일 저장 없음)
def raw_sha256_from_payload(payload: dict) -> str:
    buf = io.BytesIO()
    # 키 순서를 고정해 캐논컬 직렬화
    ordered = {k: np.asarray(payload[k]) for k in sorted(payload.keys())}
    np.savez_compressed(buf, **ordered)
    data = buf.getvalue()
    return hashlib.sha256(data).hexdigest()

# (교체) 메인 결과 CSV — RAW 관련 컬럼 제거
def write_results_csv(results, prefix="falcon_sweep", ts=None):
    ts = ts or timestamp()
    fname = f"{prefix}_{ts}.csv"
    with open(fname, "w", newline="") as f:
        # --- UPDATE: write_results_csv fieldnames ---
        fieldnames = [
            "I","N","sigma","mp_dps","sampler",
            "fft64_mse","fft64_relL2","fftq_mse","fftq_relL2",
            "disc_pmf_l2_fp64","disc_hist_mse_fp64","disc_hist_mse_qx","disc_hist_ks_qx",  # KS 추가
            "cont64_mse","contqx_mse",
            "sampler_ns_per_sample_fp64","sampler_ns_per_sample_qx"                          # 성능 추가
        ]
        # -------------------------------------------------------------------

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    return fname


# 기존 write_rawmeta_csv(...) 정의를 다음처럼 교체
def write_rawmeta_csv(rows, prefix="falcon_rawmeta", ts=None):
    ts = ts or timestamp()
    fname = f"{prefix}_{ts}.csv"
    with open(fname, "w", newline="") as f:
        fieldnames = ["I","N","sigma","mp_dps","sampler","timestamp","raw_sha256",
                      "raw_input_re","raw_input_im"]  # ← ✅ 추가
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return fname

def write_csv(results, prefix="falcon_sweep"):
    fname = f"{prefix}_{timestamp()}.csv"
    with open(fname, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "I", "N", "sigma", "mp_dps", "sampler",
                "fft64_mse", "fft64_relL2",
                "fftq_mse", "fftq_relL2",
                "disc_pmf_l2_fp64", "disc_hist_mse_fp64", "disc_hist_mse_qx",
                "cont64_mse", "contqx_mse"
            ]
        )
        writer.writeheader()
        writer.writerows(results)
    return fname

def plot_from_csv(csv_file):
    import numpy as np
    import matplotlib.pyplot as plt

    data = np.genfromtxt(csv_file, delimiter=",", names=True, dtype=None, encoding=None)

    # 공통 축
    plt.figure()
    plt.xlabel("FFT size N")
    plt.ylabel("Relative L2 error")
    plt.title("FFT relative L2 vs N")

    # 1) Qx를 I별로 분리해 QI.F 라벨 부여 (예: Q12.52)
    unique_I = np.unique(data["I"])
    for I in unique_I:
        m = (data["I"] == I)
        if not np.any(m):
            continue
        F = 64 - int(I)
        label_q = f"FFT Q{int(I)}.{F} relL2"
        plt.scatter(data["N"][m], data["fftq_relL2"][m], label=label_q)

    # 2) FP64 기준선은 한 번만 표시
    plt.scatter(data["N"], data["fft64_relL2"], label="FFT FP64 relL2")

    plt.legend()
    png = csv_file.replace(".csv", ".png")
    plt.tight_layout()
    plt.savefig(png, dpi=150)
    return png


# --- ADD: additional plots ---
def plot_perf_from_csv(csv_file):
    data = np.genfromtxt(csv_file, delimiter=",", names=True, dtype=None, encoding=None)
    plt.figure()
    for name in np.unique(data["sampler"]):
        m = data["sampler"] == name
        plt.plot(data["sigma"][m], data["sampler_ns_per_sample_qx"][m], marker="o", linestyle="-", label=f"{name} (Qx)")
    plt.xlabel("sigma"); plt.ylabel("ns per sample (Qx)")
    plt.title("Sampler speed vs sigma")
    plt.legend(); plt.tight_layout()
    png = csv_file.replace(".csv", "_perf.png")
    plt.savefig(png, dpi=150); return png

def plot_ks_from_csv(csv_file):
    data = np.genfromtxt(csv_file, delimiter=",", names=True, dtype=None, encoding=None)
    plt.figure()
    for name in np.unique(data["sampler"]):
        m = data["sampler"] == name
        plt.plot(data["sigma"][m], data["disc_hist_ks_qx"][m], marker="o", linestyle="-", label=name)
    plt.xlabel("sigma"); plt.ylabel("KS (hist Qx vs FP64)")
    plt.title("Discrete KS vs sigma")
    plt.legend(); plt.tight_layout()
    png = csv_file.replace(".csv", "_ks.png")
    plt.savefig(png, dpi=150); return png

def plot_mse_from_csv(csv_file):
    data = np.genfromtxt(csv_file, delimiter=",", names=True, dtype=None, encoding=None)
    plt.figure()
    for name in np.unique(data["sampler"]):
        m = data["sampler"] == name
        plt.plot(data["sigma"][m], data["disc_hist_mse_qx"][m], marker="o", linestyle="-", label=name)
    plt.xlabel("sigma"); plt.ylabel("Hist MSE (Qx)")
    plt.title("Discrete MSE vs sigma")
    plt.legend(); plt.tight_layout()
    png = csv_file.replace(".csv", "_mse.png")
    plt.savefig(png, dpi=150); return png
# ---------------------------------------------

# (교체) sweep_and_export: 한 번의 ts를 공유해 results.csv 와 rawmeta.csv 생성
def sweep_and_export(param_grid, compute_func, prefix="falcon_sweep"):
    results = []
    rawmeta_rows = []
    ts = timestamp()

    total = (len(param_grid["I_list"])
             * len(param_grid["N_list"])
             * len(param_grid["sigma_list"])
             * len(param_grid["mp_dps_list"])
             * len(param_grid["sampler_list"]))
    count = 0

    print(f"\n🚀 Starting sweep for {total} combinations...\n")

    for I in param_grid["I_list"]:
        for N in param_grid["N_list"]:
            for sigma in param_grid["sigma_list"]:
                for mp_dps in param_grid["mp_dps_list"]:
                    for sampler in param_grid["sampler_list"]:
                        count += 1
                        print(
                            f"[{count:3d}/{total}] I={I:2d}  N={N:<5d}  σ={sigma:<4.2f}  mp_dps={mp_dps:<3d}  sampler={sampler:<10s} ... ",
                            end="", flush=True,
                        )
                        try:
                            res, raw_payload = compute_func(I, N, sigma, mp_dps, sampler, need_raw=True)

                            # 1) SHA 계산 (기존 그대로)
                            sha = raw_sha256_from_payload(raw_payload)

                            # 2) 입력 x를 CSV에 그대로 박아 넣기
                            raw_re, raw_im = encode_complex_vector_to_csv_fields(raw_payload["x"])

                            rawmeta_rows.append({
                                "I": I, "N": N, "sigma": sigma, "mp_dps": mp_dps, "sampler": sampler,
                                "timestamp": ts, "raw_sha256": sha,
                                "raw_input_re": raw_re,           # ← ✅ 추가
                                "raw_input_im": raw_im,           # ← ✅ 추가
                            })
                            
                            results.append(res)
                            print("✅ done")
                        except Exception as e:
                            print(f"❌ error: {e}")

    # 두 CSV 생성(동일 ts)
    csv_path = write_results_csv(results, prefix=prefix, ts=ts)
    rawmeta_path = write_rawmeta_csv(rawmeta_rows, prefix="falcon_rawmeta", ts=ts)
    # --- UPDATE: sweep_and_export end ---
    csv_path = write_results_csv(results, prefix=prefix, ts=ts)
    png_relL2 = plot_from_csv(csv_path)             # 기존 (FFT relL2)
    png_perf  = plot_perf_from_csv(csv_path)        # 신규
    png_ks    = plot_ks_from_csv(csv_path)          # 신규
    png_mse   = plot_mse_from_csv(csv_path)         # 신규
    print(f"\n✅ Sweep completed!\n📄 Results → {csv_path}\n"
        f"📊 FFT → {png_relL2}\n⚡ Perf → {png_perf}\n📈 KS → {png_ks}\n📉 MSE → {png_mse}")
    return csv_path, png_relL2, png_perf, png_ks, png_mse
    # ---------------------------------------------------
