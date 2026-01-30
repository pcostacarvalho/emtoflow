#!/usr/bin/env python3
"""
Predict the EOS fit with symmetric_fit=true and n_points_final=7
"""
import numpy as np
import matplotlib.pyplot as plt
import json

# New data from the JSON file
data_points = [
    {"parameter": 2.515978903926613, "energy": -1855.276946},
    {"parameter": 2.539055827003536, "energy": -1855.287932},
    {"parameter": 2.562132750080459, "energy": -1855.297857},
    {"parameter": 2.565978903926613, "energy": -1855.299481},
    {"parameter": 2.585209673157382, "energy": -1855.306797},
    {"parameter": 2.6082865962343056, "energy": -1855.314823},
    {"parameter": 2.6159789039266133, "energy": -1855.317413},
    {"parameter": 2.6313635193112286, "energy": -1855.322001},
    {"parameter": 2.6544404423881516, "energy": -1855.328392},
    {"parameter": 2.665978903926613, "energy": -1855.331434},
    {"parameter": 2.6775173654650746, "energy": -1855.334285},
    {"parameter": 2.7005942885419976, "energy": -1855.339241},
    {"parameter": 2.715978903926613, "energy": -1855.342133},
    {"parameter": 2.7236712116189206, "energy": -1855.342133},
    {"parameter": 2.746748134695844, "energy": -1855.347322},
    {"parameter": 2.765978903926613, "energy": -1855.350013},
    {"parameter": 2.769825057772767, "energy": -1855.350013},
    {"parameter": 2.79290198084969, "energy": -1855.353253},
    {"parameter": 2.8000000000000003, "energy": -1855.353677},
    {"parameter": 2.815978903926613, "energy": -1855.355506},
    {"parameter": 2.8230769230769233, "energy": -1855.355506},
    {"parameter": 2.8461538461538463, "energy": -1855.357871},
    {"parameter": 2.8692307692307693, "energy": -1855.359109},
    {"parameter": 2.8923076923076927, "energy": -1855.360065},
    {"parameter": 2.9153846153846157, "energy": -1855.36069},
    {"parameter": 2.9384615384615387, "energy": -1855.36101},
    {"parameter": 2.9615384615384617, "energy": -1855.361043},
    {"parameter": 2.9846153846153847, "energy": -1855.36081},
    {"parameter": 3.0076923076923077, "energy": -1855.360337},
    {"parameter": 3.030769230769231, "energy": -1855.359644},
    {"parameter": 3.053846153846154, "energy": -1855.359058},
    {"parameter": 3.076923076923077, "energy": -1855.357666},
    {"parameter": 3.1, "energy": -1855.356602}
]

# Extract parameter and energy values
parameters = np.array([point["parameter"] for point in data_points])
energies = np.array([point["energy"] for point in data_points])

# Find the minimum
min_idx = np.argmin(energies)
min_param = parameters[min_idx]
min_energy = energies[min_idx]

print("="*60)
print("SYMMETRIC FIT PREDICTION")
print("="*60)
print(f"\nMinimum energy point:")
print(f"  Index: {min_idx}")
print(f"  SWS: {min_param:.6f} Bohr")
print(f"  Energy: {min_energy:.6f} Ry")

# For symmetric fit with 7 points: 3 points on each side + minimum
n_points_final = 7
n_side = (n_points_final - 1) // 2  # 3 points on each side

print(f"\nSymmetric fit configuration:")
print(f"  Total points: {n_points_final}")
print(f"  Points on each side: {n_side}")

# Select symmetric points
left_indices = []
right_indices = []

# Get points to the left of minimum
for i in range(min_idx - 1, -1, -1):
    if len(left_indices) < n_side:
        left_indices.append(i)
    else:
        break
left_indices.reverse()

# Get points to the right of minimum
for i in range(min_idx + 1, len(parameters)):
    if len(right_indices) < n_side:
        right_indices.append(i)
    else:
        break

selected_indices = left_indices + [min_idx] + right_indices
selected_params = parameters[selected_indices]
selected_energies = energies[selected_indices]

print(f"\nSelected {len(selected_indices)} points symmetrically around minimum:")
print("\n  Index |    SWS      |    Energy (Ry)    | Position")
print("-" * 60)
for idx, p, e in zip(selected_indices, selected_params, selected_energies):
    if idx == min_idx:
        pos = "MINIMUM"
    elif idx in left_indices:
        pos = f"Left-{left_indices.index(idx)+1}"
    else:
        pos = f"Right-{right_indices.index(idx)+1}"
    print(f"  {idx:3d}   | {p:11.6f} | {e:13.6f}   | {pos}")

# Polynomial fit (4th order for EOS-like behavior)
# Fit E(sws) as a polynomial
try:
    # Use 4th order polynomial for smooth EOS-like curve
    poly_order = 4
    coeffs = np.polyfit(selected_params, selected_energies, poly_order)
    poly_fit = np.poly1d(coeffs)
    
    # Find minimum of the polynomial fit
    # Take derivative and find roots
    poly_deriv = np.polyder(poly_fit)
    critical_points = np.roots(poly_deriv)
    
    # Find real critical points within reasonable range
    real_critical = critical_points[np.isreal(critical_points)].real
    valid_critical = real_critical[
        (real_critical >= selected_params.min()) & 
        (real_critical <= selected_params.max())
    ]
    
    if len(valid_critical) > 0:
        # Evaluate polynomial at critical points to find minimum
        critical_energies = [poly_fit(cp) for cp in valid_critical]
        min_critical_idx = np.argmin(critical_energies)
        sws_fit = valid_critical[min_critical_idx]
        E0_fit = critical_energies[min_critical_idx]
    else:
        # Fallback to minimum of selected points
        sws_fit = min_param
        E0_fit = min_energy
    
    print("\n" + "="*60)
    print("POLYNOMIAL FIT RESULTS (4th order)")
    print("="*60)
    print(f"  Polynomial coefficients:")
    for i, c in enumerate(coeffs):
        print(f"    a{poly_order-i}: {c:.10e}")
    print(f"\n  E0 (minimum energy):     {E0_fit:.6f} Ry")
    print(f"  SWS (equilibrium):       {sws_fit:.6f} Bohr")
    
    # Calculate fit quality
    fitted_energies = poly_fit(selected_params)
    residuals = selected_energies - fitted_energies
    rmse = np.sqrt(np.mean(residuals**2))
    
    print(f"\n  RMSE: {rmse:.8f} Ry")
    print(f"  Max residual: {np.max(np.abs(residuals)):.8f} Ry")
    
    fit_success = True
    
except Exception as e:
    print(f"\nFit failed: {e}")
    fit_success = False
    import traceback
    traceback.print_exc()

# Create visualization
fig = plt.figure(figsize=(14, 10))
gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

# Plot 1: Full dataset with selected points (SWS vs Energy)
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(parameters, energies, 'o-', linewidth=1, markersize=4, alpha=0.5, 
         color='gray', label='All data points')
ax1.plot(selected_params, selected_energies, 'ro', markersize=10, 
         label=f'Selected symmetric points (n={len(selected_params)})', zorder=5)
ax1.plot(min_param, min_energy, 'g*', markersize=18, 
         label=f'Data minimum: sws={min_param:.4f}', zorder=6)

if fit_success:
    # Plot the fit
    sws_fit_range = np.linspace(parameters.min(), parameters.max(), 200)
    energy_fit = poly_fit(sws_fit_range)
    ax1.plot(sws_fit_range, energy_fit, 'b-', linewidth=2, alpha=0.7,
             label=f'Polynomial fit: sws={sws_fit:.4f}', zorder=4)
    ax1.plot(sws_fit, E0_fit, 'bs', markersize=12, 
             label=f'Fit minimum', zorder=6)

ax1.set_xlabel('SWS Parameter (Bohr)', fontsize=11, fontweight='bold')
ax1.set_ylabel('Energy (Ry)', fontsize=11, fontweight='bold')
ax1.set_title('Symmetric Fit: 7 Points Around Minimum', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.legend(fontsize=9)

# Plot 2: Zoomed view around minimum
ax2 = fig.add_subplot(gs[1, 0])
zoom_mask = (parameters >= min_param - 0.3) & (parameters <= min_param + 0.3)
ax2.plot(parameters[zoom_mask], energies[zoom_mask], 'o-', linewidth=1, markersize=5, 
         alpha=0.5, color='gray', label='All points')
ax2.plot(selected_params, selected_energies, 'ro', markersize=10, 
         label='Selected points', zorder=5)
ax2.plot(min_param, min_energy, 'g*', markersize=15, zorder=6)

if fit_success:
    sws_zoom = np.linspace(min_param - 0.3, min_param + 0.3, 100)
    energy_zoom = poly_fit(sws_zoom)
    ax2.plot(sws_zoom, energy_zoom, 'b-', linewidth=2, alpha=0.7, zorder=4)
    ax2.plot(sws_fit, E0_fit, 'bs', markersize=10, zorder=6)

ax2.set_xlabel('SWS (Bohr)', fontsize=10, fontweight='bold')
ax2.set_ylabel('Energy (Ry)', fontsize=10, fontweight='bold')
ax2.set_title('Zoomed View Around Minimum', fontsize=11, fontweight='bold')
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.legend(fontsize=8)

# Plot 3: Residuals
if fit_success:
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.plot(selected_params, residuals * 1000, 'ro-', markersize=8, linewidth=1.5)
    ax3.axhline(y=0, color='k', linestyle='--', alpha=0.5)
    ax3.set_xlabel('SWS (Bohr)', fontsize=10, fontweight='bold')
    ax3.set_ylabel('Residuals (mRy)', fontsize=10, fontweight='bold')
    ax3.set_title('Fit Residuals', fontsize=11, fontweight='bold')
    ax3.grid(True, alpha=0.3, linestyle='--')

# Plot 4: Energy curvature (second derivative)
ax4 = fig.add_subplot(gs[2, :])
if fit_success:
    sws_range = np.linspace(parameters.min(), parameters.max(), 200)
    energy_range = poly_fit(sws_range)
    
    # Calculate second derivative (curvature)
    poly_deriv2 = np.polyder(poly_fit, 2)
    curvature = poly_deriv2(sws_range)
    
    ax4_twin = ax4.twinx()
    
    # Plot energy on left axis
    ax4.plot(sws_range, energy_range, 'b-', linewidth=2, alpha=0.7, label='Fit curve')
    ax4.plot(selected_params, selected_energies, 'ro', markersize=8, 
             label='Selected points', zorder=5)
    ax4.plot(sws_fit, E0_fit, 'bs', markersize=12, label='Fit minimum', zorder=6)
    
    # Plot curvature on right axis
    ax4_twin.plot(sws_range, curvature, 'g--', linewidth=1.5, alpha=0.6, label='Curvature (d²E/dV²)')
    ax4_twin.axhline(y=0, color='gray', linestyle=':', alpha=0.5)
    
    ax4.set_xlabel('SWS (Bohr)', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Energy (Ry)', fontsize=11, fontweight='bold', color='b')
    ax4_twin.set_ylabel('Curvature (Ry/Bohr²)', fontsize=11, fontweight='bold', color='g')
    ax4.tick_params(axis='y', labelcolor='b')
    ax4_twin.tick_params(axis='y', labelcolor='g')
else:
    ax4.plot(parameters, energies, 'o-', linewidth=1, markersize=4, alpha=0.5, 
             color='gray', label='All data')
    ax4.plot(selected_params, selected_energies, 'ro', markersize=10, 
             label='Selected points', zorder=5)
    ax4.set_xlabel('SWS (Bohr)', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Energy (Ry)', fontsize=11, fontweight='bold')

ax4.set_title('Polynomial Fit and Curvature Analysis', fontsize=12, fontweight='bold')
ax4.grid(True, alpha=0.3, linestyle='--')
ax4.legend(fontsize=9, loc='upper left')

plt.savefig('symmetric_fit_prediction.png', dpi=300, bbox_inches='tight')
print(f"\nPlot saved as 'symmetric_fit_prediction.png'")

# Save results to JSON
if fit_success:
    results = {
        "fit_type": f"Polynomial (order {poly_order})",
        "configuration": {
            "symmetric_fit": True,
            "n_points_final": 7,
            "eos_auto_expand_range": False,
            "eos_use_saved_data": True,
            "eos_use_all_saved_for_final_fit": True
        },
        "data_minimum": {
            "index": int(min_idx),
            "sws": float(min_param),
            "energy": float(min_energy)
        },
        "fit_results": {
            "E0_minimum_energy_Ry": float(E0_fit),
            "SWS_equilibrium_Bohr": float(sws_fit),
            "polynomial_coefficients": [float(c) for c in coeffs],
            "RMSE_Ry": float(rmse),
            "max_residual_Ry": float(np.max(np.abs(residuals)))
        },
        "selected_points": [
            {
                "index": int(idx),
                "sws": float(p),
                "energy": float(e),
                "position": "minimum" if idx == min_idx else ("left" if idx in left_indices else "right")
            }
            for idx, p, e in zip(selected_indices, selected_params, selected_energies)
        ]
    }
    
    with open('symmetric_fit_prediction.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("Results saved to 'symmetric_fit_prediction.json'")

print("\n" + "="*60)
plt.show()
