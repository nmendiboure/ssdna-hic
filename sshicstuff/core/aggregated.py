"""
Script that aggregates contacts made by probes around centromeres or telomeres. The script allows for different
normalization strategies and plots the aggregated mean of contacts around centromeres with standard deviation.

This script requires pandas, numpy and matplotlib packages.

Functions
---------
aggregate(binned_contacts_path, centros_coord_path, probes_to_fragments_path, window_size, on, excluded_chr_list,
          exclude_probe_chr, inter_normalization, plot)
    Aggregate contacts made by probes around centromeres or telomeres.

main(argv)
    Main function that processes command line arguments and calls the aggregate function.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from os.path import join 
from typing import List, Optional
from sshicstuff.core.utils import sort_by_chr, make_groups_of_probes

#   Set as None to avoid SettingWithCopyWarning
pd.options.mode.chained_assignment = None


def aggregate(
        binned_contacts_path: str,
        centros_coord_path: str,
        oligos_path: str,
        window_size: int,
        on: str,
        output_dir: str,
        aggregate_by_arm_sizes: bool = True,
        excluded_chr_list: Optional[List[str]] = None,
        exclude_probe_chr: bool = True,
        additional_path: Optional[str] = None,
        inter_normalization: bool = True,
        plot: bool = False
):

    aggregated_dir = join(output_dir, on)
    dir_tables, dir_plots = (join(aggregated_dir, 'tables'), join(aggregated_dir, 'plots'))
    os.makedirs(aggregated_dir, exist_ok=True)
    os.makedirs(dir_tables, exist_ok=True)
    if plot:
        os.makedirs(dir_plots, exist_ok=True)

    df_centros: pd.DataFrame = pd.read_csv(centros_coord_path, sep='\t', index_col=None)
    chr_list = list(df_centros['chr'].unique())
    df_arms_size: pd.DataFrame = pd.DataFrame(columns=["chr", "arm", "size", "category"])
    for _, row in df_centros.iterrows():
        chr_ = row["chr"]
        if chr_ not in excluded_chr_list:
            left_, right_, category_ = row["left_arm_length"], row["right_arm_length"], row["category"]
            if pd.isna(left_) or pd.isna(right_) or pd.isna(category_):
                continue
            df_arms_size.loc[len(df_arms_size)] = chr_, "left", left_, category_.split("_")[0]
            df_arms_size.loc[len(df_arms_size)] = chr_, "right", right_, category_.split("_")[1]
    df_centros.drop(columns="category", inplace=True)

    df_contacts: pd.DataFrame = pd.read_csv(binned_contacts_path, sep='\t')

    df_probes: pd.DataFrame = pd.read_csv(oligos_path, sep=',')
    probes = df_probes['name'].to_list()
    fragments = df_probes["fragment"].astype(str).tolist()
    unique_fragments = df_probes["fragment"].astype(str).unique().tolist()

    if additional_path:
        df_additional: pd.DataFrame = pd.read_csv(additional_path, sep='\t')
        groups = df_additional['name'].to_list()
        df_contacts.drop(columns=groups, inplace=True)
    else:
        df_additional: pd.DataFrame = pd.DataFrame()

    if len(excluded_chr_list) > 0:
        df_contacts = df_contacts[~df_contacts['chr'].isin(excluded_chr_list)]
        df_centros = df_centros[~df_centros['chr'].isin(excluded_chr_list)]

    if exclude_probe_chr:
        #   We need to remove for each oligo the number of contact it makes with its own chr.
        #   Because we know that the frequency of intra-chr contact is higher than inter-chr
        #   We have to set them as NaN to not bias the average
        for frag in unique_fragments:
            ii_frag = df_probes.loc[df_probes["fragment"] == int(frag)].index[0]
            probe_chr_ori = df_probes.loc[ii_frag, 'chr_ori']
            if probe_chr_ori not in excluded_chr_list:
                df_contacts.loc[df_contacts['chr'] == probe_chr_ori, frag] = np.nan

    if inter_normalization:
        norm_suffix = "inter"
        #   Inter normalization
        df_contacts.loc[:, unique_fragments] = \
            df_contacts[unique_fragments].div(df_contacts[unique_fragments].sum(axis=0))
    else:
        norm_suffix = "absolute"

    if additional_path:
        probes_to_fragments = dict(zip(probes, fragments))
        make_groups_of_probes(df_additional, df_contacts, probes_to_fragments)

    if on == "centromeres":
        df_merged: pd.DataFrame = pd.merge(df_contacts, df_centros, on='chr')
        df_merged_cen_areas: pd.DataFrame = df_merged[
            (df_merged.chr_bins > (df_merged.left_arm_length-window_size-10000)) &
            (df_merged.chr_bins < (df_merged.left_arm_length+window_size))]
        df_merged_cen_areas['chr_bins'] = \
            abs(df_merged_cen_areas['chr_bins'] - (df_merged_cen_areas['left_arm_length'] // 10000)*10000)
        df_grouped: pd.DataFrame = df_merged_cen_areas.groupby(['chr', 'chr_bins'], as_index=False).mean(
            numeric_only=True)
        df_grouped.drop(columns=['length', 'left_arm_length', 'right_arm_length', 'genome_bins'], axis=1, inplace=True)

    elif on == "telomeres":
        df_telos: pd.DataFrame = pd.DataFrame({'chr': df_centros['chr'], 'telo_l': 0, 'telo_r': df_centros['length']})
        df_merged: pd.DataFrame = pd.merge(df_contacts, df_telos, on='chr')
        df_merged_telos_areas_part_a: pd.DataFrame = \
            df_merged[df_merged.chr_bins < (df_merged.telo_l + window_size + 10000)]
        df_merged_telos_areas_part_b: pd.DataFrame = \
            df_merged[df_merged.chr_bins > (df_merged.telo_r - window_size - 10000)]
        df_merged_telos_areas_part_b['chr_bins'] = \
            abs(df_merged_telos_areas_part_b['chr_bins'] - (df_merged_telos_areas_part_b['telo_r'] // 10000) * 10000)
        df_merged_telos_areas: pd.DataFrame = pd.concat((df_merged_telos_areas_part_a, df_merged_telos_areas_part_b))
        df_grouped: pd.DataFrame = df_merged_telos_areas.groupby(['chr', 'chr_bins'], as_index=False).mean(
            numeric_only=True)
        df_grouped.drop(columns=['telo_l', 'telo_r', 'genome_bins'], axis=1, inplace=True)

        if aggregate_by_arm_sizes:
            if "category" not in df_arms_size.columns:
                raise ValueError(
                    "The 'category' column is missing in the centromeres file. "
                    "Must be in the form small_small or long_middle concerning lengths of left_right arms")
            chr_arm(
                df_chr_arm=df_arms_size, df_telos=df_telos, df_contacts=df_contacts,
                telomeres_size=30000, output_path=join(aggregated_dir, f"aggregated_by_arm_sizes_{norm_suffix}.tsv"))

    else:
        return

    df_grouped = sort_by_chr(df_grouped, chr_list, 'chr', 'chr_bins')
    df_grouped['chr_bins'] = df_grouped['chr_bins'].astype('int64')

    df_aggregated_mean: pd.DataFrame = df_grouped.groupby(by="chr_bins", as_index=False).mean(numeric_only=True)
    df_aggregated_mean.to_csv(join(dir_tables, f"aggregated_mean_contacts_around_{on}_{norm_suffix}.tsv"), sep="\t")
    df_aggregated_std: pd.DataFrame = df_grouped.groupby(by="chr_bins", as_index=False).std(numeric_only=True)
    df_aggregated_std.to_csv(join(dir_tables, f"aggregated_std_contacts_around_{on}_{norm_suffix}.tsv"), sep="\t")
    df_aggregated_median: pd.DataFrame = df_grouped.groupby(by="chr_bins", as_index=False).median(numeric_only=True)
    df_aggregated_median.to_csv(join(dir_tables, f"aggregated_median_contacts_around_{on}_{norm_suffix}.tsv"), sep="\t")

    for probe, frag in zip(probes, fragments):
        if df_grouped[frag].sum() == 0:
            continue
        df_chr_centros_pivot: pd.DataFrame = df_grouped.pivot_table(
            index='chr_bins', columns='chr', values=frag, fill_value=0)
        df_chr_centros_pivot.to_csv(
            join(dir_tables, str(frag) + f"_contacts_around_{on}_per_chr_{norm_suffix}.tsv"), sep='\t')

        if plot:
            mean = df_chr_centros_pivot.T.mean()
            std = df_chr_centros_pivot.T.std()

            ymin = -np.max((mean + std)) * 0.01
            pos = mean.index
            plt.figure(figsize=(16, 12))
            plt.bar(pos, mean)
            plt.errorbar(pos, mean, yerr=std, fmt="o", color='b', capsize=5, clip_on=True)
            plt.ylim((ymin, None))
            plt.title(f"Aggregated frequencies for probe {probe} "
                      f"(fragment {frag}) around {on} {norm_suffix} normalization")
            plt.xlabel("Bins around the centromeres (in kb), 5' to 3'")
            plt.xticks(rotation=45)
            plt.ylabel("Average frequency made and standard deviation")
            plt.savefig(
                join(dir_plots, f"{frag}_{on}_aggregated_freq_plot_{norm_suffix}.jpg"), dpi=96)
            plt.close()


def chr_arm(
        df_chr_arm: pd.DataFrame,
        df_telos: pd.DataFrame,
        df_contacts: pd.DataFrame,
        telomeres_size: int,
        output_path: str
):

    df_merged = pd.merge(df_contacts, df_telos, on='chr')
    df_merged_telos_areas_part_a = df_merged[df_merged.chr_bins < (df_merged.telo_l + telomeres_size + 1000)]
    df_merged_telos_areas_part_a.insert(2, 'arm', 'left')
    df_merged_telos_areas_part_b = df_merged[df_merged.chr_bins > (df_merged.telo_r - telomeres_size - 1000)]
    df_merged_telos_areas_part_b.insert(2, 'arm', 'right')

    df_telo_freq = pd.concat((df_merged_telos_areas_part_a, df_merged_telos_areas_part_b))
    df_merged2 = pd.merge(df_telo_freq, df_chr_arm, on=['chr', 'arm'])
    df_merged2.drop(columns=['telo_l', 'telo_r', 'size'], inplace=True)

    df_grouped = df_merged2.groupby(by='category', as_index=False).mean(numeric_only=True)
    df_grouped.drop(columns=['chr_bins', 'genome_bins'], inplace=True)
    df_grouped = df_grouped.rename(columns={'category': 'fragments'}).T
    df_grouped.to_csv(output_path, sep='\t', header=False)