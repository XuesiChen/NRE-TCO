# source: dev cost of Taalas, assuming one? https://www.heise.de/en/news/AI-inference-cast-in-silicon-Taalas-announces-HC1-chip-11185112.html HNLPU's estimate was 38M in N5 but didn't detail the process
taalas_NRE = 30 # 30M
taalas_perf = 16960 # 17k tok/s/user https://www.cnx-software.com/2026/02/22/taalas-hc1-hardwired-llama-3-1-8b-ai-accelerator-delivers-up-to-17000-tokens-s/

# --- Power ---

# Derived from HNLPU Table 1 "Single Chip Hardware Characteristics" https://arxiv.org/abs/2508.16151
# Table 1 is ONE of 16 chips in the gpt-oss-120B system (Table 2: 13,232 mm2 total = 16 x 827.08 mm2), 5nm, 1.0 GHz
hnlpu_chip_power = {   # W, Table 1
    "HN Array": 76.92,           # hardwired weights
    "VEX": 33.09,                # vector / nonlinear ops
    "Control Unit": 0.01,        # "<0.01"
    "Attention Buffer": 85.73,   # on-chip KV cache
    "Interconnect Engine": 49.65,# chip-to-chip (CXL), not needed on a single-chip 8B design
    "HBM PHY": 63.0,             # HC1 has no HBM
}  # total 308.39 W, 827.08 mm2
hnlpu_chip_params = 116.8 / 16 # B params per chip: gpt-oss-120B split over 16 chips = 7.3B
taalas_params = 8.03              # B params, Llama-3.1-8B

# Process: 1) drop blocks HC1 doesn't have, 2) scale by params per chip, 3) scale 5nm -> N6
hnlpu_chip_power_single = sum(hnlpu_chip_power.values()) - hnlpu_chip_power["Interconnect Engine"] - hnlpu_chip_power["HBM PHY"] # 195.7 W
# N5 vs N7: "15% speed improvement or 30% lower power consumption" (TSMC claim)https://www.tomshardware.com/news/tsmc-reveals-2nm-fabrication-process
# assume power scaling is linear 
node_factor_n5_to_n6 = 1 / (1 - 0.15)
hc1_power_est = hnlpu_chip_power_single * (taalas_params / hnlpu_chip_params) * node_factor_n5_to_n6 
# Caveats: HNLPU is MoE (4/128 experts active) running at full pipeline occupancy; Llama-3.1-8B is dense with
# full attention (~3x the KV traffic of gpt-oss), so per-block drivers differ. Table 1 does not split static vs dynamic.
hc1_energy_per_token = hc1_power_est / taalas_perf # J/token, ~16.5 mJ (range ~12-25 mJ)


def log_taalas(path="taalas_power_perf.log"):
    lines = [
        "Taalas HC1 (Llama-3.1-8B) power & perf",
        f"perf                       {taalas_perf:,} tok/s/user",
        f"NRE                        ${taalas_NRE}M",
        f"HNLPU chip power (Table 1) {sum(hnlpu_chip_power.values()):.2f} W",
        *[f"  {k:<25}{v:>7.2f} W" for k, v in hnlpu_chip_power.items()],
        f"minus Interconnect, HBM    {hnlpu_chip_power_single:.2f} W",
        f"x params ({taalas_params} / {hnlpu_chip_params:.2f} B)  {hnlpu_chip_power_single * taalas_params / hnlpu_chip_params:.2f} W",
        f"x node factor N5->N6 ({node_factor_n5_to_n6:.3f}) {hc1_power_est:.2f} W",
        f"energy per token           {hc1_energy_per_token * 1e3:.2f} mJ ({1 / hc1_energy_per_token:.1f} tok/J)",
    ]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    log_taalas()



