import numpy as np
import matplotlib.pyplot as plt

operation_intensity_min = 1e-3
operation_intensity_max = 1e6

def roofline_drawer(ax, device_name, peak_perf, bw, power = 1):
  operation_intensity = np.logspace(np.log10(operation_intensity_min), np.log10(operation_intensity_max), 1000)
  performance = operation_intensity * bw
  performance = np.minimum(performance, peak_perf) # cap performance at peak perfomrance

  # power = 1 gives OPs/s; power in W gives OPs/J
  ax.loglog(operation_intensity, performance / power, label = device_name)

# (name, peak OPs/s, bandwidth B/s, power W)
devices_specs = [
    # H100 source: https://www.nvidia.com/en-us/data-center/h100/
    ("NVIDIA H100 SXM\n(INT8, sparse)", 3958e12, 3.35e12, 700),
    # TPUv4 source: https://arxiv.org/pdf/2304.01433
    # power: no TDP given; Table 4 idle, min/mean/max power 90, 121/170/192 W -> max 192W
    ("TPUv4 (INT8)", 275e12, 1200e9, 192),
    # Jetson Orin NX 16GB source: https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/
    # power: 10W - 15W - 25W - 40W modes, same source; 157 TOPS is the 40W (Super) mode
    ("Jetson Orin NX 16GB", 157e12, 102.4e9, 40),
    # Cerebras WSE-3 source: https://arxiv.org/html/2503.11698v1
    # 125 PFLOPS peak performance, 21 PB/s memory bandwidth
    # power: 23 kW per CS-3 system (Table 1), same source -- system power, not chip only
    # scale to chip power with the DGX H100 chip/system ratio from the same table:
    # 8 x 700 W H100 / 10.4 kW DGX H100 = 0.538 -> 23 kW * 0.538 = ~12.4 kW
    ("Cerebras WSE-3\n", 125e15, 21e15, 23e3 * (8 * 700) / 10.4e3),
    # NVIDIA DGX Spark source: https://www.nvidia.com/en-us/products/workstations/dgx-spark/
    # 1 PFLOP, 273 GB/s LPDDR5x
    # power: GB10 TDP 140 W (chip, CPU + GPU), same source; 240 W is the whole-box power supply
    ("NVIDIA DGX Spark (FP4)\n", 1e15, 273e9, 240),
    # d-Matrix Corsair source: https://d-matrix.ai/pdf/d-Matrix-WhitePaper-Technical-FINAL.pdf
    # 2400 TFLOPs peak dense MXINT8, 150 TB/s on-chip Performance Memory (2 GB SRAM) bandwidth
    # power: 600 W TDP per card, source: https://www.techinsights.com/blog/d-matrix-samples-ai-chiplet
    ("d-Matrix Corsair\n(MXINT8, dense)", 2400e12, 150e12, 600)
]

fig, ax = plt.subplots(figsize = (5,4))
for device, peak_perf, bw, power in devices_specs:
  roofline_drawer(ax, device, peak_perf, bw)

ax.set_xlabel("Operation Intensity [OPs/Byte]")
ax.set_ylabel("Performance [OPs/s]")
ax.legend(loc = "center left", bbox_to_anchor = (1.02, 0.5))

fig.savefig("figures/roofline.png", dpi=300, bbox_inches="tight")

# Energy roofline: attainable performance divided by rated power
fig, ax = plt.subplots(figsize = (5,4))
for device, peak_perf, bw, power in devices_specs:
  roofline_drawer(ax, device, peak_perf, bw, power)

ax.set_xlabel("Operation Intensity [OPs/Byte]")
ax.set_ylabel("Energy Efficiency [OPs/J]")
ax.legend(loc = "center left", bbox_to_anchor = (1.02, 0.5))

fig.savefig("figures/energy_roofline.png", dpi=300, bbox_inches="tight")
