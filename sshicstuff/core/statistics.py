import os
import sys
import argparse
import numpy as np
import pandas as pd


def get_stats(
        sample_name: str,
        contacts_unbinned_path: str,
        sparse_contacts_path: str,
        centros_coord_path: str,
        oligos_path: str,
        output_dir: str,
        cis_range: int = 50000,
):
    """
    Generate statistics and normalization for contacts made by each probe.

    Parameters
    ----------
    sample_name : str
        Name of the sample.
    contacts_unbinned_path : str
        Path to the unbinned_contacts.tsv file (generated by fragments).
    sparse_contacts_path : str
        Path to the sparse_contacts_input.txt file (generated by hicstuff).
    centros_coord_path : str
        Path to the input chr_centros_coordinates.tsv file.
    oligos_path : str
        Path to the oligos input CSV file.
    cis_range: int, default=5000
        Cis range to be considered around the probe.
    output_dir : str
        Path to the output directory.
    """

    df_probes: pd.DataFrame = pd.read_csv(oligos_path, sep=',')
    df_coords: pd.DataFrame = pd.read_csv(centros_coord_path, sep='\t', index_col=None)

    chr_size_dict = {k: v for k, v in zip(df_coords['chr'], df_coords['length'])}
    chr_list = list(chr_size_dict.keys())

    df_unbinned_contacts: pd.DataFrame = pd.read_csv(contacts_unbinned_path, sep='\t')
    df_unbinned_contacts = df_unbinned_contacts.astype(dtype={'chr': str, 'start': int, 'sizes': int})

    df_sparse_contacts: pd.DataFrame = \
        pd.read_csv(sparse_contacts_path, header=0, sep="\t", names=['frag_a', 'frag_b', 'contacts'])
    #   from sparse_matrix (hicstuff results): get total contacts from which probes enrichment is calculated
    total_sparse_contacts = sum(df_sparse_contacts["contacts"])

    chr_contacts_nrm = {k: [] for k in chr_size_dict}
    chr_inter_only_contacts_nrm = {k: [] for k in chr_size_dict}

    df_stats: pd.DataFrame = pd.DataFrame(columns=[
        "probe", "chr", "fragment", "type", "contacts",
        "coverage_over_hic_contacts", "cis", "trans",
        "intra_chr", "inter_chr"])

    probes = df_probes['name'].to_list()
    fragments = df_probes['fragment'].astype(str).to_list()
    for index, (probe, frag) in enumerate(zip(probes, fragments)):
        df_stats.loc[index, "probe"] = probe
        df_stats.loc[index, "fragment"] = frag
        df_stats.loc[index, "type"] = df_probes.loc[index, "type"]

        #  get the probe's original coordinates
        self_chr_ori = df_probes.loc[index, "chr_ori"]
        self_start_ori = df_probes.loc[index, "start_ori"]
        self_stop_ori = df_probes.loc[index, "stop_ori"]

        df_stats.loc[index, "chr"] = self_chr_ori

        sub_df = df_unbinned_contacts[['chr', 'start', 'sizes', frag]]
        sub_df.insert(3, 'end', sub_df['start'] + sub_df['sizes'])
        cis_start = self_start_ori - cis_range
        cis_stop = self_stop_ori + cis_range

        probe_contacts = sub_df[frag].sum()
        df_stats.loc[index, "contacts"] = probe_contacts
        df_stats.loc[index, 'coverage_over_hic_contacts'] = probe_contacts / total_sparse_contacts
        probes_contacts_inter = sub_df.query("chr != @self_chr_ori")[frag].sum()

        if probe_contacts > 0:
            cis_freq = sub_df.query("chr == @self_chr_ori & start >= @cis_start & end <= @cis_stop")[frag].sum()
            cis_freq /= probe_contacts

            trans_freq = 1 - cis_freq
            inter_chr_freq = probes_contacts_inter / probe_contacts
            intra_chr_freq = 1 - inter_chr_freq
        else:
            cis_freq = 0
            trans_freq = 0
            inter_chr_freq = 0
            intra_chr_freq = 0

        df_stats.loc[index, "cis"] = cis_freq
        df_stats.loc[index, "trans"] = trans_freq
        df_stats.loc[index, "intra_chr"] = intra_chr_freq
        df_stats.loc[index, "inter_chr"] = inter_chr_freq

        for chrom in chr_list:
            #   n1: sum contacts chr_i
            #   d1: sum contacts all chr
            #   chrom_size: chr_i's size
            #   genome_size: sum of sizes for all chr except frag_chr
            #   c1: normalized contacts on chr_i for frag_j
            chrom_size = chr_size_dict[chrom]
            genome_size = sum([s for c, s in chr_size_dict.items() if c != self_chr_ori])
            n1 = sub_df.loc[sub_df['chr'] == chrom, frag].sum()
            if n1 == 0:
                chr_contacts_nrm[chrom].append(0)
            else:
                d1 = probe_contacts
                c1 = (n1/d1) / (chrom_size/genome_size)
                chr_contacts_nrm[chrom].append(c1)

            #   n2: sum contacts chr_i if chr_i != probe_chr
            #   d2: sum contacts all inter chr (exclude the probe_chr)
            #   c2: normalized inter chr contacts on chr_i for frag_j
            n2 = sub_df.loc[
                (sub_df['chr'] == chrom) &
                (sub_df['chr'] != self_chr_ori), frag].sum()

            if n2 == 0:
                chr_inter_only_contacts_nrm[chrom].append(0)
            else:
                d2 = probes_contacts_inter
                c2 = (n2 / d2) / (chrom_size / genome_size)
                chr_inter_only_contacts_nrm[chrom].append(c2)

    #  capture_efficiency_vs_dsdna: amount of contact for one oligo divided
    #  by the mean of all other 'ds' oligos in the genome
    n3 = df_stats.loc[:, 'contacts']
    d3 = np.mean(df_stats.loc[df_stats['type'] == 'ds', 'contacts'])
    df_stats['dsdna_norm_capture_efficiency'] = n3 / d3

    df_chr_nrm = pd.DataFrame({
        "probe": probes, "fragment": fragments, "type": df_probes["type"].values
    })

    df_chr_inter_only_nrm = df_chr_nrm.copy(deep=True)

    for chr_id in chr_list:
        df_chr_nrm[chr_id] = chr_contacts_nrm[chr_id]
        df_chr_inter_only_nrm[chr_id] = chr_inter_only_contacts_nrm[chr_id]

    df_stats.to_csv(os.path.join(output_dir, f'{sample_name}_contacts_statistics.tsv'), sep='\t', index=False)
    df_chr_nrm.to_csv(os.path.join(output_dir, f'{sample_name}_normalized_chr_freq.tsv'), sep='\t', index=False)
    df_chr_inter_only_nrm.to_csv(os.path.join(output_dir, f'{sample_name}_normalized_inter_chr_freq.tsv'),
                                 sep='\t', index=False)


def compare_to_wt(statistics_path: str, reference_path: str, wt_ref_name: str):
    """
    wt_reference: Optional[str], default=None
            Path to the wt_capture_efficiency file (Optional, if you want to weighted sample).
    """
    df_stats: pd.DataFrame = pd.read_csv(statistics_path, header=0, sep="\t")
    df_wt: pd.DataFrame = pd.read_csv(reference_path, sep='\t')
    df_stats[f"capture_efficiency_vs_{wt_ref_name}"] = np.nan
    for index, row in df_stats.iterrows():
        probe = row['probe']
        wt_capture_eff = df_wt.loc[df_wt['probe'] == probe, "dsdna_norm_capture_efficiency"].tolist()[0]

        if wt_capture_eff > 0:
            df_stats.loc[index, f"capture_efficiency_vs_{wt_ref_name}"] = \
                df_stats.loc[index, 'dsdna_norm_capture_efficiency'] / wt_capture_eff

    df_stats.to_csv(statistics_path, sep='\t')