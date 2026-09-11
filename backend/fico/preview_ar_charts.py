
"""
Standalone chart preview for the AR validation report.

Run:
    python preview_ar_charts.py

This uses example values only to show the visual design.
The real report_generator.py gets its chart values directly from
ar_validator.py's validation payload.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

OUT = Path("chart_previews")
OUT.mkdir(exist_ok=True)

# ------------------------------------------------------------
# 1. Company Code Distribution
# ------------------------------------------------------------

labels = ["US01 → 1000", "CA01 → 1200"]
ecc = [28619, 1382]
s4 = [28619, 1382]

x = np.arange(len(labels))
width = 0.35

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(x - width / 2, ecc, width, label="ECC")
ax.bar(x + width / 2, s4, width, label="S/4")

ax.set_title("Company Code Distribution — ECC vs S/4")
ax.set_ylabel("Record Count")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
ax.grid(axis="y", alpha=0.2)

fig.tight_layout()
fig.savefig(OUT / "company_code_distribution_preview.png", dpi=180)
plt.show()
plt.close(fig)

# ------------------------------------------------------------
# 2. Amount Sign Validation
# ------------------------------------------------------------

labels = ["S / Debit", "H / Credit"]
ecc = [12500000, 8300000]
s4 = [12500000, 8300000]

x = np.arange(len(labels))

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(x - width / 2, ecc, width, label="ECC")
ax.bar(x + width / 2, s4, width, label="S/4")

ax.set_title("Amount Sign Validation — ECC vs S/4")
ax.set_ylabel("Amount")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
ax.grid(axis="y", alpha=0.2)

fig.tight_layout()
fig.savefig(OUT / "amount_sign_validation_preview.png", dpi=180)
plt.show()
plt.close(fig)

# ------------------------------------------------------------
# 3. Payment Terms Groups
# ------------------------------------------------------------

labels = [f"Set {i}" for i in range(1, 14)]

ecc = [58, 132, 91, 2341, 4120, 2750, 920,
       1150, 760, 840, 990, 1120, 84]

s4 = ecc.copy()

x = np.arange(len(labels))

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(x - width / 2, ecc, width, label="ECC")
ax.bar(x + width / 2, s4, width, label="S/4")

ax.set_title("Payment Terms Group Validation — ECC vs S/4")
ax.set_ylabel("Record Count")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.legend()
ax.grid(axis="y", alpha=0.2)

fig.tight_layout()
fig.savefig(OUT / "payment_terms_groups_preview.png", dpi=180)
plt.show()
plt.close(fig)

print(f"Preview charts created in: {OUT.resolve()}")
