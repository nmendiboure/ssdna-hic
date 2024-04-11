#! /usr/bin/env python3
import os
import numpy as np
import pandas as pd
from typing import Optional
from utils import sort_by_chr, make_groups_of_probes, frag2

#   Set as None to avoid SettingWithCopyWarning
pd.options.mode.chained_assignment = None


def build_bins_from_genome(path_to_chr_coord: str, bin_size: int):
    df = pd.read_csv(path_to_chr_coord, sep='\t', index_col=None)
    chr_sizes = dict(zip(df.chr, df.length))

    chr_list = []
    chr_bins = []

    for c, l in chr_sizes.items():
        chr_list.append([c] * (l // bin_size + 1))
        chr_bins.append(np.arange(0, (l // bin_size + 1) * bin_size, bin_size))

    chr_list = np.concatenate(chr_list)
    chr_bins = np.concatenate(chr_bins)

    df_res = pd.DataFrame({
        'chr': chr_list,
        'chr_bins': chr_bins,
        'genome_bins': np.arange(0, len(chr_bins)*bin_size, bin_size)
    })

    return df_res


def rebin_contacts(
        sample_name: str,
        contacts_unbinned_path: str,
        chromosomes_coord_path: str,
        oligos_path: str,
        bin_size: int,
        output_dir: str,
        additional_path: Optional[str] = None
):

    bin_suffix = f'{bin_size // 1000}kb'
    df_binned_template = build_bins_from_genome(chromosomes_coord_path, bin_size)

    chr_list = list(df_binned_template['chr'].unique())
    df_unbinned = pd.read_csv(contacts_unbinned_path, sep='\t')
    df_unbinned["end"] = df_unbinned["start"] + df_unbinned["sizes"]
    df_unbinned.drop(columns=["genome_start"], inplace=True)
    df_unbinned["start_bin"] = df_unbinned["start"] // bin_size * bin_size
    df_unbinned["end_bin"] = df_unbinned["end"] // bin_size * bin_size

    df_probes: pd.DataFrame = pd.read_csv(oligos_path, sep=',')
    probes = df_probes['name'].to_list()
    fragments = df_probes["fragment"].astype(str).tolist()
    if additional_path:
        df_additional: pd.DataFrame = pd.read_csv(additional_path, sep='\t')
        groups = df_additional['name'].to_list()
        df_unbinned.drop(columns=groups, inplace=True)
    else:
        df_additional: pd.DataFrame = pd.DataFrame()

    df_cross_bins = df_unbinned[df_unbinned["start_bin"] != df_unbinned["end_bin"]].copy()
    df_in_bin = df_unbinned.drop(df_cross_bins.index)
    df_in_bin["chr_bins"] = df_in_bin["start_bin"]

    df_cross_bins_a = df_cross_bins.copy()
    df_cross_bins_b = df_cross_bins.copy()
    df_cross_bins_a["chr_bins"] = df_cross_bins["start_bin"]
    df_cross_bins_b["chr_bins"] = df_cross_bins["end_bin"]

    fragments_columns = df_unbinned.filter(regex='^\d+$').columns.to_list()

    correction_factors = (df_cross_bins_b["end"] - df_cross_bins_b["chr_bins"]) / df_cross_bins_b["sizes"]
    for c in fragments_columns:
        df_cross_bins_a[c] *= (1 - correction_factors)
        df_cross_bins_b[c] *= correction_factors

    df_binned_contacts = pd.concat([df_cross_bins_a, df_cross_bins_b, df_in_bin])
    df_binned_contacts.drop(columns=["start_bin", "end_bin"], inplace=True)

    df_binned_contacts = df_binned_contacts.groupby(["chr", "chr_bins"]).sum().reset_index()
    df_binned_contacts = sort_by_chr(df_binned_contacts, chr_list, 'chr_bins')
    df_binned_contacts = pd.merge(df_binned_template, df_binned_contacts,  on=['chr', 'chr_bins'], how='left')
    df_binned_contacts.drop(columns=["start", "end", "sizes"], inplace=True)
    df_binned_contacts.fillna(0, inplace=True)

    df_binned_freq: pd.DataFrame = df_binned_contacts.copy(deep=True)
    for frag in fragments:
        frag_sum = df_binned_freq[frag].sum()
        if frag_sum > 0:
            df_binned_freq[frag] /= frag_sum

    if additional_path:
        probes_to_fragments = dict(zip(probes, fragments))
        make_groups_of_probes(df_additional, df_binned_contacts, probes_to_fragments)
        make_groups_of_probes(df_additional, df_binned_freq, probes_to_fragments)

    output_path = os.path.join(output_dir, f'{sample_name}_{bin_suffix}_profile')
    df_binned_contacts.to_csv(f'{output_path}_contacts.tsv', sep='\t', index=False)
    df_binned_freq.to_csv(f'{output_path}_frequencies.tsv', sep='\t', index=False)


def rebin_live(df: pd.DataFrame, bin_size: int, df_coords: pd.DataFrame):
    """
    Rebin function for the GUI to change resolution of contacts in live mode.
    """

    chr_sizes = dict(zip(df_coords.chr, df_coords.length))
    chr_list, chr_bins = [], []

    for c, l in chr_sizes.items():
        chr_list.append([c] * (l // bin_size + 1))
        chr_bins.append(np.arange(0, (l // bin_size + 1) * bin_size, bin_size))

    chr_list = np.concatenate(chr_list)
    chr_bins = np.concatenate(chr_bins)

    df_template = pd.DataFrame({
        'chr': chr_list,
        'chr_bins': chr_bins,
        'genome_bins': np.arange(0, len(chr_bins)*bin_size, bin_size)
    })

    df["end"] = df["start"] + df["sizes"]
    df["start_bin"] = df["start"] // bin_size * bin_size
    df["end_bin"] = df["end"] // bin_size * bin_size
    df.drop(columns=["genome_start"], inplace=True)

    df_cross_bins = df[df["start_bin"] != df["end_bin"]].copy()
    df_in_bin = df.drop(df_cross_bins.index)
    df_in_bin["chr_bins"] = df_in_bin["start_bin"]

    df_cross_bins_a = df_cross_bins.copy()
    df_cross_bins_b = df_cross_bins.copy()
    df_cross_bins_a["chr_bins"] = df_cross_bins["start_bin"]
    df_cross_bins_b["chr_bins"] = df_cross_bins["end_bin"]

    fragments_columns = df.filter(regex='^\d+$').columns.to_list()

    correction_factors = (df_cross_bins_b["end"] - df_cross_bins_b["chr_bins"]) / df_cross_bins_b["sizes"]
    for c in fragments_columns:
        df_cross_bins_a[c] *= (1 - correction_factors)
        df_cross_bins_b[c] *= correction_factors

    df_binned = pd.concat([df_cross_bins_a, df_cross_bins_b, df_in_bin])
    df_binned.drop(columns=["start_bin", "end_bin"], inplace=True)

    df_binned = df_binned.groupby(["chr", "chr_bins"]).sum().reset_index()
    df_binned = sort_by_chr(df_binned, chr_list, 'chr_bins')
    df_binned = pd.merge(df_template, df_binned,  on=['chr', 'chr_bins'], how='left')
    df_binned.drop(columns=["start", "end", "sizes"], inplace=True)
    df_binned.fillna(0, inplace=True)

    return df_binned


def profile_contacts(
        sample_name: str,
        filtered_contacts_path: str,
        oligos_path: str,
        chromosomes_coord_path: str,
        output_dir: str,
        additional_path: Optional[str] = None
):
    """
    Organize the contacts made by each probe with the genome and save the results as two .tsv files:
    one for contacts and one for frequencies.

    Parameters
    ----------
    sample_name:
        name of the sample
    filtered_contacts_path : str
        Path to the contacts_filtered_input.txt file (generated by filter).
    oligos_path : str
        Path to the oligos input CSV file.
    chromosomes_coord_path : str
        Path to the input chr_centromeres_coordinates.tsv file.
    output_dir : str
        Path to the output directory.
    additional_path: str
        Path to a csv file that contains groups of probes to sum, average etc ...
    """
    
    df_coords: pd.DataFrame = pd.read_csv(chromosomes_coord_path, sep='\t', index_col=None)
    df_chr_len = df_coords[["chr", "length"]]
    chr_list = list(df_chr_len['chr'].unique())
    df_chr_len["chr_start"] = df_chr_len["length"].shift().fillna(0).astype("int64")
    df_chr_len["cumu_start"] = df_chr_len["chr_start"].cumsum()

    df_probes: pd.DataFrame = pd.read_csv(oligos_path, sep=',')
    probes = df_probes['name'].to_list()
    fragments = df_probes['fragment'].astype(str).to_list()

    df: pd.DataFrame = pd.read_csv(filtered_contacts_path, sep='\t')
    df_contacts: pd.DataFrame = pd.DataFrame(columns=['chr', 'start', 'sizes'])
    df_contacts: pd.DataFrame = df_contacts.astype(dtype={'chr': str, 'start': int, 'sizes': int})

    for x in ['a', 'b']:
        y = frag2(x)
        df2 = df[~pd.isna(df['name_' + x])]

        for probe in probes:
            if probe not in pd.unique(df2['name_'+x]):
                tmp = pd.DataFrame({
                    'chr': [np.nan],
                    'start': [np.nan],
                    'sizes': [np.nan],
                    probe: [np.nan]})

            else:
                df3 = df2[df2['name_'+x] == probe]
                tmp = pd.DataFrame({
                    'chr': df3['chr_'+y],
                    'start': df3['start_'+y],
                    'sizes': df3['size_'+y],
                    probe: df3['contacts']})

            df_contacts = pd.concat([df_contacts, tmp])

    group = df_contacts.groupby(by=['chr', 'start', 'sizes'], as_index=False)
    df_contacts: pd.DataFrame = group.sum()
    df_contacts = sort_by_chr(df_contacts, chr_list, 'chr', 'start')
    df_contacts.index = range(len(df_contacts))

    for probe, frag in zip(probes, fragments):
        df_contacts.rename(columns={probe: frag}, inplace=True)

    df_contacts: pd.DataFrame = df_contacts.loc[:, ~df_contacts.columns.duplicated()]

    df_merged: pd.DataFrame = df_contacts.merge(df_chr_len, on="chr")
    df_merged["genome_start"] = df_merged["cumu_start"] + df_merged["start"]
    df_contacts.insert(3, "genome_start", df_merged["genome_start"])
    del df_merged

    df_frequencies = df_contacts.copy(deep=True)
    for frag in fragments:
        frag_sum = df_frequencies[frag].sum()
        if frag_sum > 0:
            df_frequencies[frag] /= frag_sum

    if additional_path:
        df_additional: pd.DataFrame = pd.read_csv(additional_path, sep='\t')
        probes_to_fragments = dict(zip(probes, fragments))
        make_groups_of_probes(df_additional, df_contacts, probes_to_fragments)
        make_groups_of_probes(df_additional, df_frequencies, probes_to_fragments)

    #   Write into .tsv file contacts as there are and in the form of frequencies :
    df_contacts.to_csv(os.path.join(output_dir, f"{sample_name}_profile_contacts.tsv"), sep='\t', index=False)
    df_frequencies.to_csv(os.path.join(output_dir, f"{sample_name}_profile_frequencies.tsv"), sep='\t', index=False)