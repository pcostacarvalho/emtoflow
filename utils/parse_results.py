
from utils.file_io import read_file


def parse_energies(ratios, sws, path, id_name):
    energies_lda = {v: [] for v in sws}
    energies_gga = {v: [] for v in sws}
    
    for r in ratios:
        for v in sws:
            try:
                out = read_file(f"{path}/fcd/{id_name}_{r:.2f}.prn")
                
                lda_found = False
                gga_found = False
                
                for line in out:
                    if "TOT-LDA" in line and not lda_found:
                        energies_lda[v].append(float(line.split()[1]))
                        lda_found = True
                    
                    if "TOT-GGA" in line and not gga_found:
                        energies_gga[v].append(float(line.split()[1]))
                        gga_found = True
                    
                    # Exit early if both found
                    if lda_found and gga_found:
                        break
                
                # Warn if data missing
                if not lda_found or not gga_found:
                    print(f"Warning: Missing energy data for r={r:.2f}, v={v:.2f}")
                    
            except FileNotFoundError:
                print(f"Warning: File not found for r={r:.2f}, v={v:.2f}")
            except (IndexError, ValueError) as e:
                print(f"Warning: Failed to parse energy for r={r:.2f}, v={v:.2f}: {e}")
    
    # If only one sws value, return flat lists for backward compatibility
    if len(sws) == 1:
        return energies_lda[sws[0]], energies_gga[sws[0]]
    
    # Otherwise return dictionaries keyed by sws value
    return energies_lda, energies_gga