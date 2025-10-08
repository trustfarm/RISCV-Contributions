# falcon_validate/main.py
# CLI entry for Falcon PQC Q-format validator

from __future__ import annotations
import argparse
import numpy as np
from .qformat_module import QCtx
from .fft_module import fft_q, mp_fft, to_qc_array, to_complex128
# 추가/보강: discrete PMF + Box–Muller 함수들
from .gaussian_module import (
    discrete_gaussian_pmf_mp,
    discrete_gaussian_pmf_float,
    box_muller_from_uniforms_np,
    box_muller_from_uniforms_mp,
    box_muller_qx,
)

# --- UPDATE: imports ---
import time
from .sampler_module import (
    sample_discrete_variants,
    sample_discrete_variants_qx,
    build_alias_table,                      # (직접 호출은 안 하지만 유지)
)
# (gaussian import는 기존대로 유지)
from .metrics_module import compute_fft_errors, compute_hist_errors, compute_continuous_errors
from .sweep_module import sweep_and_export

# ------------------------

def align_scale(ref, est):
    ref = np.asarray(ref, dtype=np.complex128)
    est = np.asarray(est, dtype=np.complex128)
    den = np.vdot(est, est)
    if den == 0:
        return est
    s = np.vdot(ref, est) / den  # complex least-squares scale
    return s * est

# def compare_single(I, N, sigma, mp_dps, sampler):
# 수정
def compare_single(I, N, sigma, mp_dps, sampler, need_raw=False):
    q = QCtx(I)
    rng = np.random.default_rng(0)
    x = (rng.random(N) + 1j * rng.random(N)) / np.sqrt(2)

    # --- FFT (MP128을 기준 ref로 사용) ---
    # MP128 (ref)
    mp_fft_out = mp_fft(x, mp_dps)
    mp_fft_out = np.asarray([complex(v) for v in mp_fft_out], dtype=np.complex128)

    # FP64 (est1)
    np_fft_out = np.asarray(np.fft.fft(x) / 2, dtype=np.complex128)

    # Qx (est2)
    qx_in = to_qc_array(x, q)
    q_fft_out, _ = fft_q(qx_in, q)
    qx_fft_f = to_complex128(q_fft_out, q)             # complex128 배열

    # 스케일/위상 정렬: 각 est를 ref(mp) 기준으로 정렬
    np_fft_aligned = align_scale(mp_fft_out, np_fft_out)
    qx_fft_aligned = align_scale(mp_fft_out, qx_fft_f)

    # 오차 집계 (인자 순서: FP64, FP128(ref), Qx)
    fft_err = compute_fft_errors(np_fft_aligned, mp_fft_out, qx_fft_aligned)


    # --- UPDATE: inside compare_single(...) after pmf, before histograms ---
    # === Discrete Gaussian PMF (먼저 확정적으로 생성) ===
    k_max = max(1, int(np.ceil(10.0 * sigma)))
    try:
        pmf_mp = discrete_gaussian_pmf_mp(k_max, sigma, mp_dps)   # FP128 기준
        pmf_f  = discrete_gaussian_pmf_float(k_max, sigma)        # FP64 스냅샷
    except Exception as e:
        raise RuntimeError(
            f"PMF build failed (k_max={k_max}, sigma={sigma}, mp_dps={mp_dps}): {e}"
        )

    # === Sampler 실행 + 타이밍 ===
    n_samples = 10000
    t0 = time.perf_counter_ns()
    vals_fp64 = sample_discrete_variants(pmf_mp, sigma, k_max, n_samples, sampler)
    t1 = time.perf_counter_ns()
    t2 = time.perf_counter_ns()
    vals_qx   = sample_discrete_variants_qx(pmf_mp, sigma, k_max, n_samples, sampler, q)
    t3 = time.perf_counter_ns()

    ns_per_sample_fp64 = (t1 - t0) / n_samples
    ns_per_sample_qx   = (t3 - t2) / n_samples

    # === 히스토그램/정확도 ===
    hist_edges = np.arange(-k_max, k_max + 2)
    hist64, _ = np.histogram(vals_fp64, bins=hist_edges)
    histqx, _ = np.histogram(vals_qx,  bins=hist_edges)
    gauss_err = compute_hist_errors(pmf_mp, pmf_f, pmf_f, hist64, histqx)

    # === Continuous Gaussian (Box–Muller, 공유 uniform) ===
    pairs = 5000
    u1 = rng.random(pairs); u2 = rng.random(pairs)
    z_np0, z_np1 = box_muller_from_uniforms_np(u1, u2)
    z_fp64 = np.concatenate([z_np0, z_np1])
    z_mp_pairs = box_muller_from_uniforms_mp(u1, u2, dps=mp_dps)
    z_mp = np.array([v for pair in z_mp_pairs for v in pair], dtype=np.float64)
    z_q = []
    for i in range(pairs):
        z0, z1 = box_muller_qx(float(u1[i]), float(u2[i]), q)
        z_q.extend([z0, z1])
    z_q = np.array(z_q, dtype=np.float64)

    cont_err = compute_continuous_errors(z_fp64, z_mp, z_q)

    # === 결과 딕셔너리 ===
    res = {"I": I, "N": N, "sigma": sigma, "mp_dps": mp_dps, "sampler": sampler}
    res.update(fft_err)
    res.update(gauss_err)
    res.update(cont_err)
    res["sampler_ns_per_sample_fp64"] = float(ns_per_sample_fp64)
    res["sampler_ns_per_sample_qx"]   = float(ns_per_sample_qx)

    # === RAW가 필요 없으면 여기서 종료 ===
    if not need_raw:
        return res

    # === RAW payload (위에서 생성된 동일 변수명 사용) ===
    raw_payload = {
        "x": x.astype(np.complex128),
        "fft_mp": np.array(mp_fft_out, dtype=np.complex128),
        "fft_fp64": np_fft_out.astype(np.complex128),
        "fft_qx": qx_fft_f.astype(np.complex128),

        "pmf_mp": np.array([float(p) for p in pmf_mp], dtype=np.float64),
        "pmf_fp64": np.array(pmf_f, dtype=np.float64),
        "disc_vals_fp64": vals_fp64.astype(np.int32),
        "disc_vals_qx": vals_qx.astype(np.int32),

        "bm_u1": u1.astype(np.float64),
        "bm_u2": u2.astype(np.float64),
        "bm_z_mp": z_mp.astype(np.float64),
        "bm_z_fp64": z_fp64.astype(np.float64),
        "bm_z_qx": z_q.astype(np.float64),
    }
    return res, raw_payload



def main():
    p = argparse.ArgumentParser()
    p.add_argument("--I_list", type=str, default="8,10,12,16,32")
    p.add_argument("--N_list", type=str, default="256,512")
    p.add_argument("--sigma_list", type=str, default="1.2,1.5,2.0")
    p.add_argument("--mp_dps_list", type=str, default="33,50")
    p.add_argument("--sweep", action="store_true", help="Run full parameter sweep")
    # --- UPDATE: argparse help only (choices 제한이 없다면 문구만) ---
    p.add_argument("--sampler_list", type=str,
        default="cdt,knuth_yao,rejection,ziggurat,alias,expcut",
        help="comma-separated samplers: cdt,knuth_yao,rejection,ziggurat,alias,expcut")
    # -----------------------------------------------------------------

    args = p.parse_args()

    param_grid = {
        "I_list": [int(x) for x in args.I_list.split(",")],
        "N_list": [int(x) for x in args.N_list.split(",")],
        "sigma_list": [float(x) for x in args.sigma_list.split(",")],
        "mp_dps_list": [int(x) for x in args.mp_dps_list.split(",")],
        "sampler_list": args.sampler_list.split(","),
    }
    
    # (교체) args.sweep 분기 안
    if args.sweep:
        # --- UPDATE: in main(), sweep call receive 5 returns ---
        csv_path, png_relL2, png_perf, png_ks, png_mse = sweep_and_export(param_grid, compare_single)
        print(f"\n✅ Sweep done.\nCSV: {csv_path}\nFFT: {png_relL2}\nPerf: {png_perf}\nKS: {png_ks}\nMSE: {png_mse}")
        # -----------------------------------------------------------------
    else:
        # 단일 실행도 RAW 해시만 콘솔에 같이 표시 (파일 저장 없음)
        res, raw = compare_single(param_grid["I_list"][0], param_grid["N_list"][0],
                                param_grid["sigma_list"][0], param_grid["mp_dps_list"][0],
                                param_grid["sampler_list"][0], need_raw=True)
        from .sweep_module import raw_sha256_from_payload, timestamp
        sha = raw_sha256_from_payload(raw)
        print(json.dumps({"result": res, "raw_timestamp": timestamp(), "raw_sha256": sha}, indent=2))


if __name__ == "__main__":
    main()
