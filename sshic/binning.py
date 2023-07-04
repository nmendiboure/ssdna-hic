#! /usr/bin/env python3
import os
import re
import numpy as np
import pandas as pd
from utils import sort_by_chr, remove_columns

#   Set as None to avoid SettingWithCopyWarning
pd.options.mode.chained_assignment = None


def build_bins_from_genome(
        path_to_chr_coord: str,
        bin_size: int
):
    """
    Parses the genome and divides each chromosome into bins of size 'bin_size'.
    Bins are created for each chromosome and the whole genome.

    Parameters
    ----------
    path_to_chr_coord : str
        Path to the input file containing chromosome coordinates.
    bin_size : int
        Size of the bins (in base pairs).

    Returns
    -------
    df_res : pd.DataFrame
        DataFrame containing the bins for each chromosome and the genome.

    """

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
        contacts_unbinned_path: str,
        chromosomes_coord_path: str,
        bin_size: int,
        output_dir: str
):
    """
    Re-bin contacts from the input contacts file and create binned contacts and binned frequencies files.

    Parameters
    ----------
    contacts_unbinned_path : str
        Path to the input unbinned_contacts.tsv file (generated by fragments).
    chromosomes_coord_path : str
        Path to the input chr_centromeres_coordinates.tsv file.
    bin_size : int
        Binning size (in base pairs).
    output_dir : str
        Path to the output directory.
    """
    sample_filename = contacts_unbinned_path.split("/")[-1]
    sample_id = re.search(r"AD\d+", sample_filename).group()
    bin_suffix = str(bin_size // 1000) + 'kb'
    output_path = os.path.join(output_dir, sample_id) + '_' + bin_suffix

    df_binned_template: pd.DataFrame = build_bins_from_genome(
        path_to_chr_coord=chromosomes_coord_path,
        bin_size=bin_size
    )

    df_unbinned: pd.DataFrame = pd.read_csv(contacts_unbinned_path, sep='\t').drop(columns='sizes')
    df: pd.DataFrame = df_unbinned.copy(deep=True)
    df.insert(2, 'chr_bins', (df["start"] // bin_size) * bin_size)
    df_binned_contacts: pd.DataFrame = df.groupby(["chr", "chr_bins"], as_index=False).sum()
    df_binned_contacts = sort_by_chr(df_binned_contacts, 'chr', 'chr_bins')
    df_binned_contacts = pd.merge(df_binned_template, df_binned_contacts,  on=['chr', 'chr_bins'], how='left')
    df_binned_contacts = remove_columns(df_binned_contacts, exclusion=['start', 'end', 'genome_start'])
    df_binned_contacts.fillna(0, inplace=True)

    fragments = [c for c in df_binned_contacts.columns if c not in ['chr', 'chr_bins', "genome_bins"]]

    df_binned_freq: pd.DataFrame = df_binned_contacts.copy(deep=True)
    df_binned_freq[fragments] = (df_binned_contacts[fragments].div(df_binned_contacts[fragments].sum(axis=0)))

    df_binned_contacts.to_csv(output_path + '_binned_contacts.tsv', sep='\t', index=False)
    df_binned_freq.to_csv(output_path + '_binned_frequencies.tsv', sep='\t', index=False)

